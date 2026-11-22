# Phase 02 — Identity

**Status:** NOT STARTED

This is a documentation checkpoint, not a numbered implementation prompt.

## Scope

Establish agent identity, sessions, credential state and capability scope.

## Implementation record

Identity, sessions, credentials and capabilities are reserved packages only. No identity or session enforcement is active.

## Dependencies and blockers

Consult the database checkpoint and the authorized identity prompt before introducing persistence dependencies.

## Verification

NOT RUN. Verify valid, expired and revoked sessions and out-of-scope capabilities when implemented.

## Next handoff

Use the [master instructions](../../PROXI_MASTER_PROMPT.md#security-invariants) to check identity boundaries when authorized. See [current status](../CURRENT_STATUS.md) for the active handoff; wait for explicit authorization.
