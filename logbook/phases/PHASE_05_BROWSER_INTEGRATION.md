# Phase 05 — Browser Integration

**Status:** COMPLETE (Prompt 12)

This is a documentation checkpoint, not a numbered implementation prompt.

## Scope

Route supported browser actions through the shared authorization pipeline.

## Implementation record

The [controlled browser API](../../docs/API.md#controlled-browser) binds requests to the agent and session, uses exact-page scopes, and dispatches only authorized navigation and reading. `HOLD` requires owner approval and an exact retry. Blocked attempts never reach the renderer. Click, fill, and download are unsupported. No Chrome extension was built.

## Security boundary

Each dispatch uses a fresh, offline Chromium context and bounded HTML fetched without redirects. Only allowlist trusted read-only endpoints: an HTTP GET by itself does not guarantee no upstream side effects. Web content cannot change authorization, and actions that bypass PROXI are not protected.

## Verification

The [flight-fare demo](../../docs/DEVELOPMENT.md#controlled-browser-demo) verified authorized access, approval, and audited policy blocks for purchase and personal-data sharing. The full backend suite passed 77 tests; see [Prompt 12 verification](../TEST_LOG.md#prompt-12).

## Prompt 13 integration follow-up

The [controlled MCP gateway and local-agent adapter](../../docs/API.md#controlled-mcp-and-local-agent-tools) now use the same authorization pipeline for a single, exact-scope catalog lookup. See [Prompt 13 verification](../TEST_LOG.md#prompt-13). This follow-up adds no browser operations or extension.

## Next handoff

See [current status](../CURRENT_STATUS.md) and wait for the next explicitly authorized prompt.
