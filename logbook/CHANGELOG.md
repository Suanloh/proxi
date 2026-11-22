# Changelog

Newest prompt first. Describe actual changes, not planned work. Record test outcomes in the [test log](TEST_LOG.md).

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

## Entry template

- **Added:** New capabilities or docs.
- **Changed:** Existing behavior or docs updated.
- **Fixed:** Defects or misleading records corrected.
- **Removed:** Items removed.
- **Security:** Security-relevant changes or advisories.
- **Testing:** New or updated checks and a result link.

Use `None` or omit categories that did not change.
