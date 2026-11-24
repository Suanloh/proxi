# Architecture decisions

This log is a chronological index of architecture choices and their trade-offs. Link formal decision records under `docs/adr/` when available. Decisions below describe boundaries; they do not certify future implementations.

| ID / prompt | Status | Decision | Alternatives | Rationale | Consequences / evidence |
| --- | --- | --- | --- | --- | --- |
| D-001 / 00 | Superseded by D-004; not implemented | Use SQLite, SQLAlchemy and Alembic for MVP persistence. | A separately managed database service. | Fits a local-first MVP and supports versioned schema changes. | Database phase must implement and verify migrations; health does not depend on storage. See [database scope](../docs/DATABASE.md). |
| D-002 / 00–01 | Accepted | Keep one modular Python backend with hexagonal boundaries, consumer-owned ports and adapter wiring in the composition root. Name infrastructure `infra/`. | Separate backend services; core directly coupled to SDKs or storage. | Keep local deployment simple and isolate deterministic logic from external dependencies. | Add concrete integrations at the edges and keep core independently testable. See [architecture](../docs/ARCHITECTURE.md#hexagonal-boundaries-and-dependency-direction). |
| D-003 / 01 | Accepted | Run the Next.js shell separately on loopback and keep its backend URL server-side. | Publish a browser-side backend URL; serve the UI through FastAPI. | Keep the existing frontend toolchain while avoiding exposure of server-only configuration. | Two local processes; the UI can start without the backend. See [development guide](../docs/DEVELOPMENT.md#frontend). |
| D-004 / 03 | Accepted | [Use Supabase PostgreSQL](../docs/adr/0004-supabase-postgresql.md) with SQLAlchemy and Alembic. | SQLite (D-001). | Approved hosted persistence; local tests exercise the same dialect. | Dedicated `proxi` schema and disposable local test databases. Hosted rollout is not verified. |
| D-005 / 06 | Accepted | Use DeepSeek behind an outbound port for advisory intent proposals, replacing the original Gemini plan. | Original Gemini plan; directly converting model output to policy. | Prompt 06 selects DeepSeek while retaining explicit human review and deterministic authority boundaries. | The model has no tools; validated proposals and classified failures are stored without changing policy or issuing capabilities. See [intent architecture](../docs/ARCHITECTURE.md#advisory-intent-interpretation). |
| D-006 / 12 | Accepted | Fetch exact-page HTML through one bounded request and render in a fresh offline Chromium context. | Let the browser navigate and interact with sites directly. | Keep browser requests and side effects within the authorization boundary. | Only navigation and reading are supported. Operators must allowlist trusted read-only endpoints and restrict network egress. See [browser security](../docs/SECURITY.md#controlled-browser-boundary). |

## Entry template

| ID / prompt | Status | Decision | Alternatives | Rationale | Consequences / evidence |
| --- | --- | --- | --- | --- | --- |
| D-NNN / NN | Proposed / Accepted / Superseded | Chosen boundary or approach | Options considered | Reasons for choice | Trade-offs, implementation state and evidence link |
