# Master log

Append entries in prompt execution order. Dates below use local time; historical entries distinguish the first commit evidence from the original session date when it is unknown.

## Prompt 00 — Master project instructions

- **Date:** Original session date not recorded; first committed evidence is November 22, 2026 (`010dbbb`, which also contains Prompt 01).
- **Objective:** Save the master instructions and identify the repository baseline without implementing the app.
- **Implementation summary:** Recorded the fixed stack, layer boundaries, security invariants, and session workflow. The [Prompt 01 audit](../docs/ARCHITECTURE.md#repository-audit) describes the baseline before scaffolding.
- **Files created:** [Master prompt](../PROXI_MASTER_PROMPT.md).
- **Files modified:** None attributable to Prompt 00 in available evidence.
- **Tests executed:** No application test execution recorded.
- **Result:** Master prompt was present at the start of Prompt 01; no separately attributable application work.
- **Issues encountered:** No separate commit or test record identifies the original Prompt 00 session.
- **Next task:** Prompt 01 — repository audit and architecture setup.

## Prompt 01 — Repository audit and architecture setup

- **Date:** November 22, 2026 (commit `010dbbb`).
- **Objective:** Audit the repository and set up the backend, frontend, and architecture boundaries.
- **Implementation summary:** Added a FastAPI app factory, liveness route, settings, structured logging and error handling; scaffolded domain and adapter packages and a Next.js placeholder.
- **Files created:** [Backend](../backend/), [frontend](../frontend/), root environment and ignore examples, README, product docs, and initial logbook. The master prompt first appears in the same commit but is attributed to Prompt 00 above.
- **Files modified:** [Agent instructions](../AGENTS.md).
- **Tests executed:** Pytest, import/boundary checks, Uvicorn and Next.js smoke checks, frontend build, shadcn/ui detection, and dependency audit; see [historical results](TEST_LOG.md#prompt-01).
- **Result:** Foundation scaffold verified; domain features remained unimplemented. See the [original checkpoint](phases/01-repo-audit-and-architecture.md).
- **Issues encountered:** Four moderate development dependency advisories; see [KI-001](KNOWN_ISSUES.md#ki-001--shadcn-development-dependency-advisories).
- **Next task:** Prompt 02 once authorized; Prompt 01.5 was subsequently recorded as separate UI foundation work.

## Prompt 01.5 — UI foundation and future enhancement planning

- **Date:** November 22, 2026 (commit `08ab83c`).
- **Objective:** Define the UI foundation without implementing the dashboard.
- **Implementation summary:** Introduced a reusable shell, system light/dark tokens and a skip link; documented screen and component plans.
- **Files created:** [Frontend design docs](../docs/frontend/), [app shell](../frontend/src/components/layout/app-shell.tsx), and [tokens](../frontend/src/styles/tokens.css).
- **Files modified:** [Development guide](../docs/DEVELOPMENT.md), frontend [global CSS](../frontend/src/app/globals.css), [layout](../frontend/src/app/layout.tsx), and [page](../frontend/src/app/page.tsx); status, master and test logs.
- **Tests executed:** Production build, loopback smoke check, browser spot check and palette contrast check; see [historical results](TEST_LOG.md#prompt-015).
- **Result:** UI foundation verified within the recorded scope; dashboard not implemented.
- **Issues encountered:** Native Tab/Enter interaction was not confirmed; see [KI-002](KNOWN_ISSUES.md#ki-002--native-keyboard-verification-pending).
- **Next task:** Prompt 02 — documentation and logbook.

## Prompt 02 — Documentation & Markdown Logbook System

- **Date:** November 22, 2026.
- **Objective:** Make progress, historical verification and next steps recoverable from the repository alone.
- **Implementation summary:** Expanded the six root logbook records, added nine phase checkpoints, preserved the original audit record, and documented mandatory session startup and shutdown.
- **Files created:** Nine `PHASE_00` through `PHASE_08` checkpoint files in [phases](phases/).
- **Files modified:** [Master log](MASTER_LOG.md), [current status](CURRENT_STATUS.md), [changelog](CHANGELOG.md), [architecture decisions](ARCHITECTURE_DECISIONS.md), [test log](TEST_LOG.md), [known issues](KNOWN_ISSUES.md), [development guide](../docs/DEVELOPMENT.md), and [README](../README.md).
- **Tests executed:** See [Prompt 02 verification](TEST_LOG.md#prompt-02); no application suites run for this documentation-only change.
- **Result:** Acceptance met: required records, entry structure and local links verified; no application behavior added.
- **Issues encountered:** No standalone Prompt 00 commit or original execution transcript; historical claims are limited to available Git and logbook evidence.
- **Next task:** Prompt 03 — database foundation, only when explicitly supplied.

## Prompt 03 — Database & Domain Models

- **Date:** 2026-11-22.
- **Objective:** Establish persistence for the 20 domain records with Supabase PostgreSQL, SQLAlchemy and Alembic.
- **Implementation summary:** Added transactional persistence, repository ports and adapters, the private schema and initial revision. Retain audit references and keep testing isolated from development and hosted data.
- **Files created:** [Domain records](../backend/app/models/records.py), [repository ports](../backend/app/core/repositories.py), database [engine](../backend/app/infra/db/database.py) and [mappings](../backend/app/infra/db/models.py), [SQLAlchemy adapter](../backend/app/infra/repos/sqlalchemy.py), [Alembic configuration](../backend/alembic.ini) and [migrations](../backend/migrations/), [database tests](../backend/app/tests/test_database.py), and [ADR D-004](../docs/adr/0004-supabase-postgresql.md).
- **Files modified:** Backend settings, lifespan and requirements; environment example, [master instructions](../PROXI_MASTER_PROMPT.md), database, architecture and development guides; affected logbook records and database checkpoint.
- **Tests executed:** 11 backend tests passed on disposable local PostgreSQL 18.4; Alembic upgrade and drift check passed. See [Prompt 03 verification](TEST_LOG.md#prompt-03).
- **Result:** Local acceptance met. Agent registration and authorization logic were not implemented.
- **Issues encountered:** Database settings were missing at preflight. Resolved by the approved switch from SQLite to Supabase PostgreSQL and the addition of configuration. No hosted credentials supplied; hosted connection and migration not run.
- **Next task:** Prompt 04 — identity and agent registration, only when explicitly supplied.

## Prompt 04 — Agent Identity Management

- **Date:** 2026-11-22.
- **Objective:** Persist uniquely identified agents and manage their lifecycle through owner-scoped operations.
- **Implementation summary:** Added registration, listing, lookup, update, and revocation. The identity service rejects non-active agents during status validation and prevents ordinary updates to revoked agents. The management API is disabled by default and supports only the documented local operator boundary.
- **Files created:** [Agent API](../backend/app/api/agents.py), [schemas](../backend/app/schs/agents.py), [service](../backend/app/svcs/identity.py), [lifecycle rules](../backend/app/core/identity/lifecycle.py), and [revision 0002](../backend/migrations/versions/0002_agent_identity.py).
- **Files modified:** [Settings](../backend/app/config.py), [app wiring](../backend/app/main.py), [records](../backend/app/models/records.py), [repository ports](../backend/app/core/repositories.py), [ORM mappings](../backend/app/infra/db/models.py), [repository adapter](../backend/app/infra/repos/sqlalchemy.py), [app tests](../backend/app/tests/test_app.py), [database tests](../backend/app/tests/test_database.py), [environment example](../.env.example), development, security, architecture, and database guides, and affected logbook records.
- **Tests executed:** 15 backend tests passed on disposable PostgreSQL 18.4; migration upgrade and drift check passed. See [Prompt 04 verification](TEST_LOG.md#prompt-04).
- **Result:** Local acceptance met. `last_seen_at` remains unset until there is a trusted source of agent activity. No session, credential, or capability behavior was added.
- **Issues encountered:** The first scratch validation attempt stopped before executing tests because the bundled PostgreSQL package lacked `pg_isready`; the retry used `pg_ctl -w` and a loopback connection probe. Hosted rollout and production user authentication were not verified.
- **Next task:** Prompt 05, only when explicitly supplied.

## Prompt 05 — Session & Capability Management

- **Date:** 2026-11-22.
- **Objective:** Require valid agent identity, session, short-lived credential, and task-scoped capability before considering authorization.
- **Implementation summary:** Added local owner-scoped lifecycle endpoints, a PyJWT credential codec, and a prerequisite check. Revocation remains enforceable from persistent records without storing bearer tokens.
- **Files created:** [Access API](../backend/app/api/access.py), [owner bearer dependency](../backend/app/api/owner_auth.py), [schemas](../backend/app/schs/access.py), [service](../backend/app/svcs/access.py), [token port](../backend/app/core/creds/tokens.py), [JWT adapter](../backend/app/infra/creds/jwt.py), and [revision 0003](../backend/migrations/versions/0003_session_access.py).
- **Files modified:** App wiring, configuration, requirements, persistence and identity adapters, [backend tests](../backend/app/tests/), [environment example](../.env.example), API, database, development and security docs, and logbook records.
- **Tests executed:** 18 backend tests passed against disposable PostgreSQL 18.4. Alembic upgrade and drift check passed. See [Prompt 05 verification](TEST_LOG.md#prompt-05).
- **Result:** The prerequisite gate rejects invalid, expired, revoked, or misbound access and grants no execution authority.
- **Issues encountered:** Hosted rollout and production owner authentication were not verified. No Gemini, policy engine, or protected execution was added.
- **Next task:** Stop at Prompt 05 pending explicit authorization.

## Prompt 06 — DeepSeek Intent Interpretation

- **Date:** 2026-11-22.
- **Objective:** Interpret natural-language tasks into advisory permission proposals for explicit owner review.
- **Implementation summary:** Added a configurable [DeepSeek adapter](../backend/app/infra/llm/deepseek.py), strict [intent schemas](../backend/app/schs/intent.py), a [proposal service](../backend/app/svcs/intent.py), and [owner-scoped endpoints](../backend/app/api/intent.py). [Revision 0004](../backend/migrations/versions/0004_intent_proposals.py) stores proposals and classified failures.
- **Files modified:** App composition, settings, persistence, dependencies, tests, environment example, API and architecture docs, and logbook.
- **Tests executed:** 33 backend tests passed with mocked DeepSeek on disposable PostgreSQL 18.4; migration round-trip and schema drift checks passed. See [verification](TEST_LOG.md#prompt-06).
- **Result:** Successful proposals are retrievable for review; schema-valid model suggestions are not authorization, and failures do not change existing policy.
- **Issues encountered:** Live DeepSeek and hosted PostgreSQL were not tested.
- **Next task:** Stop at Prompt 06. Policy evaluation and enforcement were not implemented.

## Prompt 07 — Policy Management Engine

- **Date:** 2026-11-23.
- **Objective:** Store owner-approved security policies independently of the intent model.
- **Implementation summary:** Added [policy management](../backend/app/svcs/policies.py), [lifecycle validation](../backend/app/core/policies/lifecycle.py), [request and response schemas](../backend/app/schs/policies.py), and [owner endpoints](../backend/app/api/policies.py). [Revision 0005](../backend/migrations/versions/0005_policy_management.py) stores fixed scope and version snapshots.
- **Files modified:** Application wiring, record and repository contracts, SQLAlchemy mappings and adapter, tests, API/database/security docs, and logbook.
- **Tests executed:** All 36 backend tests passed on disposable PostgreSQL 18.7. Migration round-trip passed; Alembic reported no drift. See [verification](TEST_LOG.md#prompt-07).
- **Result:** Owned validated proposals convert deterministically to drafts. Explicit version approval activates policy; replacement and revocation preserve history. This does not authorize operations.
- **Issues encountered:** Hosted deployment and production owner authentication were not tested; the API uses the local owner bearer.
- **Next task:** Stop at Prompt 07. Await authorization to implement deterministic RBAC/ABAC evaluation.

## Prompt 08 — Authorization & Enforcement Engine

- **Objective:** Centralize deterministic decisions and enforce them independently of integrations.
- **Implemented:** Normalized action requests, ordered security checks, JWT-bound check endpoint, and synchronous adapter dispatch after fresh authorization under the agent lock.
- **Verified:** 53 backend tests passed on disposable PostgreSQL 18.7, including migration round-trip and revocation between checks. Alembic found no schema drift.
- **Remaining:** The controller requires an injected decision recorder. No production audit sink, action approval interface, browser/MCP adapter, or hosted rollout was added.
- **Next task:** Stop at Prompt 08 and await further instructions.

## Prompt 09 — Human Approval System

- **Objective:** Make enforcement holds reviewable without granting unconditional execution authority.
- **Implemented:** Persisted action and policy-gate snapshots, owner-only review and history, and durable single-use claims before fresh authorization. See the [approval API](../docs/API.md#action-approvals) and [revision 0006](../backend/migrations/versions/0006_action_approvals.py).
- **Verified:** 61 backend tests passed on disposable PostgreSQL 18.7. Migration round-trip passed and Alembic found no schema drift. See [Prompt 09 verification](TEST_LOG.md#prompt-09).
- **Stop point:** No trust scoring, dashboard UI, production execution adapter, or hosted rollout.

## Prompt 10 — Behaviour Analysis & Dynamic Trust Engine

- **Implemented:** Deterministic behaviour analysis, persisted evidence, configurable scores and bands, authorization restrictions, and controlled recovery. See the [trust rules and enforcement](../docs/SECURITY.md#behaviour-analysis-and-dynamic-trust) and [revision 0007](../backend/migrations/versions/0007_dynamic_trust.py).
- **Verified:** 73 backend tests passed on disposable PostgreSQL 18.7. Migration round-trip passed and Alembic detected no schema drift. See [Prompt 10 verification](TEST_LOG.md#prompt-10).
- **Stop point:** No dashboard visualizations, hosted rollout, or production executor.

## Prompt 11 — Audit Logging & Security Monitoring

- **Implemented:** Synchronous in-process events, transactional audit and security records, and [owner-only monitoring endpoints](../docs/API.md#audit-and-security-monitoring) with filtering and correlation. Added the event bus, monitoring service, API and schemas, and [revision 0008](../backend/migrations/versions/0008_security_monitoring.py); updated operation producers, mappings, tests, and documentation.
- **Verified:** 75 backend tests passed on disposable PostgreSQL 18.7. Migration round-trip passed and Alembic detected no schema drift. See [Prompt 11 verification](TEST_LOG.md#prompt-11).
- **Integrity:** Application interfaces are append-only. Privileged database or file access can bypass application controls; neither PostgreSQL nor SQLite history is independently tamper-evident. See the [security notes](../docs/SECURITY.md).
- **Stop point:** No dashboard, external broker, hosted rollout, or production execution adapter. Wait for the next authorized prompt.

## Prompt 12 — Playwright Browser Integration

- **Implemented:** Added [browser API](../backend/app/api/browser.py), [browser schemas](../backend/app/schs/browser.py), and [Playwright adapter](../backend/app/integrations/browser/playwright.py). Updated the shared bearer binding and enforcement, app wiring, scope configuration, dependencies, tests, and documentation. No migration was added.
- **Verified:** The [flight-fare demo](../docs/DEVELOPMENT.md#controlled-browser-demo) permitted navigation and approved reading, blocked scripted purchase and disclosure requests, and verified both blocks in owner-visible audit history. All 77 backend tests passed; the disposable database was stopped and removed. See [Prompt 12 verification](TEST_LOG.md#prompt-12).
- **Security:** Only exact-page navigation and reading are supported. Fresh offline Chromium contexts do not share browser state. The demo shows policy enforcement, not general prompt-injection detection or protection for traffic that bypasses PROXI.
- **Stop point:** No Chrome extension, live travel site test, or hosted rollout. Wait for the next authorized prompt.

## Prompt 13 — MCP & Local Agent Integration

- **Implemented:** Added [tool routes](../backend/app/api/integrations.py), [request and response schemas](../backend/app/schs/integrations.py), a [trusted integration registry](../backend/app/svcs/integrations.py), the [Python MCP SDK gateway](../backend/app/integrations/mcp/gateway.py), and a [local catalog adapter](../backend/app/integrations/local_agent/catalog.py). Updated startup wiring, configuration, dependencies, tests, and operator documentation. No database migration was added.
- **Verified:** A real MCP SDK tool call and a local lookup returned the read-only catalog entry only after authorization. The tests confirmed that denial, out-of-scope requests, missing capability, session expiry, revocation, and pending approval did not dispatch. They also covered single-use approval and sanitized server failures. See [Prompt 13 verification](TEST_LOG.md#prompt-13).
- **Security:** Both integrations start disabled, with fixed identity and resource scope. Tool descriptions do not affect authorization. Registry changes are process-local. No shell execution, unrestricted file access, generic MCP listener, or protection for out-of-gateway traffic.
- **Stop point:** No other integrations, hosted rollout, or UI changes. Wait for the next explicitly authorized prompt.

## Prompt 14 — PROXI Dashboard & Frontend

- **Date:** 2026-11-24.
- **Implementation:** Built ten dashboard screens, owner sign-in, dark/light themes, audit filters, monitor refresh, and backend-backed management forms. Added four owner-scoped, non-cacheable backend dashboard reads.
- **Files:** Added dashboard frontend features, route, loading UI, shared controls and contracts, smoke test, and backend dashboard router, service, and schemas. Updated integration status support, backend tests, API and development docs, and the [frontend checkpoint](phases/PHASE_07_FRONTEND.md).
- **Security:** The owner bearer stays in an HttpOnly cookie and is forwarded server side. React does not authorize actions. Dashboard approvals never dispatch; the backend revalidates a later retry. Integration connectivity is reported as unknown without probes.
- **Result:** `TESTING`. Production build and frontend loopback browser smoke passed. Focused backend checks passed where runnable; persisted verification and one earlier backend browser renderer failure are recorded in the [test log](TEST_LOG.md#prompt-14).
- **Stop point:** Verify persisted reads and writes using disposable PostgreSQL before acceptance. No dedicated browser launcher or Chrome extension; wait for explicit authorization.

## Entry template

- **Date:** YYYY-MM-DD (note source for historical entries).
- **Prompt number:** Number and title in the entry heading.
- **Objective:** Intended scope.
- **Implementation summary:** Changes actually made.
- **Files created:** Paths, or none.
- **Files modified:** Paths, or none.
- **Tests executed:** Commands or links to test IDs, or none.
- **Result:** Outcome and acceptance evidence.
- **Issues encountered:** Blockers, limitations or issue IDs, or none.
- **Next task:** Recommended prompt or follow-up; not authorization.
