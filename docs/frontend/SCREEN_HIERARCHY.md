# Preliminary screen hierarchy

Only `/` exists today: a static foundation page, not the Overview Dashboard. Routes below are proposals, not links exposed by the shell. Bracketed segments are dynamic route parameters. The [API](../API.md) currently exposes liveness only; every domain API dependency below is planned.

| Screen / proposed route | Purpose and main information | Main interactions | Backend dependencies | Reusable components |
| --- | --- | --- | --- | --- |
| Overview Dashboard `/overview` | Summarize agent activity, unresolved approvals, and recent security decisions | Filter time range; drill into a real event, agent, or approval | Read models from agents, approvals, enforcement, audit | Agent status card, decision badge, activity timeline |
| Agent Management `/agents` | Find agents and see identity, session and capability summaries | Search, filter, open details; submit authorized enrollment or revocation | Identity, sessions, capabilities | Agent status card, permission summary, confirmation |
| Agent Details `/agents/[agentId]` | Inspect one agent's identity, scope, advisory trust and activity | Review history; submit authorized scope or session changes | Identity, sessions, capabilities, trust, audit | Permission summary, trust indicator, activity timeline |
| Policy Management `/policies` | List policy scopes, versions and lifecycle states | Search, open editor; request authorized publishing or retirement | Policies and policy history | Policy summary, confirmation, status badge |
| Policy Editor `/policies/[policyId]/edit` | Review and edit rule drafts, validation messages and version differences | Edit draft; submit validation, save and publish requests | Policies, server validation, authorization and version checks | Policy summary, field errors, confirmation |
| Approval Center `/approvals` | Review held actions, request details, scope and expiry | Approve or reject eligible requests; refresh actual outcome | Approvals, policy, enforcement, audit | Approval request card, decision badge, risk indicator |
| Security Monitor `/security` | Triage security events by severity, source and timestamp | Filter, inspect, navigate to supporting records | Security events, enforcement, audit | Security event item, risk indicator, timeline |
| Trust & Behaviour Analysis `/trust` | Inspect advisory trust, evidence, recency and behavior trends | Filter by agent/time; inspect contributing events | Trust, behaviour, audit | Trust indicator, activity timeline, risk indicator |
| Audit Logs `/audit` | Find traceable request, decision and execution records | Search/filter by time, actor and correlation ID; inspect records | Audit read models and scoped pagination | Audit log entry, decision badge, empty state |
| Integration Management `/integrations` | Inspect adapter status, scopes and configuration metadata | Submit authorized setup, connection checks or disconnect requests | Browser/MCP/local adapters, capabilities, credentials via redacted metadata | Permission summary, status badge, confirmation |
| PROXI Browser `/browser` | Surface controlled browsing context, proposed actions and outcomes | Review action scope and request a backend action; open a relevant HOLD in approvals | Browser integration and the common identity, policy, enforcement and audit pipeline | Decision badge, approval card, activity timeline |
| Settings `/settings` | View user preferences and authorized workspace configuration | Save preferences; confirm sensitive changes | Settings APIs and backend authorization for protected changes | Form fields, inline errors, confirmation |

Group Agent Details and Policy Editor under their parent sections. Keep the Overview read-only initially and link to dedicated task views for mutations. Final routing and navigation groupings depend on backend contracts and usability findings.
