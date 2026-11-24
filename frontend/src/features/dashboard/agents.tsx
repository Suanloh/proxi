import Link from "next/link";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { agentTypes, editableStatuses, type Agent, type AgentDetail, type Policy, type TrustEvent, type TrustSummary } from "@/lib/contracts";
import { OperationForm, Select, Textarea } from "./controls";
import { EventPanel } from "./monitoring";
import { AgentLink, Data, Facts, Id, Panel, Records, Stamp, Status, Values } from "./shared";

function AgentFields({agent}: {agent?: Agent}) {
  return <div className="grid gap-3 sm:grid-cols-2">
    <label className="field">Name<Input name="name" required maxLength={120} defaultValue={agent?.name} /></label>
    <label className="field">Type<Select name="type" required defaultValue={agent?.type ?? ""}><option value="" disabled>Select a type</option>{agentTypes.map((item) => <option key={item}>{item}</option>)}</Select></label>
    {agent && <label className="field">Status<Select name="status" defaultValue={agent.status}>{editableStatuses.map((item) => <option key={item}>{item}</option>)}</Select></label>}
    <label className="field sm:col-span-2">Description<Textarea name="description" defaultValue={agent?.description ?? ""} maxLength={2000} /></label>
  </div>;
}

export function Agents() {
  return <>
    <Panel title="Agent inventory"><Data load={() => Promise.all([api<Agent[]>("agents"), api<TrustSummary[]>("dashboard/trust")])}>{([agents, scores]) => {
      const byId = new Map(scores.map((item) => [item.agent_id, item]));
      return <Records columns={["Agent", "Type", "Agent ID", "Status", "Trust", "Last active", "Active sessions"]} rows={agents.map((agent) => [agent.id, <AgentLink key="name" id={agent.id} name={agent.name} />, agent.type ?? "—", <Id key="id" value={agent.id} />, <Status key="status" value={agent.status} />, byId.get(agent.id)?.score ?? "Not scored", <Stamp key="seen" value={agent.last_seen_at} />, byId.get(agent.id)?.active_sessions ?? "—"])} />;
    }}</Data></Panel>
    <Panel title="Register agent"><OperationForm operation="register" label="Register agent"><AgentFields /></OperationForm></Panel>
  </>;
}

export function TrustHistory({history}: {history: TrustEvent[]}) {
  return <Records columns={["Recorded (UTC)", "Trust event"]} empty="No trust changes recorded." rows={history.map((event) => [event.id, <Stamp key="time" value={event.created_at} />, <details key="event"><summary className="cursor-pointer">{event.reason_code}</summary><Facts items={Object.entries(event).filter(([key, value]) => key !== "created_at" && value != null).map(([key, value]) => [key.replaceAll("_", " "), typeof value === "object" ? JSON.stringify(value) : String(value)])} /></details>])} />;
}

