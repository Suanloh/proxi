# Security

Run both apps on loopback. Configuration examples contain no credentials. Keep real configuration in ignored env files or process variables; keep the frontend API base URL server-side and credential-free.

The API suppresses raw exception details in responses. Application startup/error events are JSON and do not include request bodies or exception messages. The ASGI server has its own exception and access logs; do not put credentials in URLs or exception text.

Agent identity management is disabled by default. Its [local development opt-in](DEVELOPMENT.md#agent-identity-api-local-development-only) binds a backend-only bearer secret to one active application user and restricts reads and writes to that user's agents. It is not production user authentication. Never provide that secret to agents or expose this boundary beyond loopback.

Registration allocates a server-generated ID; possession of that ID is not proof of agent identity. The service rejects non-active identities when checking status, but the app does not yet authenticate agents, authorize actions, or enforce session, credential, or capability scope. See [Architecture](ARCHITECTURE.md) for the planned enforcement boundaries.
