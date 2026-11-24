# Local development

## Session workflow

### Startup (required before edits)

1. Read the [master instructions](../PROXI_MASTER_PROMPT.md), [current status](../logbook/CURRENT_STATUS.md), and [master log](../logbook/MASTER_LOG.md), in that order.
2. Read the relevant [phase checkpoint](../logbook/phases/) and any linked architecture, issue, or test records. Checkpoints record progress; only the explicitly supplied numbered prompt authorizes work.
3. Inspect the working tree and relevant sources and tests. Confirm preconditions against repository evidence, preserve existing changes, and plan only the authorized scope. If a precondition fails, stop and report it.

### Shutdown (required before handoff)

1. Run applicable validation and record exact commands or methods, actual results, and follow-up actions in the [test log](../logbook/TEST_LOG.md). Mark anything skipped `NOT RUN` with a reason. Stop temporary processes started for validation.
2. Append a [master log](../logbook/MASTER_LOG.md) entry and update the [current status](../logbook/CURRENT_STATUS.md) and affected phase checkpoints. Record changes, decisions, and open issues in their respective logs when applicable. Do not record secrets or sensitive input.
3. Report the prompt number and name, completed scope, files created or modified, tests passed, failed or not run, security considerations, incomplete work, logbook and acceptance status, and the recommended next prompt. Stop and wait for explicit authorization; if acceptance fails, report the blocker rather than marking work complete.

## Running locally

Use Python 3.12 and Node.js 22 or newer. Commands below use PowerShell from the repository root. Run the two servers in separate terminals.

## Backend

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements-test.txt
# Optional: Copy-Item -LiteralPath .env.example -Destination .env
Set-Location .\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

Check `http://127.0.0.1:8000/api/v1/health`. Development is the default and loads the optional root `.env`; process variables override file values. Set `PROXI_ENV=testing` in the process to skip `.env` and default to warning-level logs. `PROXI_LOG_LEVEL` overrides the default in either mode.

