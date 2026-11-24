"""Bind action approvals to reviewable snapshots and single-use claims."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006"
down_revision = "0005"
branch_labels = None

_SCHEMA = "proxi"
_REQUESTS = "approval_requests"
_RECORDS = "approval_records"
_OUTCOME = "ck_approval_records_outcome"


def upgrade() -> None:
    op.add_column(_REQUESTS, sa.Column("reviewer_id", sa.Uuid()), schema=_SCHEMA)
    op.add_column(_REQUESTS, sa.Column("snapshot", JSONB(none_as_null=True)), schema=_SCHEMA)
    op.add_column(_REQUESTS, sa.Column("consumed_at", sa.DateTime(timezone=True)), schema=_SCHEMA)
    op.create_foreign_key(op.f("fk_approval_requests_reviewer_id"), _REQUESTS, "users", ["reviewer_id"], ["id"],
                          source_schema=_SCHEMA, referent_schema=_SCHEMA, ondelete="RESTRICT")
    op.create_index(op.f("ix_approval_requests_reviewer_id"), _REQUESTS, ["reviewer_id"], schema=_SCHEMA)
    op.create_check_constraint(
        op.f("ck_approval_requests_binding"), _REQUESTS,
        "(reviewer_id IS NULL AND snapshot IS NULL AND consumed_at IS NULL) OR "
        "(reviewer_id IS NOT NULL AND snapshot IS NOT NULL AND (consumed_at IS NULL OR consumed_at < expires_at))",
        schema=_SCHEMA,
    )
    op.drop_constraint(op.f(_OUTCOME), _RECORDS, type_="check", schema=_SCHEMA)
    op.create_check_constraint(op.f(_OUTCOME), _RECORDS, "outcome IN ('approved', 'rejected', 'cancelled')", schema=_SCHEMA)


def downgrade() -> None:
    # Older versions cannot represent cancellation; keep those reviews non-authorizing.
    op.execute("UPDATE proxi.approval_records SET outcome = 'rejected' WHERE outcome = 'cancelled'")
    op.drop_constraint(op.f(_OUTCOME), _RECORDS, type_="check", schema=_SCHEMA)
    op.create_check_constraint(op.f(_OUTCOME), _RECORDS, "outcome IN ('approved', 'rejected')", schema=_SCHEMA)
    op.drop_constraint(op.f("ck_approval_requests_binding"), _REQUESTS, type_="check", schema=_SCHEMA)
    op.drop_index(op.f("ix_approval_requests_reviewer_id"), table_name=_REQUESTS, schema=_SCHEMA)
    op.drop_constraint(op.f("fk_approval_requests_reviewer_id"), _REQUESTS, type_="foreignkey", schema=_SCHEMA)
    for column in ("consumed_at", "snapshot", "reviewer_id"):
        op.drop_column(_REQUESTS, column, schema=_SCHEMA)
