# Phase 04 — Policy Engine

**Status:** NOT STARTED

This is a documentation checkpoint, not a numbered implementation prompt.

## Scope

Evaluate deterministic policy and coordinate ALLOW, HOLD and BLOCK outcomes.

## Implementation record

Policy, authorization, enforcement and approval packages are placeholders. No protected execution path exists.

## Dependencies and blockers

Review identity and capability contracts before implementing their policy checks. Advisory signals cannot override a hard deny.

## Verification

NOT RUN. Verify hard-deny precedence, that HOLD does not execute, and that approval requires revalidation.

## Next handoff

Use the [master security invariants](../../PROXI_MASTER_PROMPT.md#security-invariants) to check the authorized policy scope. See [current status](../CURRENT_STATUS.md) for the active handoff; wait for explicit authorization.