To enable persistence, follow the [database setup and migration instructions](DATABASE.md#configuration-and-migrations).

Run tests from `backend`. For PostgreSQL integration tests, use a dedicated, disposable local PostgreSQL instance with a role that can create databases. Set `PROXI_TEST_DATABASE_URL` with a literal loopback address, an explicit port, and no query options. The test fixture creates and drops a separate database for each integration test. Never use the hosted Supabase URL for tests; if the variable is absent, PostgreSQL integration tests are skipped.

Example (replace placeholders):

```powershell
$env:PROXI_ENV = 'testing'
$env:PROXI_TEST_DATABASE_URL = 'postgresql+psycopg://USER:ENCODED_PASSWORD@127.0.0.1:PORT/postgres'
..\.venv\Scripts\python.exe -m pytest app\tests
```

## Controlled browser demo

From `backend`, install Playwright's Chromium runtime, set the disposable PostgreSQL test variables above, and run:

```powershell
..\.venv\Scripts\python.exe -m playwright install chromium
..\.venv\Scripts\python.exe -m pytest -q app\tests\test_database.py -k browser
```

If Chromium was installed to a custom cache, set `PLAYWRIGHT_BROWSERS_PATH` to that same absolute path before running the tests. The demo starts its own loopback site and uses synthetic fares and a disposable database; it does not contact an airline, book travel, or use real personal data.

The task is to compare Kuala Lumpur–Tokyo fares without buying or sharing personal data. The page displays two prices and instructs the caller to ignore the task, disclose data, and buy a ticket. The demo navigates, then reads after an owner approval. It submits two scripted attempts representing those instructions and checks the explicit policy blocks in the owner audit log. The fixture also confirms that Chromium makes no checkout request. This demonstrates policy enforcement, not prompt-injection detection.

## Controlled MCP and local-agent demo

From `backend`, with the disposable PostgreSQL settings above, run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q app\tests\test_database.py -k controlled_tool_gateway
```

The demo seeds agent credentials, a capability, and policy. It invokes the built-in MCP server through the Python SDK and exercises the local lookup through the [same authorization pipeline](API.md#controlled-mcp-and-local-agent-tools). It also checks that denied requests never reach the tool handler. Chromium and external MCP servers are not required.

For manual use, enable the chosen tool with `PROXI_MCP_CATALOG_ENABLED=true` or `PROXI_LOCAL_CATALOG_ENABLED=true` before starting the backend. Both default to off. Provision a matching agent, session, capability, and policy for the route's action and exact resource `catalog:proxi`. The trusted registry in `app.state.integrations` supports `register`, `enable`, `disable`, and `inspect` for code-defined supported tools; startup already registers the built-ins. Runtime changes apply only to the current process. Each restart loads the configured flags again.

## Agent identity API (local development only)

1. Point the backend at a local PostgreSQL database and migrate to `head`. Using a trusted SQL connection to that database, provision an active application user and copy the returned UUID:

   ```sql
   INSERT INTO proxi.users (id, email) VALUES (gen_random_uuid(), 'operator@example.test') RETURNING id;
   ```

2. Set `PROXI_DEV_IDENTITY_OWNER_ID` to that UUID and `PROXI_DEV_IDENTITY_TOKEN` to a randomly generated secret (use at least 32 random bytes encoded as hex). Use backend process variables or the ignored root `.env`. Restart the loopback-bound backend. Never put the token in a URL, frontend configuration, or source control.
3. Use `Authorization: Bearer <token>` from a trusted local client. The token represents one configured application user, not an agent. This is not production authentication and must not be exposed beyond loopback.

| Method and path | Behavior |
| --- | --- |
| `POST /api/v1/agents` | Register with `name`, `type`, and optional `description`; returns `201`. |
| `GET /api/v1/agents` | List only the configured user's agents, including revoked records. |
| `GET /api/v1/agents/{agent_id}` | Retrieve one owned identity. |
| `PATCH /api/v1/agents/{agent_id}` | Change `name`, `type`, `description`, or `status`; set `description` to `null` to clear it. |
| `POST /api/v1/agents/{agent_id}/revoke` | Revoke an owned agent; repeated revocation returns the same revoked record. |

Names are trimmed, must be 1–120 characters, and are unique per owner. Descriptions are limited to 2,000 characters. Types are `browser`, `mcp`, `local`, and `coding` (legacy rows may still have `null`). The server assigns the UUID, UTC `created_at`, and initial `active` status. `last_seen_at` starts `null` and is not set by management operations; session access checks do not update it. `PATCH` can move non-revoked agents between `active`, `inactive`, and `suspended`; only `active` passes the service's status check. Revoked agents cannot be patched or reactivated.

Agent management returns `503` without opt-in, `401` for missing or incorrect bearer credentials, `403` for a missing or disabled configured user, `404` for an unknown or unowned agent, `409` for a duplicate or prohibited status change, and `422` for invalid request data. IDs, owners, and timestamps cannot be set by the client.

## Agent access API (local development only)

Use the same local owner setup and migrate to revision `0003` or later. Generate 32 random bytes with a cryptographically secure random generator (for example, Python `secrets.token_hex(32)`) and set the resulting 64 hex characters as `PROXI_CREDENTIAL_SIGNING_KEY` in the backend process or ignored root `.env`. Use a dedicated key, separate from the owner token, and restart the backend after configuring it. Replacing the key invalidates all previously issued agent JWTs; issue new credentials for eligible sessions as needed.

Use the owner bearer to create sessions, issue credentials, and grant capabilities for existing tasks. Give the agent only its short-lived JWT, not the signing key or owner bearer. See the [endpoint contract](API.md#agent-sessions-and-access-prerequisites).

## Frontend

```powershell
Set-Location .\frontend
npm.cmd ci
# Optional: Copy-Item -LiteralPath .env.example -Destination .env.local
npm.cmd run dev
```

Open `http://127.0.0.1:3000` and sign in with the local development owner token configured above. The dashboard needs a migrated local database and an active stored owner. The server-side API client defaults to `http://127.0.0.1:8000/api/v1`; override it with `PROXI_API_BASE_URL` in `frontend/.env.local` or the frontend process. Do not use the `NEXT_PUBLIC_` prefix. The frontend stores the token in an HttpOnly, SameSite Strict session cookie; set `PROXI_SECURE_COOKIES=true` for HTTPS. This is local development authentication, not production sign-in. Operations that show a confirmation require JavaScript.

Run `npm.cmd run build` for production compilation and TypeScript validation, then `npm.cmd run start` to serve that build. To run the dashboard smoke test after building, run `npx.cmd playwright install chromium` and `npm.cmd test`. Alternatively, set `PROXI_TEST_BROWSER_CHANNEL=msedge` or `chrome` to use an already installed browser. The test starts a separate Next server and a fixture API on loopback ports. It does not use the project database or an owner credential from the environment.

See the [UI guidelines](frontend/UI_GUIDELINES.md), [component architecture](frontend/COMPONENT_ARCHITECTURE.md), and [screen hierarchy](frontend/SCREEN_HIERARCHY.md) for layout and component guidance.
