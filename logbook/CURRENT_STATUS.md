# Current status

- **Latest completed prompt:** Prompt 14 — PROXI Dashboard & Frontend (`COMPLETE`; production build, browser smoke, focused PostgreSQL tests, and manual approval and session persistence checks passed).
- **Prompt 15 checkpoint:** Browser console and Chrome companion implemented; Chromium smoke tests passed. PostgreSQL workspace verification remains pending.
- **Frontend checkpoint:** [Phase 07 — Frontend](phases/PHASE_07_FRONTEND.md).
- **Integration checkpoint:** [Phase 05 — Browser Integration](phases/PHASE_05_BROWSER_INTEGRATION.md) (`COMPLETE`), with the Prompt 13 catalog follow-up recorded. Phase numbers are checkpoint IDs, not prompt numbers.
- **Overall status:** `IN PROGRESS` — deterministic authorization, human review, guarded browser and catalog dispatch, and dynamic trust restrictions are available; no hosted rollout.
- **Status vocabulary:** `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `TESTING`, `COMPLETE`. Use evidence rather than completion percentages.

- **Prompt 16 validation:** `BLOCKED` for MVP acceptance. DeepSeek is the accepted intent provider; its live workflow was not verified. Backend regression without PostgreSQL: 37 passed, 52 skipped; frontend production build and fixture smoke passed. Workspace persistence, migrations, and critical guarded-dispatch cases were not re-run. See the [validation report](../docs/INTEGRATION_VALIDATION.md) and [test log](TEST_LOG.md#prompt-16).
- **Next:** Provision disposable PostgreSQL and verify the DeepSeek workflow during the live-stack rehearsal. Do not mark Prompt 16 complete on the basis of fixtures or liveness.

## Architecture layers

| Progress | Layer | What exists or remains |
| --- | --- | --- |
| Completed | None | Foundation setup is complete, not the product layers. |
| Partial (`IN PROGRESS`) | Experience | Next.js owner dashboard, isolated Playwright browser console, and read-only Chrome companion. |
| Partial (`IN PROGRESS`) | Integration | Controlled Playwright navigation and reading, plus a fixed catalog lookup through MCP and a local-agent adapter. No generic MCP listener or remote enrollment. |
| Partial (`IN PROGRESS`) | Identity & Authorization | Local owner-scoped agent and session lifecycle, short-lived JWT credentials, and task-scoped capability checks. No production owner authentication. |
| Partial (`IN PROGRESS`) | Intelligence & Trust | Stored intent proposals, deterministic behaviour events, configurable trust scoring and owner review. |
| Partial (`IN PROGRESS`) | Policy & Enforcement | Owner-managed policies and action approvals, deterministic authorization, and revalidating dispatch. No production execution adapter. |
| Partial (`IN PROGRESS`) | Data & Audit | PostgreSQL stores structured audit and security events, with owner-scoped read APIs. The controller still requires an injected pre-dispatch recorder. Storage has no independent tamper evidence. |

## Functionality and handoff

- **Working:** FastAPI liveness at `GET /api/v1/health`; the dashboard builds and renders all major screens against a loopback API fixture. See [verification](TEST_LOG.md) and [local run commands](../docs/DEVELOPMENT.md). Liveness does not establish readiness or protection.
- **Dashboard verification:** Focused tests passed against disposable PostgreSQL, including the browser renderer test that failed in an earlier run for an unknown reason. The user confirmed approval and session persistence through the live dashboard. See the [test log](TEST_LOG.md#prompt-14) and the [known issues register](KNOWN_ISSUES.md).
- **Hosted verification:** No migration or connection attempted against Supabase; hosted configuration was not supplied.
- **Agent identity and access:** Lifecycle management requires the local owner bearer. The [access prerequisite check](../docs/API.md#agent-sessions-and-access-prerequisites) requires an active agent, active session, valid JWT, and matching capability. It does not authorize or execute operations; `last_seen_at` remains unset.
- **Authorization:** The [JWT-bound check endpoint](../docs/API.md#authorization-check) returns `ALLOW`, `HOLD`, or `BLOCK` without executing anything. The controller rechecks authority before dispatching only `ALLOW` to a registered adapter.
- **Action approvals:** [Owner-only endpoints](../docs/API.md#action-approvals) expose pending holds, review, and history. Approval permits one exact retry, subject to fresh authorization.
- **Behaviour and trust:** [Trust restrictions](../docs/SECURITY.md#behaviour-analysis-and-dynamic-trust) supplement policy and capability checks. Persisted events explain score changes; recovery uses a cooldown and compliant streak or [owner review](../docs/API.md#trust-review).
- **Monitoring:** [Owner-only endpoints](../docs/API.md#audit-and-security-monitoring) and the dashboard filter and correlate append-only application history. The monitor refreshes every 15 seconds while visible. No external broker was added.
- **Controlled browser:** The [browser API](../docs/API.md#controlled-browser) supports exact-page navigation and reading through enforcement. The [flight-fare demo](../docs/DEVELOPMENT.md#controlled-browser-demo) verifies approvals and audited blocks on purchase and personal-data sharing. No click, fill, or download. The [Chrome companion](../docs/DEVELOPMENT.md#proxi-browser-and-chrome-companion) displays backend status and events without monitoring regular tabs.
- **Session workflow:** Follow the [mandatory startup and shutdown checklist](../docs/DEVELOPMENT.md#session-workflow).
