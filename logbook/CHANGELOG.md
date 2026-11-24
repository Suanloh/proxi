# Changelog

Newest prompt first. Describe actual changes, not planned work. Record test outcomes in the [test log](TEST_LOG.md).

## Prompt 13 — MCP & Local Agent Integration

- **Added:** Python MCP SDK gateway and local adapter for one read-only catalog lookup, plus trusted process-local integration management.
- **Security:** Both tools are off by default and use the same credential, capability, policy, approval, revocation, and audit pipeline as controlled browser calls. Neither accepts commands or paths.
- **Testing:** See [Prompt 13 verification](TEST_LOG.md#prompt-13).

## Prompt 11 — Audit Logging & Security Monitoring

- **Added:** In-process lifecycle events, transactional audit persistence, structured security classifications, and filtered owner-scoped read endpoints.
- **Security:** Monitoring history is append-only through the application. Records omit raw credentials and arbitrary request payloads; storage is not tamper-proof.
- **Changed:** Revision `0008` adds structured audit fields, lookup indexes, and links from security events to their source audit records.

## Prompt 08 — Authorization & Enforcement Engine

- **Added:** Normalized action requests, structured authorization decisions, a protected decision-only endpoint, and an enforcement controller with an adapter allowlist and mandatory decision recorder.
- **Security:** Explicit denial overrides grants; `HOLD` and `BLOCK` never dispatch. The controller revalidates immediately before synchronous dispatch and serializes supported revocations against it.

## Prompt 06 — DeepSeek Intent Interpretation

- **Added:** Configurable DeepSeek adapter, validated intent and permission schemas, and owner-scoped submission and review endpoints.
- **Security:** Explicit consent is required before sending non-sensitive task text. Proposals cannot grant authority; failures preserve existing policy and store no proposal.
- **Changed:** Revision `0004` stores structured proposals and classified failures.
- **Testing:** 33 backend tests passed on disposable PostgreSQL 18.4 with mocked DeepSeek; Alembic reported no drift. See [Prompt 06 verification](TEST_LOG.md#prompt-06).

## Prompt 05 — Session & Capability Management

- **Added:** Owner-scoped sessions, revocable five-minute JWT credentials, and session- and task-bound capability grants.
- **Security:** The prerequisite check rejects invalid identity, session, credential, or scope; it does not evaluate policy or execute operations.
- **Changed:** Revision `0003` adds session and task foreign keys without dropping legacy records.
- **Testing:** 18 backend tests passed on disposable PostgreSQL 18.4; Alembic reported no drift. See [Prompt 05 verification](TEST_LOG.md#prompt-05).

## Prompt 04 — Agent Identity Management

- **Added:** Server-assigned agent IDs, four agent types, persisted registration metadata, and five owner-scoped management endpoints.
- **Changed:** Revision `0002` adds agent metadata and migrates legacy statuses. The service rejects inactive, suspended, and revoked identities during active-status validation; revocation is terminal.
- **Security:** The API is disabled by default. Local opt-in requires a bearer secret bound to an active application user. No production authentication or sessions, credentials, or capabilities were added.
- **Testing:** 15 backend tests passed on disposable PostgreSQL 18.4, and Alembic reported no schema drift. See [Prompt 04 verification](TEST_LOG.md#prompt-04).

## Prompt 03 — Database & Domain Models

- **Added:** PostgreSQL engine and transactions, 20 domain records and mappings, repositories, and Alembic revision `0001`.
- **Changed:** Supabase PostgreSQL replaces the planned SQLite stack. Startup accepts optional database configuration without making liveness depend on it.
- **Security:** Restrictive foreign keys preserve audit references; test settings reject hosted DSNs. Registration and authorization are not implemented.
- **Testing:** 11 backend tests passed on disposable local PostgreSQL; see [Prompt 03 verification](TEST_LOG.md#prompt-03). Hosted Supabase was not accessed.

## Prompt 02 — Documentation & Markdown Logbook System

- **Added:** Nine phase checkpoints, log entry templates and mandatory session startup/shutdown instructions.
- **Changed:** Expanded the six root logs; linked the workflow from the README and retained the original Prompt 01 checkpoint.
- **Fixed:** Separated verified behavior, deferred work and verification gaps in the status and test records.
- **Removed:** Nothing.
- **Security:** No runtime change. Clarified that liveness is not protection or readiness and that logs must not contain secrets.
- **Testing:** Added auditable test records with expected and actual results; see [Prompt 02 verification](TEST_LOG.md#prompt-02).

## Prompt 01.5 — UI foundation

- **Added:** Reusable shell, skip link, theme and decision tokens, UI guidelines and a frontend roadmap.
- **Changed:** Applied the shell and tokens to the placeholder.
- **Testing:** Production build, loopback smoke, theme/layout spot checks and contrast checks recorded. Native keyboard behavior was not verified.

## Prompt 01 — Repository audit and architecture setup

- **Added:** FastAPI factory, versioned liveness route, environment settings, JSON logs, centralized error responses and reserved domain/adapter packages.
- **Added:** Next.js shell with TypeScript, Tailwind, shadcn/ui configuration and a server-only health client; startup, architecture, API, security and database scope documentation.
- **Security:** Centralized safe error responses and kept the backend URL server-side. No protected actions implemented; development advisories tracked separately.
- **Testing:** Added backend scaffold tests and recorded import, build, smoke and dependency checks.

## Prompt 00 — Master project instructions

- **Added:** [Master instructions](../PROXI_MASTER_PROMPT.md) covering architecture, security invariants and prompt workflow.

## Prompt 07 — Policy Management Engine

- **Added:** [Owner policy API](../docs/API.md#policy-management) for draft creation, review, explicit approval, revision history and revocation.
- **Changed:** Revision `0005` persists policy scope, version definitions and lifecycle metadata while retaining legacy records.
- **Security:** Provider output remains advisory, and only explicit owner approval of a pending version can activate it. No authorization pipeline was added.
- **Testing:** 36 backend tests passed; Alembic reported no drift. See [verification](TEST_LOG.md#prompt-07).

## Prompt 12 — Playwright Browser Integration

- **Added:** [Controlled browser API](../docs/API.md#controlled-browser) for agent-bound navigation and reading, plus a reproducible [flight-fare demo](../docs/DEVELOPMENT.md#controlled-browser-demo).
- **Security:** Exact-page allow/deny scopes, isolated offline rendering, single-use approval retries, and correlated audit records. Click, fill, and download are unsupported.
- **Testing:** 77 backend tests passed with real Chromium and disposable PostgreSQL. See [verification](TEST_LOG.md#prompt-12).

## Entry template

- **Added:** New capabilities or docs.
- **Changed:** Existing behavior or docs updated.
- **Fixed:** Defects or misleading records corrected.
- **Removed:** Items removed.
- **Security:** Security-relevant changes or advisories.
- **Testing:** New or updated checks and a result link.

Use `None` or omit categories that did not change.
