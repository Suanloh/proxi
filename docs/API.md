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

A grant covers one exact action/resource pair on one existing pending task owned by the agent. Intent submission can create a task, but does not create a grant. The grant and credential cannot outlive their session; credentials last at most five minutes. Revocation is idempotent.

A successful access check is **not** policy authorization or execution. A check returns `401` for missing/invalid credentials or an inactive agent or session, and `403` if the capability is missing, expired, revoked, or out of scope. Management returns `404` for unknown or mismatched resource IDs, `409` when provisioning requires an active agent or session, and `403` for a disabled owner or non-pending task. Access is unavailable (`503`) without the configured database and signing key.

## Intent proposals

Both routes require the [local owner bearer](DEVELOPMENT.md#agent-identity-api-local-development-only) and are under `/api/v1/agents/{agent_id}/intent-interpretations`.

- `POST` requires an active owned agent and a JSON body with `task` (1–4000 characters) and `share_with_deepseek: true`. Only submit non-sensitive task text. Consent allows the text to be sent to DeepSeek; it does not redact secrets or approve operations. Success returns `201` with `id`, `task_id`, `created_at`, `status: "proposed"`, `interpretation`, and `proposed_permissions`.
- `GET /{interpretation_id}` returns the stored proposal for review under its original agent. Unavailable proposals, including failed attempts, return `404`.

The proposal is advisory even when its schema is valid. It cannot itself create or alter policies, grant capabilities, authorize operations, or execute anything. The owner can use a stored proposal to create a draft through the policy API below. For example, a flight comparison proposal can suggest `browser.navigate` and `browser.read`, prohibit `payment.purchase` and personal-data disclosure, and flag `external_data_submission` for approval.

Missing provider configuration returns `503`, provider errors and invalid output return `502`, and timeouts return `504`. Each recorded failure has a local failure code and no proposal; it leaves existing authorization state unchanged. The backend uses `PROXI_DEEPSEEK_API_KEY`, `PROXI_DEEPSEEK_MODEL` (default `deepseek-flash`), and `PROXI_DEEPSEEK_TIMEOUT_SECONDS` (default `20`, maximum `120`).

## Policy management

These routes require the [local owner bearer](DEVELOPMENT.md#agent-identity-api-local-development-only) and are under `/api/v1/policies`. Agent credentials cannot manage policies.

| Route | Behavior |
| --- | --- |
| `POST /` | Accepts `agent_id` and `proposal_id` for a stored, validated proposal from the active owned agent. Returns `201` with a draft at version 1. |
| `GET /` | Lists the owner's managed policies. |
| `GET /{policy_id}` | Returns the policy's fixed owner, agent, task, and source proposal, with `latest` and `active_version`. |
| `GET /{policy_id}/versions` | Returns version snapshots in ascending order. |
| `POST /{policy_id}/versions` | Accepts `base_version` (the latest version number) and a complete `definition`. Returns `201` with a replacement draft. |
| `POST /{policy_id}/versions/{version}/submit` | Moves a draft to `pending_approval`. |
| `POST /{policy_id}/versions/{version}/approve` | Requires the JSON body `{"approve": true}`. Activates a pending version and atomically supersedes any prior active version. |
| `POST /{policy_id}/versions/{version}/revoke` | Revokes a draft, pending, or active version; does not reactivate an older version. |

A definition contains `allowed_actions`, `denied_actions`, `approval_required_actions`, `resource_scope`, `sensitive_resources`, and optional `conditions`. Conditions can specify `required_capability_ids`, timezone-aware `not_before` and `expires_at`, and `context_attributes` with string, integer or boolean values. The three action lists are disjoint. Revisions preserve prior definitions and allow at most one outstanding draft or pending version. An existing active version remains active until superseded or explicitly revoked.

Unknown or out-of-scope resources return `404`; invalid transitions, stale or unchanged revisions, and approval of an expired version return `409`; invalid request bodies return `422`. `active_version` is a lifecycle indicator, not a runtime authorization decision. Policy approval does not satisfy individual action approval requirements.
