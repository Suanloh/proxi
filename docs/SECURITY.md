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

The first failing check determines the reason. Policy ID order breaks ties for decision attribution, not for permission precedence. No trust scoring or action approval workflow is implemented.

The controller accepts only explicitly registered integration/action adapters. Before synchronous dispatch it evaluates again in a fresh transaction, calls the required decision recorder, and holds the agent row lock through dispatch. Agent, session, credential, capability, and policy lifecycle mutations share that lock; policy mutations that change active authority take it before the policy lock. The recorder must be synchronous, must not re-enter these mutations, and must not log credentials or raw parameters. If recording fails, dispatch does not start. The controller accepts an injected recorder; no production audit sink is wired yet.

Adapters must execute the exact authorized action and resource, validate action-specific parameters, and finish without scheduling deferred work. A `HOLD`, `BLOCK`, or missing adapter does not dispatch. No browser or MCP executor is registered, and the [check endpoint](API.md#authorization-check) never dispatches.
