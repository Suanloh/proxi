import Link from "next/link";
import { api } from "@/lib/api";
import type { Agent, Approval, Query } from "@/lib/contracts";
import { queryValue } from "@/lib/validation";
import { OperationForm } from "./controls";
import { AgentLink, Data, Facts, Id, Panel, Records, Stamp, Status, Values } from "./shared";

export function Approvals({id, query}: {id?: string; query: Query}) {
  if (id) return <>
    <Link href="/approvals" className="data-link text-sm">← Approval centre</Link>
    <Data load={() => api<Approval>(`approvals/${id}`)}>{(item) => <Panel title="Action request">
      <Facts items={[["Request ID", item.id], ["Agent", <AgentLink key="agent" id={item.request.agent_id} />], ["Action", item.request.action], ["Target resource", item.request.resource], ["Reason", item.reason], ["Policy version IDs", <Values key="policy" values={item.policy_version_ids} />], ["Session", item.request.session_id], ["Task", item.request.task_id], ["Status", <Status key="status" value={item.status} />], ["Expires (UTC)", <Stamp key="expiry" value={item.expires_at} />], ["Reviewed (UTC)", <Stamp key="review" value={item.reviewed_at} />], ["Reviewer", item.reviewed_by], ["Review outcome", item.review_outcome], ["Consumed (UTC)", <Stamp key="claim" value={item.consumed_at} />]]} />
      {item.status === "PENDING" && <div className="mt-4 space-y-3"><p className="text-sm text-muted-foreground">Approval does not run the action. A retry must pass backend revalidation before dispatch.</p><div className="flex flex-wrap gap-3">
        <OperationForm operation="approve-action" id={id} label="Approve request" confirmation="Approve this exact action for backend revalidation on retry?" />
        <OperationForm operation="reject-action" id={id} label="Reject request" confirmation="Reject this request?" />
      </div></div>}
    </Panel>}</Data>
  </>;
  const history = queryValue(query, "history") === "true";
  const raw = queryValue(query, "offset");
  const offset = /^\d+$/.test(raw) && Number(raw) <= 10000 ? Number(raw) : 0;
  const page = (next: number) => `/approvals?history=${history}&offset=${next}`;
  return <Panel title={history ? "Review history" : "Pending requests"}>
    <nav aria-label="Approval views" className="mb-4 flex gap-4 text-sm"><Link aria-current={!history ? "page" : undefined} href="/approvals" className="data-link">Pending</Link><Link aria-current={history ? "page" : undefined} href="/approvals?history=true" className="data-link">History</Link></nav>
    <Data load={() => Promise.all([api<Approval[]>(`approvals?history=${history}&limit=50&offset=${offset}`), api<Agent[]>("agents")])}>{([items, agents]) => {
      const names = new Map(agents.map((agent) => [agent.id, agent.name]));
      return <><Records columns={["Request / action", "Requesting agent", "Target resource", "Reason", "Policy versions", "Expires (UTC)", "Status"]} empty={history ? "No reviewed or expired requests." : "No requests awaiting review."} rows={items.map((item) => [item.id,
        <Link key="request" href={`/approvals/${item.id}`} className="data-link">{item.request.action}</Link>, <AgentLink key="agent" id={item.request.agent_id} name={names.get(item.request.agent_id)} />,
        <Id key="target" value={item.request.resource} />, item.reason, <Values key="policy" values={item.policy_version_ids} />, <Stamp key="expiry" value={item.expires_at} />, <Status key="status" value={item.status} />,
      ])} /><nav className="mt-3 flex gap-4 text-sm" aria-label="Approval pages">{offset > 0 && <Link href={page(Math.max(0, offset - 50))} className="data-link">Previous</Link>}{items.length === 50 && offset < 10000 && <Link href={page(offset + 50)} className="data-link">Next</Link>}</nav></>;
    }}</Data>
  </Panel>;
}
