import Link from "next/link";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { Agent, Policy, PolicyVersion } from "@/lib/contracts";
import { policyFields } from "@/lib/validation";
import { OperationForm, Select, Textarea } from "./controls";
import { AgentLink, Data, Facts, Id, Panel, Records, Stamp, Status, Values } from "./shared";

const labels = {allowed_actions: "Allowed actions", denied_actions: "Denied actions", approval_required_actions: "Actions requiring approval", resource_scope: "Resource scope", sensitive_resources: "Sensitive resources"};

export function Policies({id}: {id?: string}) {
  if (!id) return <>
    <Panel title="Managed policies"><Data load={() => api<Policy[]>("policies")}>{(policies) => <Records columns={["Policy ID", "Agent", "Latest status", "Latest version", "Active version"]} rows={policies.map((policy) => [policy.id, <Link key="id" href={`/policies/${policy.id}`} className="data-link"><Id value={policy.id} /></Link>, <AgentLink key="agent" id={policy.agent_id} />, <Status key="status" value={policy.latest.status} />, policy.latest.version, policy.active_version ?? "—"])} />}</Data></Panel>
    <Panel title="Create draft from stored proposal"><Data load={() => api<Agent[]>("agents")}>{(agents) => <OperationForm operation="create-policy" label="Create draft"><div className="grid gap-3 sm:grid-cols-2">
      <label className="field">Agent<Select name="agent" defaultValue="" required><option value="" disabled>Select an agent</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}</Select></label>
      <label className="field">Validated proposal ID<Input name="proposal" required maxLength={36} /></label>
    </div></OperationForm>}</Data></Panel>
  </>;
  return <>
    <Link href="/policies" className="data-link text-sm">← Managed policies</Link>
    <Data load={() => Promise.all([api<Policy>(`policies/${id}`), api<PolicyVersion[]>(`policies/${id}/versions`)])}>{([policy, versions]) => <>
      <Panel title="Policy identity"><Facts items={[["Policy ID", policy.id], ["Agent", <AgentLink key="agent" id={policy.agent_id} />], ["Task", policy.task_id], ["Source proposal", policy.source_proposal_id], ["Active version", policy.active_version], ["Latest version", policy.latest.version]]} /></Panel>
      <Panel title="Version and approval history"><Records columns={["Version", "Status", "Created (UTC)", "Approved (UTC)", "Superseded (UTC)", "Revoked (UTC)"]} rows={versions.map((version) => [version.version,
        <details key="version"><summary className="cursor-pointer whitespace-nowrap">Version {version.version}</summary><Facts items={[...policyFields.map((key): [string, React.ReactNode] => [labels[key], <Values key={key} values={version.definition[key]} />]), ["Conditions", <pre key="conditions" className="whitespace-pre-wrap text-xs">{JSON.stringify(version.definition.conditions, null, 2)}</pre>]]} /></details>,
        <Status key="status" value={version.status} />, <Stamp key="created" value={version.created_at} />, <Stamp key="approval" value={version.approved_at} />, <Stamp key="superseded" value={version.superseded_at} />, <Stamp key="revoke" value={version.revoked_at} />,
      ])} /></Panel>
      <Panel title="Manage versions"><div className="flex flex-wrap gap-3">
        {versions.filter((v) => ["draft", "pending_approval", "active"].includes(v.status)).map((v) => <div key={v.version} className="space-y-2 rounded-md border border-border p-3"><p className="text-sm font-medium">Version {v.version}</p>
          {v.status === "draft" && <OperationForm operation="submit-policy" id={id} secondary={String(v.version)} label="Submit for approval" />}
          {v.status === "pending_approval" && <OperationForm operation="approve-policy" id={id} secondary={String(v.version)} label="Approve version" confirmation="Approve and activate this version, replacing any active version?" />}
          <OperationForm operation="revoke-policy" id={id} secondary={String(v.version)} label="Revoke version" confirmation="Revoke this policy version?" />
        </div>)}
      </div><details className="mt-4"><summary className="cursor-pointer font-medium">Draft a replacement version</summary><div className="mt-3"><OperationForm key={policy.latest.version} operation="revise-policy" id={id} secondary={String(policy.latest.version)} label="Save replacement draft"><div className="grid gap-3 sm:grid-cols-2">
        {policyFields.map((key) => <label key={key} className="field">{labels[key]} (one per line)<Textarea name={key} defaultValue={policy.latest.definition[key].join("\n")} /></label>)}
        <label className="field">Conditions (JSON)<Textarea name="conditions" defaultValue={JSON.stringify(policy.latest.definition.conditions, null, 2)} /></label>
      </div></OperationForm></div></details></Panel>
    </>}</Data>
  </>;
}
