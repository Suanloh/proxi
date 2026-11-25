import { agentTypes, decisions, editableStatuses, severities, type Query } from "./contracts";

const uuid = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;
const actionName = /^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$/;
const invalidText = /[\u0000\uD800-\uDFFF]/u;
export class InputError extends Error {}
export function identifier(value: string): string {
  if (!uuid.test(value)) throw new InputError("Enter a valid record ID.");
  return value;
}
export function text(data: FormData, key: string): string {
  const value = data.get(key);
  return typeof value === "string" ? value.trim() : "";
}
export function fields(data: FormData) {
  const name = text(data, "name");
  const type = text(data, "type");
  const description = text(data, "description") || null;
  if (!name || name.length > 120 || (description?.length ?? 0) > 2000 || invalidText.test(name + (description ?? ""))) {
    throw new InputError("Enter a name of 1–120 characters and a description of up to 2,000 characters.");
  }
  if (!agentTypes.some((item) => item === type)) throw new InputError("Select an agent type.");
  const status = text(data, "status");
  if (status && !editableStatuses.some((item) => item === status)) throw new InputError("Select a valid status.");
  return {name, type, description, ...(status ? {status} : {})};
}

export const policyFields = ["allowed_actions", "denied_actions", "approval_required_actions", "resource_scope", "sensitive_resources"] as const;
export function policyDefinition(data: FormData) {
  const lists = Object.fromEntries(policyFields.map((key, i) => {
    const list = text(data, key).split(/\r?\n/).map((entry) => entry.trim()).filter(Boolean);
    if (list.length > (i < 3 ? 32 : 24) || list.some((entry) => invalidText.test(entry) || (i < 3 ? entry.length > 96 || !actionName.test(entry) : entry.length > 256))) {
      throw new InputError(`Check the number and format of entries in ${key.replaceAll("_", " ")}.`);
    }
    return [key, list];
  }));
  const actions = policyFields.slice(0, 3).flatMap((key) => lists[key]);
  if (new Set(actions).size !== actions.length) throw new InputError("Each action may be listed only once across the action fields.");
  let conditions: unknown;
  try { conditions = JSON.parse(text(data, "conditions") || "{}"); } catch {
    throw new InputError("Conditions must be a JSON object.");
  }
  if (!conditions || typeof conditions !== "object" || Array.isArray(conditions)) throw new InputError("Conditions must be a JSON object.");
  return {...lists, conditions};
}

export function queryValue(query: Query, key: string) {
  const value = query[key];
  return typeof value === "string" ? value.trim() : "";
}

export function eventParams(query: Query) {
  const params = new URLSearchParams({limit: "50"});
  const filter = queryValue(query, "find");
  const field = queryValue(query, "field") || "event_type";
  if (filter) {
    if (field === "correlation_id") identifier(filter);
    else if (field === "action" && (!actionName.test(filter) || filter.length > 96)) throw new InputError("Enter a valid action name.");
    else if (field === "event_type" && filter.length > 64) throw new InputError("Event type must be at most 64 characters.");
    else if (!["event_type", "action", "correlation_id"].includes(field)) throw new InputError("Select a valid search field.");
    params.set(field, filter);
  }
  const agent = queryValue(query, "agent_id");
  if (agent) params.set("agent_id", identifier(agent));
  for (const [key, options] of [["decision", decisions], ["severity", severities]] as const) {
    const value = queryValue(query, key);
    if (value) {
      if (!options.some((item) => item === value)) throw new InputError(`Select a valid ${key}.`);
      params.set(key, value);
    }
  }
  for (const key of ["since", "until"]) {
    const value = queryValue(query, key);
    if (!value) continue;
    const date = new Date(`${value}T00:00:00Z`);
    if (!/^\d{4}-\d\d-\d\d$/.test(value) || !Number.isFinite(date.valueOf()) || date.toISOString().slice(0, 10) !== value) throw new InputError("Enter valid UTC dates.");
    params.set(key, date.toISOString());
  }
  if (params.has("since") && params.has("until") && params.get("since")! >= params.get("until")!) throw new InputError("The start date must precede the end date.");
  const offset = queryValue(query, "offset");
  if (/^\d+$/.test(offset) && Number(offset) <= 10000) params.set("offset", offset);
  return params;
}
