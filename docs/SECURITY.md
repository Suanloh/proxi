# Security

Run both apps on loopback. Configuration examples contain no credentials. Keep real configuration in ignored env files or process variables; keep the frontend API base URL server-side and credential-free.

The API suppresses raw exception details in responses. Application startup/error events are JSON and do not include request bodies or exception messages. The ASGI server has its own exception and access logs; do not put credentials in URLs or exception text.

The current scaffold does not provide authentication, authorization or protection for agent actions. See [Architecture](ARCHITECTURE.md) for the planned enforcement boundaries.
