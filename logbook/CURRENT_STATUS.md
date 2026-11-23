# Current status

- **Current prompt:** Prompt 08 — Authorization & Enforcement Engine (`COMPLETE`; verified on disposable PostgreSQL).
- **Current phase (last reached):** [Phase 04 — Policy Engine](phases/PHASE_04_POLICY_ENGINE.md) (`COMPLETE`). Phase numbers are checkpoint IDs, not prompt numbers.
- **Overall status:** `IN PROGRESS` — deterministic authorization and guarded dispatch are available; no production execution adapter or hosted rollout.
- **Status vocabulary:** `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `TESTING`, `COMPLETE`. Use evidence rather than completion percentages.

## Architecture layers

| Progress | Layer | What exists or remains |
| --- | --- | --- |
| Completed | None | Foundation setup is complete, not the product layers. |
| Partial (`IN PROGRESS`) | Experience | Next.js placeholder, reusable shell and light/dark tokens. Dashboard, controlled browser UI and Chrome extension are not implemented. |
| Not started (`NOT STARTED`) | Integration | Browser, MCP and local-agent packages are placeholders. |
| Partial (`IN PROGRESS`) | Identity & Authorization | Local owner-scoped agent and session lifecycle, short-lived JWT credentials, and task-scoped capability checks. No production owner authentication. |
| Partial (`IN PROGRESS`) | Intelligence & Trust | DeepSeek intent interpretation and stored proposals for owner review; no behavior analysis or trust scoring. |
| Partial (`IN PROGRESS`) | Policy & Enforcement | Owner-managed policy versions, deterministic authorization and revalidating dispatch controller. No action approval workflow or production execution adapter. |
| Partial (`IN PROGRESS`) | Data & Audit | PostgreSQL schema, migrations and repositories are implemented. The controller requires a recorder; no production decision sink is wired. |

## Functionality and handoff

- **Working:** FastAPI liveness at `GET /api/v1/health`, environment settings and safe error responses; Next.js placeholder at `/`. See [historical verification](TEST_LOG.md) and [local run commands](../docs/DEVELOPMENT.md). Liveness does not establish readiness or protection.
- **Known broken functionality:** No confirmed runtime defect in the implemented foundation. The [known issues register](KNOWN_ISSUES.md) tracks dependency advisories and an accessibility verification gap.
- **Hosted verification:** No migration or connection attempted against Supabase; hosted configuration was not supplied.
- **Agent identity and access:** Lifecycle management requires the local owner bearer. The [access prerequisite check](../docs/API.md#agent-sessions-and-access-prerequisites) requires an active agent, active session, valid JWT, and matching capability. It does not authorize or execute operations; `last_seen_at` remains unset.
- **Authorization:** The [JWT-bound check endpoint](../docs/API.md#authorization-check) returns `ALLOW`, `HOLD`, or `BLOCK` without executing anything. The controller rechecks authority before dispatching only `ALLOW` to a registered adapter.
- **Next step:** Stop at Prompt 08. Wait for explicit authorization before adding an action approval interface or execution adapter.
- **Session workflow:** Follow the [mandatory startup and shutdown checklist](../docs/DEVELOPMENT.md#session-workflow).
