# Known issues

Track defects, advisories and verification gaps separately from planned functionality in [current status](CURRENT_STATUS.md). Severity describes observed impact, not completeness. Use `Open`, `Mitigated` or `Resolved` for issue status.

## KI-001 — shadcn development dependency advisories

- **Type / severity:** Dependency advisory / Moderate (per original audit).
- **Status:** Open; historically reported, not rechecked in Prompt 02.
- **Reproduction:** From `frontend`, run `npm.cmd audit` against installed lockfile dependencies and compare with `npm.cmd audit --omit=dev`. Results can change with the advisory database.
- **Observed:** The [original audit](TEST_LOG.md#prompt-01) reported four moderate advisories in the development-only shadcn CLI chain and none for production dependencies.
- **Workaround:** Do not force the incompatible CLI major upgrade. Track a compatible upstream update and rerun both audits when evaluating it.

## KI-002 — Native keyboard verification pending

- **Type / severity:** Verification gap / Unassessed; no defect confirmed.
- **Status:** Open.
- **Reproduction:** Start the frontend using the [development guide](../docs/DEVELOPMENT.md#frontend). In a fresh page, press Tab and check that the skip link becomes visible and focused. Press Enter and check that focus moves to the main content.
- **Observed:** The [browser spot check](TEST_LOG.md#prompt-015) verified focus via programmatic activation only; native Tab/Enter and the full accessibility audit were not verified.
- **Workaround:** No runtime workaround needed for an unconfirmed defect. Use a real keyboard or a browser harness that sends native key events for follow-up verification.

## KI-003 — Intent provider scope confirmed

- **Type / severity:** Scope decision; no security defect implied.
- **Status:** Closed. DeepSeek is the accepted provider; Gemini is out of scope.
- **Observed:** The application wires DeepSeek. There is no Gemini integration. The existing provider tests mock DeepSeek rather than exercising a live provider.
- **Next action:** Verify live DeepSeek interpretation during the operator rehearsal. See the [API contract](../docs/API.md#intent-proposals).

## KI-004 — Final persistence and enforcement checks not re-run

- **Type / severity:** Verification gap; blocks MVP sign-off.
- **Status:** Open.
- **Observed:** 52 PostgreSQL-backed checks skipped without a disposable test DSN, including workspace persistence, approval concurrency, the flight scenario, and MCP dispatch. Frontend smoke uses a fixture API.
- **Next action:** Run the full suite on disposable PostgreSQL, then rehearse the [live operator path](../docs/DEVELOPMENT.md#prompt-16-demonstration).

## KI-005 — Local enforcement and audit boundaries

- **Type / severity:** Design limitation; not a production deployment boundary.
- **Status:** Open.
- **Observed:** Owner authentication is a local developer bearer. Direct website and tool traffic are outside PROXI. Audit history has no independent tamper evidence; external effects are not atomic with audit persistence.
- **Mitigation:** Use loopback only, trusted read-only demo endpoints, and deployment egress restrictions as described in [Security](../docs/SECURITY.md). Production identity and durable independent audit are separate work.

## Entry template

- **Issue ID and title:** KI-NNN and a short summary in the heading.
- **Type / severity:** Defect, advisory or gap; include severity and basis.
- **Status:** Open / Mitigated / Resolved.
- **Reproduction:** Preconditions and numbered steps or commands.
- **Observed:** Actual versus expected behavior, with evidence when available.
- **Workaround:** Mitigation and next action, or none.
