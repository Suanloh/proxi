import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { ownerCookie } from "@/lib/api";
import type { Query } from "@/lib/contracts";
import { identifier, queryValue } from "@/lib/validation";
import { AgentPage, Agents, TrustPage } from "@/features/dashboard/agents";
import { Approvals } from "@/features/dashboard/approvals";
import { Refresh, ThemeSettings } from "@/features/dashboard/controls";
import { PageHeading } from "@/features/dashboard/heading";
import { Monitoring } from "@/features/dashboard/monitoring";
import { IntegrationPanel } from "@/features/dashboard/overview";
import { Policies } from "@/features/dashboard/policies";
import { Panel } from "@/features/dashboard/shared";

const sections = {
  agents: ["Agents", "Register agents and manage their identity and sessions.", "Agent details"],
  policies: ["Policies", "Inspect policy scope, version history, and lifecycle.", "Policy details"],
  approvals: ["Approval centre", "Review held action requests without dispatching them.", "Approval details"],
  monitor: ["Security monitor", "Review classified events and recent authorization decisions."],
  trust: ["Trust & risk", "Inspect persisted scores, restrictions, and behaviour history.", "Agent trust details"],
  audit: ["Audit logs", "Search owner-scoped activity, decisions, and correlations."],
  integrations: ["Integrations", "Inspect supported operations and backend adapter status."],
  settings: ["Settings", "Manage dashboard preferences. Server credentials and configuration are not shown."],
} as const;

type Section = keyof typeof sections;

export default async function SectionPage({params, searchParams}: {params: Promise<{section: string; detail?: string[]}>; searchParams: Promise<Query>}) {
  const {section, detail = []} = await params;
  if (!Object.hasOwn(sections, section)) notFound();
  const key = section as Section;
  const [title, description, detailTitle] = sections[key];
  if (detail.length > 1 || (detail.length && !detailTitle)) notFound();
  let id: string | undefined;
  if (detail.length) {
    try { id = identifier(detail[0]); } catch { notFound(); }
  }
  if (!(await cookies()).has(ownerCookie)) redirect("/");
  const query = await searchParams;
  const content = {
    agents: id ? <AgentPage id={id} /> : <Agents />,
    policies: <Policies id={id} />,
    approvals: <Approvals id={id} query={query} />,
    monitor: <><Monitoring security query={query} /><IntegrationPanel /></>,
    trust: <TrustPage id={id} />,
    audit: <Monitoring security={false} query={query} />,
    integrations: <IntegrationPanel />,
    settings: <Panel title="Appearance"><ThemeSettings /></Panel>,
  }[key];
  const pendingApprovals = key === "approvals" && !id && queryValue(query, "history") !== "true";
  const autoRefresh = key === "monitor" || pendingApprovals;
  return <><PageHeading title={id ? detailTitle! : title} description={id ? undefined : description} controls={key !== "settings" && <Refresh key={`${key}:${autoRefresh}`} auto={autoRefresh} />} />{content}</>;
}
