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

Run tests from `backend`:

```powershell
$env:PROXI_ENV = 'testing'
..\.venv\Scripts\python.exe -m pytest app\tests
```

## Frontend

```powershell
Set-Location .\frontend
npm.cmd ci
# Optional: Copy-Item -LiteralPath .env.example -Destination .env.local
npm.cmd run dev
```

Open `http://127.0.0.1:3000`. The placeholder page starts independently of the backend. When used by server-side code, the API client defaults to `http://127.0.0.1:8000/api/v1`; set `PROXI_API_BASE_URL` in `frontend/.env.local` or the process to override it. Do not use the `NEXT_PUBLIC_` prefix. In a separate check, use `npm.cmd run build` for production compilation and TypeScript validation, then `npm.cmd run start` to serve that build.

Tailwind and shadcn/ui are configured; there are no generated UI components yet. See the [UI guidelines](frontend/UI_GUIDELINES.md), [component architecture](frontend/COMPONENT_ARCHITECTURE.md), [screen hierarchy](frontend/SCREEN_HIERARCHY.md), and [UI roadmap](frontend/FUTURE_UI_ROADMAP.md) before adding screens.
