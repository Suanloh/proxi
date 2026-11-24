# Security

Run both apps on loopback. Configuration examples contain no credentials. Keep real configuration in ignored env files or process variables; keep the frontend API base URL server-side and credential-free.

The API suppresses raw exception details in responses. Application startup/error events are JSON and do not include request bodies or exception messages. The ASGI server has its own exception and access logs; do not put credentials in URLs or exception text.

Agent identity management is disabled by default. Its [local development opt-in](DEVELOPMENT.md#agent-identity-api-local-development-only) binds a backend-only bearer secret to one active application user and restricts reads and writes to that user's agents. It is not production user authentication. Never provide that secret to agents or expose this boundary beyond loopback.

Registration allocates a server-generated ID; possession of that ID is not proof of agent identity. Agent access uses an HS256 JWT (RFC 7519), signed and verified by PyJWT with a server-pinned algorithm, issuer `proxi`, and audience `proxi-agent-access`. The claims `sub`, `sid`, and `jti` bind the token to its agent, session, and credential record; `iat` and `exp` bound its lifetime. Only an identifier and revocation/expiry metadata are stored, not the bearer token. Treat both bearer tokens and signing keys as secrets; never put them in URLs, logs, or frontend configuration.

The prerequisite gate verifies the credential and requires an active owner, agent and session plus an unexpired, unrevoked capability with the exact requested scope. A successful check does not authorize or execute anything. The [authorization engine](#authorization-and-enforcement) revalidates the prerequisites and applies policies separately.

Policy management uses that same local owner boundary. A provider proposal is never active policy. Drafts and pending versions are excluded from the approved-active state, as are revoked, superseded and legacy unbound versions. Only explicit approval of a specific pending version can activate it. Activation does not grant capabilities or authorize execution.

## Authorization and enforcement

The engine evaluates, in order:

1. Agent identity and active owner, then active agent status.
2. Agent-bound session existence, revocation and expiry, then credential validity and revocation.
3. An active capability for the exact agent, session, pending task, action and resource.
4. Approved active policy snapshots for this owner, agent and task, using server time for approval and validity windows. A malformed eligible snapshot blocks. Draft, pending, revoked, superseded and unbound policies cannot grant access.
5. Explicit action denial in any applicable policy, even if that policy's resource scope or context does not match; then exact resource scope and presence of an applicable policy.
6. Integration role (the registered agent type), action grant, and attribute conditions (exact capability IDs and type-strict trusted context). Client parameters cannot supply trusted context.
7. Configured trust restrictions, then action approval. Any scoped policy whose conditions match can require `HOLD` for an approval-required action or sensitive resource, even when another policy grants the action. Only a request passing these checks receives `ALLOW`.

The first failing check determines the reason. Policy ID order breaks ties for decision attribution, not for permission precedence. Trust can add restrictions but cannot bypass a denial or satisfy an approval.

The controller accepts only explicitly registered integration/action adapters. Before synchronous dispatch it evaluates again in a fresh transaction, calls the required decision recorder, and holds the agent row lock through dispatch. Agent, session, credential, capability, and policy lifecycle mutations share that lock; policy mutations that change active authority take it before the policy lock. The recorder must be synchronous, must not re-enter these mutations, and must not log credentials or raw parameters. If recording fails, dispatch does not start. The controller accepts an injected recorder. The browser API uses transaction-scoped decision and execution events for persistent audit history; it has no independent pre-dispatch audit sink.

Adapters must execute the exact authorized action and resource, validate action-specific parameters, and finish without scheduling deferred work. A `HOLD`, `BLOCK`, or missing adapter does not dispatch. The [browser endpoint](API.md#controlled-browser) dispatches only navigation and reading; the [check endpoint](API.md#authorization-check) never dispatches. No MCP executor is registered.

### Controlled browser boundary

A browser operation requires a credential bound to its agent and session, a matching capability, policy permission, and an exact server-allowed page. A deny-list match wins. Every execution starts a fresh offline, sandboxed Chromium context with scripts, service workers, downloads, and subresource requests disabled. No browser handle or stored browser state is available to the agent. Only one credential-free GET to the exact page is made outside Chromium; redirects are not followed. The response must be bounded HTML. Extracted title and text remain untrusted data: page instructions cannot change policy, grants, consent, or approval state.

A GET is not proof of a read-only server operation. Allowlist only trusted, read-only endpoints; enforce deployment egress controls for private addresses, DNS changes, and other unintended destinations. The adapter does not detect all prompt injection, constrain clients that bypass PROXI, or verify the behaviour of remote servers.

### Behaviour analysis and dynamic trust

Configure the engine with the `PROXI_TRUST_RULES` JSON environment variable. It accepts `initial_score`, `normal_min`, `monitored_min`, `restricted_min`, `restricted_actions`, `predecessors`, `repeat_window_seconds`, `denied_threshold`, `approval_threshold`, `recovery_successes`, `recovery_cooldown_seconds`, and per-rule `weights`. Band minima must strictly increase and scores stay within 0–100.

| Default score | Enforcement |
| --- | --- |
| 80–100 | Normal scoped operation |
| 50–79 | Enhanced monitoring; no additional access restrictions |
| 20–49 | Only actions in `restricted_actions`, subject to all other gates; empty by default |
| 0–19 | Dispatch blocked pending owner review |

The engine compares verified requests against deterministic authorization outcomes, exact action/resource pairs in usable policy-linked proposals, and configured predecessors from the same session and task. Proposals are advisory; missing or unusable proposals do not trigger an intent deviation. It records attributable denials, new approval holds, session anomalies, and execution outcomes. It does not call an LLM or claim to detect all attacks. Invalid credentials cannot penalize another agent; attributable inactive-session events and trust-only denials are audit-only.

Normal operations add 0 points. Defaults subtract 5 for unusual actions, 15 for out-of-scope resources or permission-boundary violations, and 25 for repeated denials instead of stacking the base penalty. Three denials or three separate approval holds within 300 seconds trigger their respective repeat rules. Recovery adds 5 only after at least five distinct successful compliant operations and a 300-second cooldown since the latest violation or adjustment. Review restores at most one band and does not change agent lifecycle or grant access. Each effective score change links to a persisted behaviour event.

### Human approval

Only an actual enforcement `HOLD` creates an approval. It binds the action, parameters, agent, session, capability and ordered policy-gate versions to the original request UUID. The active owner can review the request, but approval does not override a hard denial or dispatch anything by itself.

An exact retry with a registered adapter may claim a valid approval once. The claim commits before fresh deterministic authorization. Dispatch requires `ALLOW`, the same approval gates, and a still-live deadline. Revoked sessions, invalid credentials or capabilities, changed policy gates, rejected, cancelled, or expired requests, and consumed approvals cannot dispatch on that approval. An unsuccessful revalidation or dispatch can leave the approval consumed; this provides at-most-once dispatch attempts, not guaranteed execution. Review responses are not cached. Action parameters are persisted and visible to the owner, so callers must not place bearer tokens or other secrets in them.

## Audit logging and security monitoring

An in-process subscriber records structured identity, session, credential, capability, policy, authorization, approval, trust, and dispatch operations. Expected agent authentication and access denials are recorded without attributing unsigned or misbound claims to an owner. Monitoring classifies expired credentials, revoked sessions, capability and policy violations, behavioural findings (including repeated authorization denials), and integration failures. A denial does not imply an attack, and the events do not send external alerts.

Events store identifiers, action names, outcomes, and reason codes rather than bearer tokens, secrets, request payloads, free-form resources, user contact details, or provider error text. Successful state changes and their events share a transaction. External adapter effects cannot be rolled back by the database, and a crash or commit failure can prevent execution evidence from persisting. The controller's required pre-dispatch recorder remains separate.

Append-only applies to application repositories and read-only APIs. The current backend uses PostgreSQL, and privileged SQL or storage access can change or remove history. If SQLite is used in another deployment, direct database-file access, raw SQL, or replacement with an older file can bypass application controls. Neither backend is tamper-proof under this design; there is no independent tamper-evidence mechanism.
