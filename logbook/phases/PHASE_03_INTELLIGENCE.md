# Phase 03 — Intelligence

**Status:** NOT STARTED

This is a documentation checkpoint, not a numbered implementation prompt.

## Scope

Interpret intent via Gemini as an advisory input to the security pipeline.

## Implementation record

The LLM and intent packages are placeholders. No Gemini client, intent schema or permission proposal workflow exists.

## Dependencies and blockers

Require an explicitly authorized prompt. Keep Gemini behind an outbound port; its output grants no authority.

## Verification

NOT RUN. Test schema validation and rejection of invalid model output once the adapter exists.

## Next handoff

Review [architecture boundaries](../../docs/ARCHITECTURE.md#hexagonal-boundaries-and-dependency-direction) before wiring an adapter. See [current status](../CURRENT_STATUS.md) for the active handoff; wait for explicit authorization.
