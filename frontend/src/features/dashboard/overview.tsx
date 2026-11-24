import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { Agent, Integration, Overview as OverviewData } from "@/lib/contracts";
import { TrustPage } from "./agents";
import { EventPanel } from "./monitoring";
import { Data, Panel, Records, Status, Values } from "./shared";

function Metric({label, value, href}: {label: string; value: number; href: string}) {
  return <Card><CardContent><Link href={href} className="data-link text-xs font-medium uppercase tracking-wider">{label}</Link><p className="mt-2 text-4xl font-semibold tabular-nums">{value}</p></CardContent></Card>;
}

export function IntegrationPanel() {
  return <Panel title="Integration status"><Data load={() => api<Integration[]>("dashboard/integrations")}>{(items) => <Records columns={["Integration", "Status", "Supported operations", "Connection", "Details"]} rows={items.map((item) => [item.id, item.name, <Status key="status" value={item.status} />, <Values key="ops" values={item.operations} />, item.connection_status, item.detail])} />}</Data></Panel>;
}

export function Overview() {
  return <>
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Data load={() => api<Agent[]>("agents")}>{(agents) => <><Metric label="Registered agents" value={agents.length} href="/agents" /><Metric label="Active agents" value={agents.filter((agent) => agent.status === "active").length} href="/agents" /></>}</Data>
      <Data load={() => api<OverviewData>("dashboard/overview")}>{(counts) => <><Metric label="Active sessions" value={counts.active_sessions} href="/agents" /><Metric label="Pending approvals" value={counts.pending_approvals} href="/approvals" /></>}</Data>
    </div>
    <EventPanel title="Recent blocked actions" path="audit-logs?event_type=ActionBlocked&limit=5" empty="No blocked actions recorded." />
    <EventPanel title="Recent security events" path="security-events?limit=5" empty="No security events recorded." />
    <TrustPage />
    <IntegrationPanel />
  </>;
}
