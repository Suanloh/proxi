# Prompt 16 — Integration and security validation

**2026-11-26 · Layer validation progressed; full-stack sign-off pending.** The initial run did not have a disposable PostgreSQL DSN. In the follow-up, the operator marked Experience complete and reported passing PostgreSQL checks for Identity & Authorization, Trust, Policy & Enforcement, and Data & Audit. A live DeepSeek POST returned `201` through PROXI after correcting the model name to `deepseek-flash`. A matching proposal GET, the Integration rerun's skip count, and a continuous live-stack rehearsal were not explicitly confirmed. DeepSeek is the accepted intent provider; Gemini is out of scope.

## Architecture and implementation

| Layer | Implemented | Remaining boundary or gap |
| --- | --- | --- |
| Experience | Next.js owner dashboard, standalone Playwright console, and a read-only Chrome companion with opt-in observation of one ordinary tab | Operator marked the layer complete. Worker tests and Chromium popup messaging passed; the dashboard smoke used a fixture API. Tab observations stay in Chrome and do not authorize or block actions. Task submission and capability issuance use the API. |
| Integration | Exact-page Playwright navigation/read, in-process MCP SDK catalog lookup, local catalog adapter | Operator reported zero failures on rerun; the skip count was not supplied. No generalized MCP proxy, arbitrary execution, browser purchase, click, fill, or download. |
| Identity & Authorization | Local owner bearer, agent lifecycle, revocable JWT sessions and exact capabilities | Operator reported 4 passed. Owner bearer authentication is for local development only. |
| Intelligence & Trust | Validated DeepSeek proposals, deterministic behaviour events and configurable restrictions | Operator reported a live POST `201` and 12 passing trust tests. Matching proposal GET was not explicitly confirmed. Provider output and webpage text remain untrusted. |
| Policy & Enforcement | Versioned owner-approved policies, deterministic `ALLOW`/`HOLD`/`BLOCK`, one-use revalidated approvals | Operator reported 27 passed, zero skipped, including approval concurrency and revocation checks. Capability provisioning remains separate. |
| Data & Audit | Alembic revisions, PostgreSQL persistence, owner-scoped audit and security reads | Operator reported all six targeted checks passed: database startup, migration round trip, record persistence, foreign keys and audit retention, owner-scoped audit and security reads, and monitoring rollback. No independent tamper evidence or durable pre-dispatch sink; external effects and audit commit are not atomic. |

The control plane manages authority and review; guarded routes in the data plane alone dispatch. Source review found one policy engine shared by the check and enforcement paths and no alternate dispatch in the supported browser, MCP, and local catalog routes. Intent uses `IntentProvider`; MCP/local catalog use `ToolAdapter`; browser dispatch uses a synchronous callable. Static review found no explicit internal cycles (88 modules, 237 edges). Concrete SQLAlchemy read services and core dependencies on boundary schema types depart from the [hexagonal design](ARCHITECTURE.md#prompt-16-dependency-review).

## Functional acceptance matrix

| # | Scenario | Prompt 16 evidence |
| --- | --- | --- |
| 1 | Agent registration and dashboard visibility | Persisted registration passed in the Identity run. The dashboard passed against a fixture API; live dashboard visibility remains unconfirmed. |
| 2 | Natural-language interpretation and proposal review | Live DeepSeek POST returned `201` after correcting the model ID. Retrieving the same proposal ID and reviewing its scope remain unconfirmed. |
| 3 | Policy activation and scoped capability | PostgreSQL policy lifecycle and capability scope checks passed in separate runs. Policy approval does not issue capabilities. |
| 4 | Allowed navigation and audit | Offline Chromium renderer passed. The enforcement suite verified dispatch and audit persistence; the database-backed Chromium flight case needs a confirmed unskipped result. |
| 5 | Prohibited purchase | Explicit policy denial passed in the enforcement suite. The fixture console displayed a purchase block; the database-backed flight result needs confirmation. There is no purchase adapter. |
| 6 | Approval-required action | PostgreSQL workflow passed for `HOLD`, approved retry, concurrent retries, and revalidation before dispatch. |
| 7 | Revocation | Identity and enforcement cases passed for session and capability revocation, including session revocation before approved dispatch. |
| 8 | Trust restriction | All 12 selected trust cases passed, including persisted events, restrictions, and the hard-deny interaction. |
| 9 | Controlled MCP | Source confirms normalization and central dispatch. The Integration rerun had zero reported failures, but execution of the previously skipped MCP cases is unconfirmed. |
| 10 | Provider or adapter failure | Focused DeepSeek tests passed (16), including safe error diagnostics. A live invalid model ID returned upstream `400` and PROXI `502`. Protected dispatch failed closed for adapter unavailability in the enforcement tests. A complete provider outage was not rehearsed. |

## Security testing

- **Passed, scoped:** expired JWT and wrong signature rejection, owner authentication and fail-closed configuration, malformed model proposals and prompt-injection schema constraints, browser renderer isolation, and Chrome companion pairing restrictions. The operator's PostgreSQL runs covered agent/session binding, expiration and revocation, capability and resource scope, explicit denial, policy revisions, approval replay and races, and owner-scoped audit visibility. Schema validation does not prove semantic alignment with the task.
- **Not confirmed:** full-suite PostgreSQL results, unskipped MCP and database-backed Chromium flight cases, and end-to-end suspension against a live adapter. See the [test log](../logbook/TEST_LOG.md#prompt-16) for the initial run. A static route review does not establish that arbitrary bypasses are impossible.
- **Known limits:** Loopback owner auth is not production auth. Direct website/tool access is outside the boundary. Allowlisted browser GET endpoints must be trusted and read-only; deployment egress controls remain the operator's responsibility. External adapter effects may occur before durable audit commit. No penetration test or new exploit reproduction was performed.

## Performance and reliability

| Measure | Observed |
| --- | --- |
| Backend cold start | Three loopback Uvicorn launches without a configured database: HTTP 200 after 2,366 ms, 2,030 ms, and 2,030 ms (median 2,030 ms). Liveness only. |
| Frontend | Production build and TypeScript passed; one built-server browser smoke passed against a fixture API (2.82 s scenario, 3.25 s runner). Not an action-latency sample. |
| Backend regression | Initial run: 37 passed, 52 skipped, 0 failed in 30.72 s. Follow-up targeted results are listed by layer above; no complete backend rerun or comparable timing was reported. |
| Authz/action latency, approval processing, revocation propagation, runtime errors, code coverage | Not measured. Database-backed workflow timings and instrumented coverage are still needed. |

## Demonstration and next steps

Follow the [demonstration runbook](DEVELOPMENT.md#prompt-16-demonstration) for the flight scenario, scripted denial, audit inspection, and revocation. It uses synthetic fares and scripted site instructions. Label mocked DeepSeek tests separately from the live proposal POST. MCP is one built-in catalog tool; the Chrome companion is optional and read-only.

1. Run the complete backend suite against disposable PostgreSQL, including Prompt 15 workspace persistence. Record the skip count and explicitly confirm the MCP and database-backed Chromium flight cases ran.
2. Confirm the proposal GET returns the ID created by the live DeepSeek POST. Rehearse the complete local workflow: task submission, proposal review, policy and capability provisioning, browser dispatch, dashboard audit visibility, and revocation.
3. Measure representative authorization, dispatch, approval, revocation, and error rates with the database enabled; collect instrumented coverage. For production use, separately address owner authentication, egress isolation, transactional audit limitations, and dependency-boundary deviations.

Passing local MVP tests would not establish production security.
