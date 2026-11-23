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

## Authorization check

`POST /api/v1/authorization/check` requires an agent bearer JWT whose agent and session match the request. Send a JSON object with `request` and `capability_id`. The `request` contains `request_id`, `agent_id`, `session_id`, `action`, `resource`, `timestamp` (timezone-aware), `integration_type`, optional `params`, and optional `task_id`. Current capabilities require a pending task and bind to its exact action and resource, so omitting `task_id` or `capability_id` cannot authorize the request.

The endpoint returns HTTP `200` with `request_id`, `outcome` (`ALLOW`, `HOLD`, or `BLOCK`), `reason`, `failed_checks`, `matched_policy` (policy ID and version identifiers, when applicable), and `required_approval` for a hold. Missing, invalid, expired, or mismatched JWTs receive `401` before evaluation; the engine checks stored credential state again. The database and signing key must be configured. Responses with decisions are not cached. This endpoint does not accept trusted context, execute the action, or create an approval request. An `ALLOW` is not reusable execution authority. See [authorization and enforcement](SECURITY.md#authorization-and-enforcement).

## Action approvals

The enforcement controller persists a `HOLD` and returns an approval ID equal to the action's request UUID. The authorization check does not create holds. These endpoints require the local owner bearer, not an agent JWT, and only expose the owner's approvals.

| Method and path | Behavior |
| --- | --- |
| `GET /api/v1/approvals` | List pending requests, newest first. Use `history=true` for non-pending requests. `limit` defaults to 50 (max 100); `offset` defaults to 0. |
| `GET /api/v1/approvals/{approval_id}` | Return the action snapshot, hold reason, policy version IDs, expiry, reviewer and decision time, and claim time if consumed. |
| `POST /api/v1/approvals/{approval_id}/approve` | Approve a pending request. Does not execute it. |
| `POST /api/v1/approvals/{approval_id}/reject` | Reject a pending request. |
| `POST /api/v1/approvals/{approval_id}/cancel` | Cancel a pending request. |

A request starts `PENDING` and can become `APPROVED`, `REJECTED`, or `CANCELLED`. Unconsumed pending and approved requests become `EXPIRED` after five minutes; the original review is still visible in history. Repeating the same current decision returns it unchanged; conflicting or expired reviews return `409`. Unknown or out-of-scope IDs return `404`. To execute after approval, resubmit the exact action through the enforcement controller. The claim timestamp records use of the approval, not execution success.

## Trust review

`POST /api/v1/agents/{agent_id}/trust/review` requires the local owner bearer and has no request body. After the configured cooldown, an active owner can move an active owned agent up one band: suspended to restricted, or restricted to enhanced monitoring. The endpoint returns `204` without a body, `403` for an inactive owner, `404` for an unknown or unowned agent, and `409` for an inactive agent, ineligible band, or unelapsed cooldown. It cannot reactivate an agent, grant capabilities, change policy, or satisfy action approval.

The authorization check can return `BLOCK` with `reason: "trust_restricted"` for an otherwise eligible request. The enforcement controller can also apply behavior signals during final revalidation, so a preview `ALLOW` is not a dispatch guarantee.
