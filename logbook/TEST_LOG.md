# Test log

Append one row per check. Use `PASS` only when execution confirms the expected result, `FAIL` when it does not, and `NOT RUN` when no result was obtained. Prompts 01 and 01.5 below preserve previously recorded executions; Prompt 02 did not rerun them. Exact historical commands are not reconstructed where the original record did not capture them.

## Prompt 00

| Test ID | Description | Expected result | Actual result | Status | Implementation / execution method | Follow-up action |
| --- | --- | --- | --- | --- | --- | --- |
| P00-01 | Application suites | Not applicable to saving instructions | No application test execution recorded | NOT RUN | Documentation-only scope | None |

## Prompt 01

| Test ID | Description | Expected result | Actual result | Status | Implementation / execution method | Follow-up action |
| --- | --- | --- | --- | --- | --- | --- |
| P01-01 | Backend tests | Versioning, safe errors and environment settings checks succeed | 5 passed; covered validation and unexpected errors, profile isolation/precedence and invalid profile rejection | PASS | Pytest on Python 3.12.10 | None |
| P01-02 | Backend import boundaries | Modules import without cycles or forbidden core imports | 34 modules imported; no local cycles or forbidden core imports | PASS | Backend import/boundary check | None |
| P01-03 | Live liveness | HTTP 200, expected JSON and structured startup event | HTTP 200, `{"status":"ok"}` and startup event observed | PASS | Live Uvicorn smoke test | None |
| P01-04 | Frontend build | Production compilation, Tailwind and TypeScript succeed | All three succeeded | PASS | Next.js build on Node.js 24.11.1 | None |
| P01-05 | Production frontend and backend URL override | Placeholder renders; server-only client reaches backend with override | HTTP 200, placeholder rendered and backend call succeeded with override | PASS | Live Next.js and FastAPI smoke test | None |
| P01-06 | UI tool configuration | CLI detects framework, CSS and aliases | Detected App Router, React Server Components, Tailwind v4 and aliases | PASS | shadcn/ui CLI | None |
| P01-07 | Production dependency advisories | No production advisories reported | None reported for production; four moderate development advisories reported | PASS | npm audit; status applies only to production advisory check | Track [KI-001](KNOWN_ISSUES.md#ki-001--shadcn-development-dependency-advisories) |
| P01-08 | Development-mode frontend smoke | Placeholder responds in dev mode | Not separately smoke-tested | NOT RUN | Next.js development server | Run when validating a development startup change |
| P01-09 | Browser automation and domain features | With implementations present, exercise controlled actions end to end | Implementations not present; no such tests executed | NOT RUN | No harness used | Add tests in the applicable feature prompts |

## Prompt 01.5

| Test ID | Description | Expected result | Actual result | Status | Implementation / execution method | Follow-up action |
| --- | --- | --- | --- | --- | --- | --- |
| P015-01 | Production build | Compilation, Tailwind, TypeScript and static prerender succeed | All succeeded | PASS | Next.js production build on Node.js 24.11.1 | None |
| P015-02 | Production loopback smoke | `/` returns HTTP 200 with placeholder and shell assets | HTTP 200; placeholder, skip link target, theme media query and decision tokens observed | PASS | Production loopback smoke test | None |
| P015-03 | Browser spot check | OS themes work, layout fits 320px, programmatic skip link focuses `main` | Both themes applied; no horizontal overflow at 320px; programmatic focus succeeded | PASS | Integrated browser | Native keyboard coverage tracked separately |
| P015-04 | Palette contrast | Sample text pairs in both themes and report minimums | Lowest sampled ratios: 7.12:1 in light and 8.32:1 in dark, including decision pairs | PASS | Palette contrast check | Recheck if tokens change |
| P015-05 | Change scope | No backend, dependency or tooling configuration changes | No such changes recorded | PASS | Change scope inspection | None |
| P015-06 | Native keyboard and accessibility audit | Tab reaches skip link, Enter moves focus to `main`; audit remaining shell behavior | Native Tab/Enter behavior was not verified; full audit not run | NOT RUN | Programmatic activation in P015-03 is not native keyboard coverage | Track [KI-002](KNOWN_ISSUES.md#ki-002--native-keyboard-verification-pending) |

## Prompt 02

| Test ID | Description | Expected result | Actual result | Status | Implementation / execution method | Follow-up action |
| --- | --- | --- | --- | --- | --- | --- |
| P02-01 | Logbook acceptance and scope | 15 required records exist, entries have required fields, local links resolve, and changes are documentation-only | Verified 15 required records, 4 prompt entries, 18 test records and 89 local links/anchors; Markdown-only diff and whitespace check passed | PASS | PowerShell file, section, table, link and heading checks; `git diff --name-only HEAD`, `git ls-files --others --exclude-standard` and `git diff --check HEAD` | None |
| P02-02 | Application regression suites | Not applicable to this documentation-only change | No application suites executed | NOT RUN | No runtime code changed | Run applicable suites when runtime changes resume |

## Prompt 03

| Test ID | Description | Expected result | Actual result | Status | Implementation / execution method | Follow-up action |
| --- | --- | --- | --- | --- | --- | --- |
| P03-01 | Existing backend startup and regression tests | App starts in test lifespan; existing tests pass | 5 passed | PASS | From `backend`: `..\.venv\Scripts\python.exe -m pytest app\tests\test_app.py` | None |
| P03-02 | Initial database configuration preflight | Usable database configuration already available | No backend database setting, local `.env`, or database environment override found | FAIL (resolved) | Inspected settings, environment example, root files and environment variable names | User approved adding PostgreSQL configuration |
| P03-03 | Backend regression, configured startup, migration round-trip, persistence, integrity and isolation | Backend acceptance checks pass without touching hosted or development data | 11 passed on disposable PostgreSQL 18.4 | PASS | From `backend`: `..\.venv\Scripts\python.exe -m pytest app\tests --tb=short` with loopback test DSN | None |
| P03-04 | Migration and schema drift | Upgrade succeeds and ORM metadata agrees with migrated schema | Revision `0001` applied; no new upgrade operations detected | PASS | From `backend`: `..\.venv\Scripts\python.exe -m alembic upgrade head` and `..\.venv\Scripts\python.exe -m alembic check` on disposable local PostgreSQL | None |
| P03-05 | Hosted Supabase connection and migration | Hosted schema accessible with configured permissions | Hosted database not accessed | NOT RUN | No hosted credentials supplied | Verify separately during hosted rollout |

## Prompt 04

| Test ID | Description | Expected result | Actual result | Status | Implementation / execution method | Follow-up action |
| --- | --- | --- | --- | --- | --- | --- |
| P04-01 | Backend regression, identity API and service, legacy migration round-trip | Scoped CRUD and revocation work; duplicates, invalid requests, and non-active identities are rejected; legacy IDs survive | 15 passed on disposable PostgreSQL 18.4 | PASS | From `backend`: `..\.venv\Scripts\python.exe -m pytest app\tests --tb=short` with `PROXI_ENV=testing` and a loopback test DSN | None |
| P04-02 | Alembic upgrade and drift | Upgrade succeeds and ORM metadata matches the result | Head applied; no new upgrade operations detected | PASS | From `backend`: `..\.venv\Scripts\python.exe -m alembic upgrade head` and `..\.venv\Scripts\python.exe -m alembic check` on the same scratch cluster | None |
| P04-03 | Hosted Supabase rollout | Hosted permissions, migration, and startup verified | No hosted database accessed | NOT RUN | Local acceptance uses a disposable cluster, not hosted data | Verify during an authorized rollout |

## Prompt 05

| Test ID | Description | Expected result | Actual result | Status | Implementation / execution method | Follow-up action |
| --- | --- | --- | --- | --- | --- | --- |
| P05-01 | Backend regression and access lifecycle | Valid access passes; missing, expired, revoked, invalidly signed, or misbound access fails | 18 passed on disposable PostgreSQL 18.4 | PASS | From `backend`: `..\.venv\Scripts\python.exe -m pytest app\tests --tb=short` with `PROXI_ENV=testing` and a loopback test DSN | None |
| P05-02 | Alembic upgrade and drift | Revision `0003` applies and ORM metadata matches the schema | Upgrade passed; no new upgrade operations detected | PASS | From `backend`: `..\.venv\Scripts\python.exe -m alembic upgrade head` and `..\.venv\Scripts\python.exe -m alembic check` | None |
| P05-03 | Hosted Supabase rollout | Hosted migration and startup verified | No hosted database accessed | NOT RUN | Verification used disposable PostgreSQL | Verify during an authorized rollout |

## Prompt 06

| Test ID | Description | Expected result | Actual result | Status | Implementation / execution method | Follow-up action |
| --- | --- | --- | --- | --- | --- | --- |
| P06-01 | Backend regression and intent proposal boundary | Consent and ownership are checked; valid output is persisted, invalid output is rejected, and neither proposals nor failures change authority | 33 passed, including malformed JSON, missing fields, provider error, timeout, prompt injection, owner scoping, and persistence | PASS | From `backend`: `..\.venv\Scripts\python.exe -m pytest app\tests --tb=short` with mocked DeepSeek and disposable PostgreSQL 18.4 | None |
| P06-02 | Schema migration and drift | Revision `0004` round-trips and metadata matches the database | Round-trip passed in the test suite; Alembic detected no new upgrade operations | PASS | From `backend`: `..\.venv\Scripts\python.exe -m alembic upgrade head` and `..\.venv\Scripts\python.exe -m alembic check` on disposable PostgreSQL | None |
| P06-03 | Live DeepSeek and hosted PostgreSQL | Verify external deployments separately | Neither service was contacted | NOT RUN | Local verification only | Verify during an authorized rollout |

## Prompt 07

| Test ID | Description | Expected result | Actual result | Status | Implementation / execution method | Follow-up action |
| --- | --- | --- | --- | --- | --- | --- |
| P07-01 | Policy lifecycle, versioning and backend regression | Create deterministic drafts; reject unauthorized operations and invalid transitions; preserve historical snapshots | 36 passed, including canonical conversion, explicit approval, replacement, revocation, expiry and owner isolation | PASS | From `backend`: `..\.venv\Scripts\python.exe -m pytest -q app\tests` with `PROXI_ENV=testing` and disposable loopback PostgreSQL 18.7 | None |
| P07-02 | Migration round-trip and schema drift | Revision `0005` applies and mappings match the schema | Round-trip passed in the suite; Alembic detected no new upgrade operations | PASS | From `backend`: `..\.venv\Scripts\python.exe -m alembic upgrade head` and `..\.venv\Scripts\python.exe -m alembic check` | None |
| P07-03 | Hosted rollout | Verify hosted migrations and endpoints | No hosted database accessed | NOT RUN | Local PostgreSQL only | Verify during an authorized rollout |

## Prompt 08

- **Backend regression:** `pytest -q` — 53 passed on disposable PostgreSQL 18.7. Includes policy conflicts, identity and access prerequisites, scope, approval holds, recorder failure, and session/policy revocation between authorization checks.
- **Schema:** Migration round-trip passed in the backend suite. `alembic upgrade head` and `alembic check` succeeded; no schema drift detected.
- **Scope:** Dispatch was tested with synchronous test adapters. No browser, MCP, hosted database, or production decision sink was exercised.

## Prompt 09

- **Backend regression:** 61 passed on disposable PostgreSQL 18.7 (from `backend`: `..\.venv\Scripts\python.exe -m pytest -q app\tests --tb=short`). Covers no dispatch before review, exact retry, concurrent claims and replay, rejection, cancellation, expiry, hard denial, removed policy gate, and revocation before and after a claim.
- **Schema:** Migration round-trip passed in the suite. `alembic upgrade head` and `alembic check` succeeded with revision `0006`; no new upgrade operations detected.
- **Scope:** Tests used synchronous test adapters and the local owner bearer. No hosted database or production executor was tested.

## Entry template

| Test ID | Description | Expected result | Actual result | Status | Implementation / execution method | Follow-up action |
| --- | --- | --- | --- | --- | --- | --- |
| PNN-XX | Check and scope | Observable criterion | Observed output or reason not run | PASS / FAIL / NOT RUN | Command or manual method and environment | Next action or none |
