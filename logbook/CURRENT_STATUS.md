# Current status

- **Current prompt:** Prompt 11 — Audit Logging & Security Monitoring (`COMPLETE`; verified on disposable PostgreSQL).
- **Current phase (last reached):** [Phase 06 — Trust Monitoring](phases/PHASE_06_TRUST_MONITORING.md) (`COMPLETE`). Phase numbers are checkpoint IDs, not prompt numbers.
- **Overall status:** `IN PROGRESS` — deterministic authorization, human review, guarded dispatch, and dynamic trust restrictions are available; no production execution adapter or hosted rollout.
- **Status vocabulary:** `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `TESTING`, `COMPLETE`. Use evidence rather than completion percentages.

## Architecture layers

| Progress | Layer | What exists or remains |
| --- | --- | --- |
| Completed | None | Foundation setup is complete, not the product layers. |
| Partial (`IN PROGRESS`) | Experience | Next.js placeholder, reusable shell and light/dark tokens. Dashboard, controlled browser UI and Chrome extension are not implemented. |
| Not started (`NOT STARTED`) | Integration | Browser, MCP and local-agent packages are placeholders. |
| Partial (`IN PROGRESS`) | Identity & Authorization | Local owner-scoped agent and session lifecycle, short-lived JWT credentials, and task-scoped capability checks. No production owner authentication. |
| Partial (`IN PROGRESS`) | Intelligence & Trust | Stored intent proposals, deterministic behaviour events, configurable trust scoring and owner review. |
| Partial (`IN PROGRESS`) | Policy & Enforcement | Owner-managed policies and action approvals, deterministic authorization, and revalidating dispatch. No production execution adapter. |
| Partial (`IN PROGRESS`) | Data & Audit | PostgreSQL stores structured audit and security events, with owner-scoped read APIs. The controller still requires an injected pre-dispatch recorder. Storage has no independent tamper evidence. |

## Functionality and handoff

- **Working:** FastAPI liveness at `GET /api/v1/health`, environment settings and safe error responses; Next.js placeholder at `/`. See [historical verification](TEST_LOG.md) and [local run commands](../docs/DEVELOPMENT.md). Liveness does not establish readiness or protection.
- **Known broken functionality:** No confirmed runtime defect in the implemented foundation. The [known issues register](KNOWN_ISSUES.md) tracks dependency advisories and an accessibility verification gap.
- **Hosted verification:** No migration or connection attempted against Supabase; hosted configuration was not supplied.
- **Agent identity and access:** Lifecycle management requires the local owner bearer. The [access prerequisite check](../docs/API.md#agent-sessions-and-access-prerequisites) requires an active agent, active session, valid JWT, and matching capability. It does not authorize or execute operations; `last_seen_at` remains unset.
- **Authorization:** The [JWT-bound check endpoint](../docs/API.md#authorization-check) returns `ALLOW`, `HOLD`, or `BLOCK` without executing anything. The controller rechecks authority before dispatching only `ALLOW` to a registered adapter.
- **Action approvals:** [Owner-only endpoints](../docs/API.md#action-approvals) expose pending holds, review, and history. Approval permits one exact retry, subject to fresh authorization.
- **Behaviour and trust:** [Trust restrictions](../docs/SECURITY.md#behaviour-analysis-and-dynamic-trust) supplement policy and capability checks. Persisted events explain score changes; recovery uses a cooldown and compliant streak or [owner review](../docs/API.md#trust-review).
- **Monitoring:** [Owner-only endpoints](../docs/API.md#audit-and-security-monitoring) filter and correlate append-only application history. No dashboard or external broker was added.
- **Session workflow:** Follow the [mandatory startup and shutdown checklist](../docs/DEVELOPMENT.md#session-workflow).
