"""Persist managed policy scope, version snapshots and owner approval.

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005"
down_revision = "0004"
branch_labels = None

_SCHEMA = "proxi"
_POLICIES = "policies"
_VERSIONS = "policy_versions"
_STATUS = "ck_policy_versions_status"
_BINDINGS = {"source_proposal_id": "intent_interpretations", "task_id": "tasks", "agent_id": "agents"}
_REVIEW = "uq_policy_versions_review"


def upgrade() -> None:
    for column, target in _BINDINGS.items():
        op.add_column(_POLICIES, sa.Column(column, sa.Uuid()), schema=_SCHEMA)
        op.create_foreign_key(
            op.f(f"fk_policies_{column}"), _POLICIES, target, [column], ["id"],
            source_schema=_SCHEMA, referent_schema=_SCHEMA, ondelete="RESTRICT",
        )
    op.create_check_constraint(
        op.f("ck_policies_binding"), _POLICIES,
        "num_nonnulls(source_proposal_id, task_id, agent_id) IN (0, 3)", schema=_SCHEMA,
    )
    op.add_column(_VERSIONS, sa.Column("definition", JSONB(none_as_null=True)), schema=_SCHEMA)
    for column in ("approved_at", "revoked_at"):
        op.add_column(_VERSIONS, sa.Column(column, sa.DateTime(timezone=True)), schema=_SCHEMA)
    op.drop_constraint(op.f(_STATUS), _VERSIONS, type_="check", schema=_SCHEMA)
    op.create_check_constraint(
        op.f(_STATUS), _VERSIONS,
        "status IN ('draft', 'pending_approval', 'active', 'revoked', 'superseded')", schema=_SCHEMA,
    )
    op.create_check_constraint(
        op.f("ck_policy_versions_revoked_at"), _VERSIONS,
        "(status = 'revoked') = (revoked_at IS NOT NULL)", schema=_SCHEMA,
    )
    op.create_check_constraint(
        op.f("ck_policy_versions_approval"), _VERSIONS,
        "definition IS NULL OR status = 'revoked' OR "
        "((status IN ('active', 'superseded')) = (approved_at IS NOT NULL))", schema=_SCHEMA,
    )
    op.create_index(
        _REVIEW, _VERSIONS, ["policy_id"], unique=True, schema=_SCHEMA,
        postgresql_where=sa.text("definition IS NOT NULL AND status IN ('draft', 'pending_approval')"),
    )


def downgrade() -> None:
    op.drop_index(_REVIEW, table_name=_VERSIONS, schema=_SCHEMA)
    for name in (_STATUS, "ck_policy_versions_revoked_at", "ck_policy_versions_approval"):
        op.drop_constraint(op.f(name), _VERSIONS, type_="check", schema=_SCHEMA)
    op.execute("UPDATE proxi.policy_versions SET status = 'draft' "
               "WHERE status IN ('pending_approval', 'revoked') OR (definition IS NOT NULL AND status = 'active')")
    op.create_check_constraint(
        op.f(_STATUS), _VERSIONS, "status IN ('draft', 'active', 'superseded')", schema=_SCHEMA,
    )
    for column in ("definition", "approved_at", "revoked_at"):
        op.drop_column(_VERSIONS, column, schema=_SCHEMA)
    op.drop_constraint(op.f("ck_policies_binding"), _POLICIES, type_="check", schema=_SCHEMA)
    for column in _BINDINGS:
        op.drop_constraint(op.f(f"fk_policies_{column}"), _POLICIES, type_="foreignkey", schema=_SCHEMA)
        op.drop_column(_POLICIES, column, schema=_SCHEMA)
