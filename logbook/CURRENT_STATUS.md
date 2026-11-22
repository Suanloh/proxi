# Current status

- **Current prompt:** Prompt 05 — Session & Capability Management (`COMPLETE`; verified on disposable local PostgreSQL).
- **Current phase (last reached):** [Phase 02 — Identity](phases/PHASE_02_IDENTITY.md) (`IN PROGRESS`). Phase numbers are checkpoint IDs, not prompt numbers.
- **Overall status:** `IN PROGRESS` — local identity, session and capability management are available; no protected execution or hosted rollout.
- **Status vocabulary:** `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `TESTING`, `COMPLETE`. Use evidence rather than completion percentages.

## Architecture layers

| Progress | Layer | What exists or remains |
| --- | --- | --- |
| Completed | None | Foundation setup is complete, not the product layers. |
| Partial (`IN PROGRESS`) | Experience | Next.js placeholder, reusable shell and light/dark tokens. Dashboard, controlled browser UI and Chrome extension are not implemented. |
| Not started (`NOT STARTED`) | Integration | Browser, MCP and local-agent packages are placeholders. |
| Partial (`IN PROGRESS`) | Identity & Authorization | Local owner-scoped agent and session lifecycle, short-lived JWT credentials, and task-scoped capability checks. No production owner authentication or policy evaluation. |
| Not started (`NOT STARTED`) | Intelligence & Trust | No Gemini intent interpretation, behavior analysis or trust scoring. |
| Not started (`NOT STARTED`) | Policy & Enforcement | No policy evaluation, approvals, protected execution or enforcement. |
| Partial (`IN PROGRESS`) | Data & Audit | PostgreSQL schema, migrations and repositories are implemented. Audit storage exists; automatic recording from protected actions does not. |

## Functionality and handoff

- **Working:** FastAPI liveness at `GET /api/v1/health`, environment settings and safe error responses; Next.js placeholder at `/`. See [historical verification](TEST_LOG.md) and [local run commands](../docs/DEVELOPMENT.md). Liveness does not establish readiness or protection.
- **Known broken functionality:** No confirmed runtime defect in the implemented foundation. The [known issues register](KNOWN_ISSUES.md) tracks dependency advisories and an accessibility verification gap.
- **Hosted verification:** No migration or connection attempted against Supabase; hosted configuration was not supplied.
- **Agent identity and access:** Lifecycle management requires the local owner bearer. The [access prerequisite check](../docs/API.md#agent-sessions-and-access-prerequisites) requires an active agent, active session, valid JWT, and matching capability. It does not authorize or execute operations; `last_seen_at` remains unset.
- **Next step:** Stop at Prompt 05; wait for explicit authorization for downstream work.
- **Session workflow:** Follow the [mandatory startup and shutdown checklist](../docs/DEVELOPMENT.md#session-workflow).
