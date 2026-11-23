# Phase 04 — Policy Engine

**Status:** COMPLETE — policy management, deterministic evaluation, action approval, and guarded dispatch are verified.

## Scope

Manage policy definitions and their approval lifecycle. Evaluate policy deterministically for `ALLOW`, `HOLD`, and `BLOCK` and enforce the result before adapter dispatch.

## Implementation record

[Policy management](../../docs/API.md#policy-management) converts a stored validated proposal into a draft without calling the model. Only the owner can approve a pending version. Revisions retain historical definitions, and replacement approval atomically supersedes the prior active version. Revocation never restores an older version.

[Authorization and enforcement](../../docs/SECURITY.md#authorization-and-enforcement) applies ordered prerequisite and policy checks. The controller revalidates under the agent lock, records each final decision through the injected recorder, and dispatches only `ALLOW` to a registered adapter.

[Action approvals](../../docs/API.md#action-approvals) persist enforcement holds and expose owner-only review and history. A durable single-use claim precedes fresh authorization; approval alone cannot dispatch.

## Verification

All 53 backend tests passed on disposable PostgreSQL 18.7, including policy lifecycle and history, decision precedence, no dispatch on `HOLD` or `BLOCK`, and revalidation after policy or session revocation. Migration round-trip passed and Alembic reported no schema drift. See [Prompt 08 verification](../TEST_LOG.md#prompt-08).

Prompt 09: all 61 backend tests passed on disposable PostgreSQL 18.7, including concurrent retry and revocation after claim. Migration round-trip passed and Alembic found no schema drift. See [Prompt 09 verification](../TEST_LOG.md#prompt-09).

## Next handoff

Stop after Prompt 09. No trust scoring, dashboard UI, or production execution adapter was added. Keep action approval separate from policy approval, and preserve the [security invariants](../../PROXI_MASTER_PROMPT.md#security-invariants) when integrating adapters.
