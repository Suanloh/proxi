# HTTP API

`GET /api/v1/health` returns HTTP 200 with `{"status":"ok"}`. This is liveness only: no database or external service is checked. Interactive OpenAPI documentation is at `/docs` on the backend.

Error responses use `{"error":{"code":"…","message":"…"}}`: `http_error` for HTTP errors, `validation_error` for invalid requests (422), and `internal_error` for unexpected failures (500). Raw exception details are not returned.

## Agent sessions and access prerequisites

All paths below are relative to `/api/v1/agents/{agent_id}/sessions`. Management routes require the [local owner bearer](DEVELOPMENT.md#agent-identity-api-local-development-only); `access-check` requires a separate agent bearer JWT.

| Method and path | Request and result |
| --- | --- |
| `POST` (collection) | Optional `ttl_seconds` (1–3600, default 3600); returns `201` and the new session. |
| `GET /{session_id}` | Returns the owned session, including derived status and timestamps. |
| `POST /{session_id}/revoke` | Revokes the session; returns `200` with the session. |
| `POST /{session_id}/credentials` | Returns `201` with `id`, `token`, and `expires_at`; the token is only returned on issuance, with `Cache-Control: no-store`. |
| `POST /{session_id}/credentials/{credential_id}/revoke` | Returns `204`. |
| `POST /{session_id}/capabilities` | Takes `task_id`, `action`, `resource`, and optional `ttl_seconds` (1–3600, default 300); returns `201` with the grant. |
| `POST /{session_id}/capabilities/{capability_id}/revoke` | Returns `204`. |
| `POST /{session_id}/access-check` | Takes `task_id`, `action`, `resource`, and `capability_id`; returns `204` only when all prerequisites pass. |

A grant covers one exact action/resource pair on one existing pending task owned by the agent. There is no task creation endpoint yet. The grant and credential cannot outlive their session; credentials last at most five minutes. Revocation is idempotent.

A successful access check is **not** policy authorization or execution. A check returns `401` for missing/invalid credentials or an inactive agent or session, and `403` if the capability is missing, expired, revoked, or out of scope. Management returns `404` for unknown or mismatched resource IDs, `409` when provisioning requires an active agent or session, and `403` for a disabled owner or non-pending task. Access is unavailable (`503`) without the configured database and signing key.
