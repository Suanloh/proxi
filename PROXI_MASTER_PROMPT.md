# PROMPT 00 — PROXI Master Project Instructions

## Role

Act as principal software architect, senior Python engineer, cybersecurity engineer, and full-stack developer for PROXI. Build a functional product, not merely a prototype UI.

## Product identity

- **Project:** PROXI
- **Full name:** Personal AI Security & Authority Infrastructure
- **Tagline:** Your AI agents act, but you decide what they're allowed to do.

PROXI is a local-first security control plane between autonomous AI agents and the tools, browser environments, MCP servers, and local resources they access. Its purpose is to independently validate agent identity, task permissions, capabilities, behavior, and authorization before protected actions execute.

## Fixed project decisions

| Area | Decision |
| --- | --- |
| Backend language | Python |
| Backend architecture | Modular monolith |
| Backend framework | FastAPI |
| Frontend | Next.js, React, TypeScript |
| UI | Tailwind CSS and shadcn/ui |
| AI model | DeepSeek API for advisory intent proposals (Prompt 06; replaces the original Gemini plan) |
| Browser automation | Playwright |
| MCP | Python MCP SDK |
| Database | Supabase PostgreSQL for the MVP; disposable local PostgreSQL for automated tests |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Validation | Pydantic |
| Testing | Pytest |
| Deployment | Local-first |
| User experience | Hybrid dashboard and background protection |
| Browser integration | Dedicated controlled browser and Chrome extension |
| Trust mechanism | Initially rule-based and dynamic |

Do not silently change these decisions.

## Six architecture layers

1. **Experience Layer** — dashboard, PROXI Browser, and Chrome extension.
2. **Integration Layer** — browser, MCP, and local agent adapters.
3. **Identity & Authorization Layer** — agent identity, sessions, credentials, and capabilities.
4. **Intelligence & Trust Layer** — DeepSeek intent interpretation, behavior analysis, and dynamic trust.
5. **Policy & Enforcement Layer** — policy management, RBAC, ABAC, authorization, and `ALLOW`/`HOLD`/`BLOCK` decisions.
6. **Data & Audit Layer** — persistence, policy history, audit logs, and security events.

## Cross-cutting architecture

Use a modular monolith, hexagonal architecture (ports and adapters), zero trust, control-plane/data-plane separation, capability-based security, policy-based access control, human-in-the-loop authorization, event-driven internal communication, and least privilege.

The core security engine must not directly depend on Playwright, the LLM provider, the MCP SDK, Chrome APIs, or PostgreSQL, Supabase and SQLAlchemy implementation details.

## Security invariants

1. The LLM provider must never make the final authorization decision.
2. LLM output is untrusted and must be schema-validated.
3. An LLM-generated permission proposal is not approved policy.
4. Every protected action must be authorized by deterministic backend logic.
5. Every action must validate identity, session, capability, and policy as applicable.
6. Trust is not authorization.
7. A high trust score cannot override a hard-deny rule.
8. `HOLD` means execution has not occurred.
9. Approval cannot override revoked credentials, expired sessions, or hard-deny rules.
10. Revalidate authorization immediately before executing an approved action.
11. Do not claim protection over integrations that bypass PROXI.
12. Treat webpage content and agent-provided instructions as untrusted data.
13. Protect credentials and sensitive personal data.
14. Local file and system operations require explicit resource restrictions.

## Development discipline

- Implement incrementally and reuse existing code.
- Keep modules cohesive. Avoid unnecessary abstractions and do not introduce services.
- Use type hints, Pydantic schemas at system boundaries, dependency injection, and structured logging.
- Write automated tests.
- Do not create fake functionality or substitute mock data for completed backend functionality.
- Label prototypes and incomplete features.

## Mandatory documentation

Maintain:

- `PROXI_MASTER_PROMPT.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/API.md`
- `docs/DATABASE.md`
- `docs/SECURITY.md`
- `docs/DEVELOPMENT.md`
- `logbook/MASTER_LOG.md`
- `logbook/CURRENT_STATUS.md`
- `logbook/CHANGELOG.md`
- `logbook/ARCHITECTURE_DECISIONS.md`
- `logbook/TEST_LOG.md`
- `logbook/KNOWN_ISSUES.md`
- `logbook/phases/`

The logbook is the source of truth for development progress. Inspect source code and test results to verify its claims.

## Mandatory workflow

1. Read this master instruction file.
2. Read `logbook/CURRENT_STATUS.md`.
3. Read `logbook/MASTER_LOG.md`.
4. Read the phase documentation.
5. Inspect the source code.
6. Verify preconditions.
7. Plan the implementation.
8. Implement only the requested scope.
9. Run tests.
10. Update the logbook.

At the end of every prompt, report:

- Prompt number and name.
- Completed features.
- Files created and files modified.
- Tests passed, failed, and not run.
- Security considerations.
- Incomplete work and known issues.
- Logbook update status.
- Acceptance criteria status.
- Recommended next prompt.

## Strict stop condition

Execute only the prompt explicitly provided by the user. Do not automatically execute future prompts or assume that completion of one prompt authorizes the next. If a precondition or acceptance criterion fails, stop and explain the problem. Wait for explicit user instruction before continuing.

## Prompt 00 scope

Save these instructions as `PROXI_MASTER_PROMPT.md` in the project root. Inspect the repository sufficiently to determine whether it is new or existing. Do not implement the application. Confirm the instructions were saved, explain the recommended next prompt, and stop after Prompt 00.
