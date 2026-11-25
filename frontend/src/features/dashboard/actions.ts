"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { api, apiMessage, ownerCookie } from "@/lib/api";
import { fields, identifier, InputError, policyDefinition, text } from "@/lib/validation";

export type ActionState = { message: string; ok: boolean } | null;
export type Operation = "register" | "edit-agent" | "revoke-agent" | "create-session" | "revoke-session" | "review-trust" | "create-policy" | "revise-policy" | "submit-policy" | "approve-policy" | "revoke-policy" | "approve-action" | "reject-action";

export async function signIn(_state: ActionState, data: FormData): Promise<ActionState> {
  const token = text(data, "token");
  if (!/^[\x21-\x7e]{1,2048}$/.test(token)) return {ok: false, message: "Enter the configured owner bearer token."};
  try {
    await api("agents", {token});
    (await cookies()).set(ownerCookie, token, {
      httpOnly: true, sameSite: "strict", secure: process.env.PROXI_SECURE_COOKIES === "true", path: "/",
    });
  } catch (error) {
    return {ok: false, message: apiMessage(error)};
  }
  redirect("/");
}

export async function signOut() {
  (await cookies()).delete(ownerCookie);
  redirect("/");
}

export async function operate(operation: Operation, id: string, secondary: string, _state: ActionState, data: FormData): Promise<ActionState> {
  try {
    const record = id ? identifier(id) : "";
    const versioned = ["revise-policy", "submit-policy", "approve-policy", "revoke-policy"].includes(operation);
    const version = Number(secondary);
    if (versioned && (!/^\d+$/.test(secondary) || !Number.isSafeInteger(version) || version < 1)) throw new InputError("Invalid policy version.");
    switch (operation) {
      case "register": {
        const {name, type, description} = fields(data);
        await api("agents", {method: "POST", body: {name, type, description}});
        break;
      }
      case "edit-agent": await api(`agents/${record}`, {method: "PATCH", body: fields(data)}); break;
      case "revoke-agent": await api(`agents/${record}/revoke`, {method: "POST"}); break;
      case "create-session": {
        const ttl = text(data, "ttl");
        if (!/^\d+$/.test(ttl) || +ttl < 1 || +ttl > 3600) throw new InputError("Session lifetime must be 1–3,600 seconds.");
        await api(`agents/${record}/sessions`, {method: "POST", body: {ttl_seconds: Number(ttl)}});
        break;
      }
      case "revoke-session": await api(`agents/${record}/sessions/${identifier(secondary)}/revoke`, {method: "POST"}); break;
      case "review-trust": await api(`agents/${record}/trust/review`, {method: "POST"}); break;
      case "create-policy": await api("policies", {method: "POST", body: {agent_id: identifier(text(data, "agent")), proposal_id: identifier(text(data, "proposal"))}}); break;
      case "revise-policy": await api(`policies/${record}/versions`, {method: "POST", body: {base_version: version, definition: policyDefinition(data)}}); break;
      case "submit-policy": await api(`policies/${record}/versions/${version}/submit`, {method: "POST"}); break;
      case "approve-policy": await api(`policies/${record}/versions/${version}/approve`, {method: "POST", body: {approve: true}}); break;
      case "revoke-policy": await api(`policies/${record}/versions/${version}/revoke`, {method: "POST"}); break;
      case "approve-action": await api(`approvals/${record}/approve`, {method: "POST"}); break;
      case "reject-action": await api(`approvals/${record}/reject`, {method: "POST"}); break;
      default: throw new InputError("Unsupported operation.");
    }
  } catch (error) {
    return {ok: false, message: error instanceof InputError ? error.message : apiMessage(error)};
  }
  revalidatePath("/", "layout");
  return {ok: true, message: operation === "approve-action" ? "Approval recorded. No action was executed." : "Change accepted by the backend."};
}
