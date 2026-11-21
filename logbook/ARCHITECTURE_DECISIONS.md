# Architecture decisions

Phase 01 uses one Python backend process with a composition root and consumer-owned interfaces for future external dependencies. The infrastructure package is named `infra/`. The frontend is a separate loopback process; its backend URL stays server-side. See [Architecture](../docs/ARCHITECTURE.md) for the dependency and data-flow rules.
