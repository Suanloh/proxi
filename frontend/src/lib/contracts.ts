export const agentTypes = ["browser", "mcp", "local", "coding"] as const;
export const editableStatuses = ["active", "inactive", "suspended"] as const;
export const decisions = ["ALLOW", "HOLD", "BLOCK"] as const;
export const severities = ["info", "warning", "critical"] as const;

export type Agent = {
  id: string; name: string; type: (typeof agentTypes)[number] | null;
  description: string | null; status: (typeof editableStatuses)[number] | "revoked";
  created_at: string; last_seen_at: string | null;
};
export type Session = { id: string; status: string; created_at: string; expires_at: string };
export type Capability = { id: string; session_id: string | null; task_id: string | null; action: string; resource_id: string; expires_at: string | null; revoked_at: string | null };
export type Task = { id: string; title: string; status: string };
export type Trust = { score: number; score_persisted: boolean; band: string };
export type TrustEvent = { id: string; created_at: string; reason_code: string; delta: number; previous_score: number | null; new_score: number | null; rule: string | null };
export type AgentDetail = { sessions: Session[]; capabilities: Capability[]; tasks: Task[]; trust: Trust & { history: TrustEvent[]; restrictions: { mode: "none" | "allowlist" | "blocked"; allowed_actions: string[] } } };
export type TrustSummary = Trust & { agent_id: string; active_sessions: number };
export type Integration = { id: string; name: string; status: string; connection_status: "unknown"; operations: string[]; detail: string };
export type Overview = { active_sessions: number; pending_approvals: number };
export type PolicyDefinition = {
  allowed_actions: string[]; denied_actions: string[]; approval_required_actions: string[];
  resource_scope: string[]; sensitive_resources: string[]; conditions: Record<string, unknown>;
};
export type PolicyVersion = {
  version: number; status: string; created_at: string; approved_at: string | null;
  revoked_at: string | null; superseded_at: string | null; definition: PolicyDefinition;
};
export type Policy = { id: string; agent_id: string; task_id: string; source_proposal_id: string; active_version: number | null; latest: PolicyVersion };
export type Approval = {
  id: string; status: string; reason: string; policy_version_ids: string[]; expires_at: string;
  reviewed_at: string | null; reviewed_by: string | null; review_outcome: string | null; consumed_at: string | null;
  request: { agent_id: string; session_id: string; action: string; resource: string; task_id: string | null };
};
export type AuditEvent = {
  id: string; event_type: string; actor_kind: string; actor_id: string | null; agent_id: string | null;
  session_id: string | null; action: string | null; resource_id: string | null; request_id: string | null;
  outcome: string; reason: string | null; created_at: string; correlation_id: string; severity: string;
  audit_event_id?: string;
};
export type Query = Record<string, string | string[] | undefined>;
