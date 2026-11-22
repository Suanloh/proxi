"""Persist advisory intent proposals and classified failures.

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None

_TABLE = "intent_interpretations"
_STATUS = "ck_intent_interpretations_status"
_FAILURE = "ck_intent_interpretations_failure"


def upgrade() -> None:
    op.add_column(_TABLE, sa.Column("proposal", JSONB(none_as_null=True)), schema="proxi")
    op.add_column(_TABLE, sa.Column("failure_code", sa.String()), schema="proxi")
    op.drop_constraint(op.f(_STATUS), _TABLE, type_="check", schema="proxi")
    op.create_check_constraint(
        op.f(_STATUS), _TABLE, "status IN ('proposed', 'rejected', 'reviewed', 'failed')", schema="proxi",
    )
    op.create_check_constraint(
        op.f(_FAILURE), _TABLE,
        "(status = 'failed' AND proposal IS NULL AND failure_code IS NOT NULL) OR "
        "(status <> 'failed' AND failure_code IS NULL)", schema="proxi",
    )


def downgrade() -> None:
    op.drop_constraint(op.f(_FAILURE), _TABLE, type_="check", schema="proxi")
    op.drop_constraint(op.f(_STATUS), _TABLE, type_="check", schema="proxi")
    op.execute("UPDATE proxi.intent_interpretations SET status = 'rejected' WHERE status = 'failed'")
    op.create_check_constraint(
        op.f(_STATUS), _TABLE, "status IN ('proposed', 'rejected', 'reviewed')", schema="proxi",
    )
    op.drop_column(_TABLE, "failure_code", schema="proxi")
    op.drop_column(_TABLE, "proposal", schema="proxi")
