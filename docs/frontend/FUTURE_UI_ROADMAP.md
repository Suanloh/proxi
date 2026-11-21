# Future UI roadmap

| Status | Scope |
| --- | --- |
| Implemented | Static `/` placeholder, reusable shell with landmarks and skip link, centralized light/dark colors, semantic Tailwind utilities and focus styling. Existing server-only liveness client remains unchanged and is not wired to the placeholder. |
| Partially implemented | Design system: foundations and decision palettes exist, but security components, manual theme selection, and full accessibility validation do not. Component architecture: layout, styling, UI and API boundaries have a home; navigation and feature composition await real screens. |
| Planned | All twelve views in the [screen hierarchy](SCREEN_HIERARCHY.md), their navigation, domain API integrations, mutations, and [security UI components](COMPONENT_ARCHITECTURE.md). |

## Suggested sequence after explicit approval

1. **Read-only views:** Agree on identity and scoped read contracts. Land accessible navigation only for real routes. Build the Overview, Agent views and Audit Logs with real pagination, filters and distinct unavailable states.
2. **Sensitive workflows:** Once policy and approval contracts exist, add Policy Management/Editor and Approval Center. Test confirmations, stale state, denied and expired requests, and the separation between receipt, decision and execution.
3. **Investigation:** Add Security Monitor and Trust & Behaviour Analysis when event sources and data provenance exist. Validate dense views on narrow screens and keep redacted history traceable.
4. **Integration and preferences:** Add Integration Management, PROXI Browser, and Settings once backend adapter, enforcement and settings contracts are available. Evaluate manual theme selection, saved filters, and notifications against real usage.

Before shipping each slice, verify keyboard use, focus, both themes, responsive behavior, failure states and authoritative refresh after mutations. Use explicitly labeled fixtures only in isolated tests or previews, never as live security data. This roadmap is provisional and does not authorize another phase to start.