export function AgentPage({id}: {id: string}) {
  return <>
    <Link className="data-link text-sm" href="/agents">← Agent inventory</Link>
    <Data load={() => api<Agent>(`agents/${id}`)}>{(agent) => <>
      <Panel title={agent.name}><Facts items={[["Agent ID", agent.id], ["Type", agent.type], ["Status", <Status key="status" value={agent.status} />], ["Last active", <Stamp key="seen" value={agent.last_seen_at} />], ["Registered", <Stamp key="created" value={agent.created_at} />], ["Description", agent.description]]} />
        {agent.status !== "revoked" && <details className="mt-4"><summary className="cursor-pointer font-medium">Manage identity</summary><div className="mt-3 space-y-4"><OperationForm operation="edit-agent" id={id} label="Save agent"><AgentFields agent={agent} /></OperationForm><OperationForm operation="revoke-agent" id={id} label="Revoke agent" confirmation="Revoke this agent permanently?" /></div></details>}
      </Panel>
      <Data load={() => api<AgentDetail>(`dashboard/agents/${id}`)}>{(detail) => <>
        <Panel title="Sessions"><Records columns={["Session", "Status", "Created (UTC)", "Expires (UTC)", "Manage"]} rows={detail.sessions.map((session) => [session.id, <Id key="id" value={session.id} />, <Status key="status" value={session.status} />, <Stamp key="created" value={session.created_at} />, <Stamp key="expiry" value={session.expires_at} />, session.status === "active" ? <OperationForm key="revoke" operation="revoke-session" id={id} secondary={session.id} label="Revoke session" confirmation="Revoke this session?" /> : "—"])} />
        {agent.status === "active" && <div className="mt-4"><OperationForm operation="create-session" id={id} label="Create session"><label className="field max-w-xs">Lifetime in seconds<Input name="ttl" type="number" defaultValue={3600} min={1} max={3600} required /></label></OperationForm></div>}</Panel>
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Assigned tasks"><Records columns={["Task ID", "Title", "Status"]} rows={detail.tasks.map((task) => [task.id, <Id key="id" value={task.id} />, task.title ?? "—", task.status ?? "—"])} /></Panel>
          <Panel title="Active policies"><Data load={() => api<Policy[]>("policies")}>{(policies) => <Records columns={["Policy ID", "Active version", "Task ID"]} rows={policies.filter((policy) => policy.agent_id === id && policy.active_version !== null).map((policy) => [policy.id, <Link key="policy" className="data-link" href={`/policies/${policy.id}`}><Id value={policy.id} /></Link>, policy.active_version, <Id key="task" value={policy.task_id} />])} />}</Data></Panel>
        </div>
        <Panel title="Capabilities"><Records columns={["Action", "Resource", "Task", "Session", "Expires (UTC)", "Revoked (UTC)"]} rows={detail.capabilities.map((item) => [item.id, item.action, <Id key="resource" value={item.resource_id} />, <Id key="task" value={item.task_id} />, <Id key="session" value={item.session_id} />, <Stamp key="expiry" value={item.expires_at} />, <Stamp key="revoke" value={item.revoked_at} />])} /></Panel>
        <Panel title="Trust history"><div className="mb-4 flex items-center gap-3"><span>Score: <strong>{`${detail.trust.score}${detail.trust.score_persisted ? "" : " (initial)"}`}</strong></span><Status value={detail.trust.band} /><Link className="data-link text-sm" href={`/trust/${id}`}>Inspect risk</Link></div><TrustHistory history={detail.trust.history} /></Panel>
      </>}</Data>
      <EventPanel title="Recent actions" path={`audit-logs?agent_id=${id}&event_type=ActionRequested&limit=10`} />
      <EventPanel title="Security events" path={`security-events?agent_id=${id}&limit=10`} />
    </>}</Data>
  </>;
}

export function TrustPage({id}: {id?: string}) {
  if (id) return <>
    <Link className="data-link text-sm" href="/trust">← Trust and risk</Link>
    <Data load={() => Promise.all([api<Agent>(`agents/${id}`), api<AgentDetail>(`dashboard/agents/${id}`)])}>{([agent, detail]) => <>
      <Panel title={agent.name}><Facts items={[["Trust score", `${detail.trust.score}${detail.trust.score_persisted ? "" : " (initial)"}`], ["Trust band", <Status key="band" value={detail.trust.band} />], ["Restrictions", detail.trust.restrictions.mode], ["Allowed actions under trust restriction", detail.trust.restrictions.mode === "allowlist" ? <Values key="actions" values={detail.trust.restrictions.allowed_actions} /> : null]]} />
      <div className="mt-4"><OperationForm operation="review-trust" id={id} label="Request owner trust review" confirmation="Submit a trust review? The backend checks eligibility and cooldown." /></div></Panel>
      <Panel title="Behaviour explanations and trust history"><TrustHistory history={detail.trust.history} /></Panel>
      <EventPanel title="Related security events" path={`security-events?agent_id=${id}&limit=10`} />
    </>}</Data>
  </>;
  return <Panel title="Agent trust overview"><Data load={() => Promise.all([api<Agent[]>("agents"), api<TrustSummary[]>("dashboard/trust")])}>{([agents, scores]) => {
    const names = new Map(agents.map((agent) => [agent.id, agent.name]));
    return <Records columns={["Agent", "Score", "Band"]} rows={scores.map((item) => [item.agent_id, <Link key="agent" href={`/trust/${item.agent_id}`} className="data-link">{names.get(item.agent_id) ?? item.agent_id}</Link>, `${item.score}${item.score_persisted ? "" : " (initial)"}`, <Status key="band" value={item.band} />])} />;
  }}</Data></Panel>;
}
