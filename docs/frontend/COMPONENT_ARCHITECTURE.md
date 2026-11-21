# Frontend component architecture

## Existing stack and layout

The foundation retains Next.js 16.4.6 App Router, React 19.3.1, strict TypeScript 5.9.x, Tailwind 4.3.5 using its PostCSS plugin and CSS-first theme, and shadcn/ui `radix-nova` with React Server Components and CSS variables. The existing `@/` alias, `cn` utility and `components.json` are unchanged. No shadcn components have been generated.

| Location under `frontend/src` | Responsibility | State |
| --- | --- | --- |
| `app/` | Route files compose screens and own route-level metadata, layout, loading and error boundaries | Root layout and static `/` exist |
| `components/layout/` | Shared shell and landmarks | `AppShell` exists |
| `components/navigation/` | Active-route navigation, breadcrumbs and responsive menus | Planned; add once real routes exist |
| `components/ui/` | Framework-level primitives such as buttons, dialogs and badges | Directory reserved; no primitives yet |
| `components/security/` | Reusable presentational patterns shared across security features | Planned; introduce as real screens adopt them |
| `features/<feature>/` | Page-level screen composition, feature-specific components and view-model mapping | Planned; route files remain thin |
| `styles/` and `app/globals.css` | Theme values and semantic Tailwind aliases | Implemented |
| `lib/api.ts` and `lib/utils.ts` | Server-only HTTP adapter and shared class-name helper, respectively | Implemented; health only |

Default to Server Components for reads and composition. Use small Client Components for interactive controls only. Pass narrow, serializable display models to clients. Renderers do not fetch, mutate, or import server-only adapters; route or feature code maps backend contracts into display values. Add directories when needed rather than empty scaffolding. Keep credentials and non-public URLs server-side; send only fields required to display a screen.

## Requirements from the six logical layers

| Layer | Frontend requirement |
| --- | --- |
| Experience | Offer responsive, accessible control-plane views and controlled browser interfaces; no dead navigation or placeholder metrics. |
| Integration | Display adapter state and scoped configuration from backend endpoints. Browser, MCP and local-agent operations enter through backend adapters. |
| Identity & Authorization | Show identity, session validity and effective capabilities reported by the server; submit privileged changes only through authorized endpoints. |
| Intelligence & Trust | Display advisory trust, provenance and freshness; never use a score to infer permission. |
| Policy & Enforcement | Render decisions and safe reason codes; submit approval, rejection or policy-change intent. Backend evaluates and revalidates before any execution. |
| Data & Audit | Display scoped, redacted audit/security records with server pagination and correlation IDs; no direct database or credential store access. |

These are integration requirements, not six frontend services. See the [backend architecture](../ARCHITECTURE.md) and [security notes](../SECURITY.md).

## Proposed reusable interfaces

Fields describe display models, not API contracts. Create types and components when the first real feature needs them; handle unsupported values and missing data explicitly at the boundary.

| Component | Input and responsibility |
| --- | --- |
| Agent status card | `id`, `name`, server-reported `status`, optional `lastSeenAt`, optional details URL; summarize lifecycle, not permission. |
| Trust score indicator | optional `score`, `scale`, `assessedAt`, `explanation`; label as advisory and show unavailable/stale data. |
| Permission summary | backend-reported list of `capability`, `resource`, `constraints`, optional `expiresAt`; distinguish empty, hidden and unavailable scope. |
| Authorization decision badge | `decision` (`ALLOW`, `HOLD`, `BLOCK`, or `unknown`), optional safe `reason`; map labels and visual tokens, never compute or mutate a decision. |
| Approval request card | `id`, agent, action/scope, expiry, reported status and server-advertised actions; emits approve/reject intent by ID, with separate pending/result feedback. |
| Security event item | `id`, `occurredAt`, `severity`, `source`, safe summary and details link; present one event without inferring its outcome. |
| Audit log entry | timestamp, actor, action, resource summary, decision, execution state and correlation ID; preserve distinct statuses and redaction. |
| Policy summary | `id`, `name`, `version`, scope, lifecycle state and optional link; summarize the recorded policy. |
| Activity timeline | ordered event models with stable IDs and timestamps; render sequence without implying causality. |
| Risk indicator | server-reported `level` and optional safe reason; distinguish unknown risk from low risk, and risk from decision. |
| Empty state | `title`, `description`, optional authorized action; distinguish no records from no matches. |
| Loading state | contextual status label and optional skeleton; preserve layout and expose busy state. |
| Error state | safe message and optional retry callback; do not expose raw errors or offer unsafe retries. |

## Security boundary

Only backend enforcement authorizes actions. The UI displays decisions, trust, policy, permissions and audit records, and submits approval/rejection and configuration requests via authorized APIs. UI affordances are not security controls: never grant permissions locally, offer a BLOCK override, treat high trust as authorization, or treat a successful request as proof of enforcement or execution. Refresh server state after changes, keep execution outcomes separate from decisions, and never put sensitive credentials in source, client bundles, browser storage or display models.
