# PROXI

Personal AI Security & Authority Infrastructure. PROXI includes a local FastAPI enforcement service and a Next.js owner dashboard for managing agents, sessions, policies, and approvals and inspecting trust, audit, and integration status. It is not a hosted deployment.

Start with the [local installation and startup guide](docs/DEVELOPMENT.md#running-locally) and [PostgreSQL setup](docs/DATABASE.md#configuration-and-migrations). The [demonstration runbook](docs/DEVELOPMENT.md#prompt-16-demonstration) covers the controlled flight scenario, MCP catalog, dashboard, browser console, and Chrome companion.

**Prompt 16: MVP acceptance not met.** DeepSeek is the accepted intent provider. This validation run could not execute PostgreSQL-backed scenarios. See the [integration validation report](docs/INTEGRATION_VALIDATION.md), [security boundaries](docs/SECURITY.md), and [current status](logbook/CURRENT_STATUS.md). This is not a production security certification.

Start each development session with the [mandatory handoff workflow](docs/DEVELOPMENT.md#session-workflow).
