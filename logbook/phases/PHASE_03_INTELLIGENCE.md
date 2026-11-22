# Phase 03 — Intelligence

**Status:** IN PROGRESS — Prompt 06 complete; behavior analysis and trust scoring not started.

## Scope

Interpret intent via DeepSeek and persist advisory permission proposals for human review.

## Implementation record

An owner explicitly consents to sending non-sensitive task text. The adapter is isolated behind an outbound port, and the backend validates its structured output. The owner can retrieve proposals for review. Failed attempts store a classification without a proposal. Neither path grants authority. See the [intent API](../../docs/API.md#intent-proposals).

## Verification

All 33 backend tests passed against disposable PostgreSQL 18.4 with mocked DeepSeek; Alembic upgraded to `0004` and reported no schema drift. See [Prompt 06 verification](../TEST_LOG.md#prompt-06). No live inference or hosted database access was attempted.

## Next handoff

Stop after Prompt 06. Policy approval, evaluation, execution, and enforcement remain out of scope without separate authorization.
