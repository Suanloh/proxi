import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { decisions, severities, type Agent, type AuditEvent, type Query } from "@/lib/contracts";
import { eventParams, queryValue } from "@/lib/validation";
import { Select } from "./controls";
import { AgentLink, Data, Facts, Id, Panel, Records, Stamp, Status } from "./shared";

export function EventRecords({events, empty}: {events: AuditEvent[]; empty?: string}) {
  return <Records columns={["Event", "Agent", "Action / reason", "Outcome", "Observed (UTC)"]} empty={empty} rows={events.map((entry) => [entry.id,
    <details key="details"><summary className="cursor-pointer font-medium">{entry.event_type}</summary><div className="mt-3 min-w-60"><Facts items={[
      ["Event ID", <Id key="id" value={entry.id} />], ["Source audit event", entry.audit_event_id], ["Severity", entry.severity],
      ["Actor", `${entry.actor_kind}${entry.actor_id ? ` / ${entry.actor_id}` : ""}`], ["Session", entry.session_id],
      ["Resource ID", entry.resource_id], ["Request ID", entry.request_id], ["Correlation ID", entry.correlation_id],
    ]} /></div></details>,
    entry.agent_id ? <AgentLink key="agent" id={entry.agent_id} /> : "—",
    <div key="action" className="min-w-28 break-all"><Id value={entry.action} /><div className="mt-1 text-xs text-muted-foreground">{entry.reason}</div></div>,
    <div key="outcome" className="flex flex-wrap gap-1"><Status value={entry.outcome} /><Status value={entry.severity} /></div>, <Stamp key="time" value={entry.created_at} />,
  ])} />;
}

export function EventPanel({title, path, empty}: {title: string; path: string; empty?: string}) {
  return <Panel title={title}><Data load={() => api<AuditEvent[]>(path)}>{(events) => <EventRecords events={events} empty={empty} />}</Data></Panel>;
}

export function Monitoring({security, query}: {security: boolean; query: Query}) {
  const pathname = security ? "/monitor" : "/audit";
  return <>
    <Panel title="Find records">
      <form action={pathname} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <label className="field">Search by<Select name="field" defaultValue={queryValue(query, "field") || "event_type"}><option value="event_type">Event type (exact)</option><option value="action">Action (exact)</option><option value="correlation_id">Correlation ID</option></Select></label>
        <label className="field">Search value<Input name="find" defaultValue={queryValue(query, "find")} maxLength={96} /></label>
        <Data load={() => api<Agent[]>("agents")}>{(agents) => <label className="field">Agent<Select name="agent_id" defaultValue={queryValue(query, "agent_id")}><option value="">All agents</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name} ({agent.id})</option>)}</Select></label>}</Data>
        <label className="field">Decision<Select name="decision" defaultValue={queryValue(query, "decision")}><option value="">All outcomes</option>{decisions.map((item) => <option key={item}>{item}</option>)}</Select></label>
        <label className="field">From (UTC, inclusive)<Input type="date" name="since" defaultValue={queryValue(query, "since")} /></label>
        <label className="field">Until (UTC, exclusive)<Input type="date" name="until" defaultValue={queryValue(query, "until")} /></label>
        <label className="field">Severity<Select name="severity" defaultValue={queryValue(query, "severity")}><option value="">All severities</option>{severities.map((item) => <option key={item}>{item}</option>)}</Select></label>
        <div className="flex items-end gap-3"><Button size="sm">Apply filters</Button><Link className="data-link py-2 text-sm" href={pathname}>Clear</Link></div>
      </form>
    </Panel>
    <Panel title={security ? "Classified security events" : "Owner audit trail"}>
      <Data load={() => api<AuditEvent[]>(`${security ? "security-events" : "audit-logs"}?${eventParams(query)}`)}>{(events) => {
        const offset = Number(eventParams(query).get("offset") ?? 0);
        const href = (next: number) => {
          const params = Object.fromEntries(Object.entries(query).filter((entry): entry is [string, string] => typeof entry[1] === "string"));
          return `${pathname}?${new URLSearchParams({...params, offset: String(next)})}`;
        };
        return <><EventRecords events={events} /><nav className="mt-3 flex gap-4 text-sm" aria-label="Event pages">
          {offset > 0 && <Link className="data-link" href={href(Math.max(0, offset - 50))}>Previous</Link>}
          {events.length === 50 && offset < 10000 && <Link className="data-link" href={href(offset + 50)}>Next</Link>}
        </nav></>;
      }}</Data>
    </Panel>
    {security && <>
      <EventPanel title="Recently allowed actions" path="audit-logs?event_type=ActionAllowed&limit=5" />
      <EventPanel title="Recently held actions" path="audit-logs?event_type=ActionHeld&limit=5" />
      <EventPanel title="Recently blocked actions" path="audit-logs?event_type=ActionBlocked&limit=5" />
    </>}
  </>;
}
