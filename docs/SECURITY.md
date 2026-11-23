# Security

Run both apps on loopback. Configuration examples contain no credentials. Keep real configuration in ignored env files or process variables; keep the frontend API base URL server-side and credential-free.

The API suppresses raw exception details in responses. Application startup/error events are JSON and do not include request bodies or exception messages. The ASGI server has its own exception and access logs; do not put credentials in URLs or exception text.

Agent identity management is disabled by default. Its [local development opt-in](DEVELOPMENT.md#agent-identity-api-local-development-only) binds a backend-only bearer secret to one active application user and restricts reads and writes to that user's agents. It is not production user authentication. Never provide that secret to agents or expose this boundary beyond loopback.

Registration allocates a server-generated ID; possession of that ID is not proof of agent identity. Agent access uses an HS256 JWT (RFC 7519), signed and verified by PyJWT with a server-pinned algorithm, issuer `proxi`, and audience `proxi-agent-access`. The claims `sub`, `sid`, and `jti` bind the token to its agent, session, and credential record; `iat` and `exp` bound its lifetime. Only an identifier and revocation/expiry metadata are stored, not the bearer token. Treat both bearer tokens and signing keys as secrets; never put them in URLs, logs, or frontend configuration.

The prerequisite gate verifies the credential and requires an active owner, agent and session plus an unexpired, unrevoked capability with the exact requested scope. A successful check does not authorize or execute anything. Future execution must supply trusted operation context, revalidate the prerequisites at execution, and apply policy separately. See [Architecture](ARCHITECTURE.md) for the planned enforcement boundaries.

Policy management uses that same local owner boundary. A provider proposal is never active policy. Drafts and pending versions are excluded from the approved-active state, as are revoked, superseded and legacy unbound versions. Only explicit approval of a specific pending version can activate it. Activation does not grant capabilities or authorize execution; a future evaluator must apply identity, task, resource, time, context and approval rules independently.
