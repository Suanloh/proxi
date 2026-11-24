# Current status

- **Current prompt:** Prompt 14 — PROXI Dashboard & Frontend (`TESTING`; production build and browser smoke test passed; persisted end-to-end verification outstanding).
- **Frontend checkpoint:** [Phase 07 — Frontend](phases/PHASE_07_FRONTEND.md). Verify against disposable PostgreSQL before marking complete.
- **Integration checkpoint:** [Phase 05 — Browser Integration](phases/PHASE_05_BROWSER_INTEGRATION.md) (`COMPLETE`), with the Prompt 13 catalog follow-up recorded. Phase numbers are checkpoint IDs, not prompt numbers.
- **Overall status:** `IN PROGRESS` — deterministic authorization, human review, guarded browser and catalog dispatch, and dynamic trust restrictions are available; no hosted rollout.
- **Status vocabulary:** `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `TESTING`, `COMPLETE`. Use evidence rather than completion percentages.

## Architecture layers

| Progress | Layer | What exists or remains |
| --- | --- | --- |
| Completed | None | Foundation setup is complete, not the product layers. |
| Partial (`IN PROGRESS`) | Experience | Next.js owner dashboard, reusable shell and dark/light preferences. Dedicated browser launcher and Chrome extension are not implemented. |
| Partial (`IN PROGRESS`) | Integration | Controlled Playwright navigation and reading, plus a fixed catalog lookup through MCP and a local-agent adapter. No generic MCP listener or remote enrollment. |
| Partial (`IN PROGRESS`) | Identity & Authorization | Local owner-scoped agent and session lifecycle, short-lived JWT credentials, and task-scoped capability checks. No production owner authentication. |
| Partial (`IN PROGRESS`) | Intelligence & Trust | Stored intent proposals, deterministic behaviour events, configurable trust scoring and owner review. |
| Partial (`IN PROGRESS`) | Policy & Enforcement | Owner-managed policies and action approvals, deterministic authorization, and revalidating dispatch. No production execution adapter. |
| Partial (`IN PROGRESS`) | Data & Audit | PostgreSQL stores structured audit and security events, with owner-scoped read APIs. The controller still requires an injected pre-dispatch recorder. Storage has no independent tamper evidence. |

## Functionality and handoff

- **Working:** FastAPI liveness at `GET /api/v1/health`; the dashboard builds and renders all major screens against a loopback API fixture. See [verification](TEST_LOG.md) and [local run commands](../docs/DEVELOPMENT.md). Liveness does not establish readiness or protection.
- **Known verification gaps:** Persisted dashboard and approval tests require disposable PostgreSQL. One existing backend browser renderer test failed in the broader run; the cause was not established. See the [known issues register](KNOWN_ISSUES.md) for previously tracked gaps.
- **Hosted verification:** No migration or connection attempted against Supabase; hosted configuration was not supplied.
- **Agent identity and access:** Lifecycle management requires the local owner bearer. The [access prerequisite check](../docs/API.md#agent-sessions-and-access-prerequisites) requires an active agent, active session, valid JWT, and matching capability. It does not authorize or execute operations; `last_seen_at` remains unset.
- **Authorization:** The [JWT-bound check endpoint](../docs/API.md#authorization-check) returns `ALLOW`, `HOLD`, or `BLOCK` without executing anything. The controller rechecks authority before dispatching only `ALLOW` to a registered adapter.
- **Action approvals:** [Owner-only endpoints](../docs/API.md#action-approvals) expose pending holds, review, and history. Approval permits one exact retry, subject to fresh authorization.
- **Behaviour and trust:** [Trust restrictions](../docs/SECURITY.md#behaviour-analysis-and-dynamic-trust) supplement policy and capability checks. Persisted events explain score changes; recovery uses a cooldown and compliant streak or [owner review](../docs/API.md#trust-review).
- **Monitoring:** [Owner-only endpoints](../docs/API.md#audit-and-security-monitoring) and the dashboard filter and correlate append-only application history. The monitor refreshes every 15 seconds while visible. No external broker was added.
- **Controlled browser:** The [browser API](../docs/API.md#controlled-browser) supports exact-page navigation and reading through enforcement. The [flight-fare demo](../docs/DEVELOPMENT.md#controlled-browser-demo) verifies approvals and audited blocks on purchase and personal-data sharing. No click, fill, download, or Chrome extension.
- **Session workflow:** Follow the [mandatory startup and shutdown checklist](../docs/DEVELOPMENT.md#session-workflow).
