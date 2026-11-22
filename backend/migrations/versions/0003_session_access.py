"""Bind credentials and capabilities to sessions and capabilities to tasks.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None

_BINDINGS = (
    ("credentials", "session_id", "agent_sessions"),
    ("capabilities", "session_id", "agent_sessions"),
    ("capabilities", "task_id", "tasks"),
)


def upgrade() -> None:
    for table, column, target in _BINDINGS:
        op.add_column(table, sa.Column(column, sa.Uuid()), schema="proxi")
        op.create_foreign_key(
            op.f(f"fk_{table}_{column}"), table, target, [column], ["id"],
            source_schema="proxi", referent_schema="proxi", ondelete="RESTRICT",
        )


def downgrade() -> None:
    for table, column, _ in reversed(_BINDINGS):
        op.drop_constraint(op.f(f"fk_{table}_{column}"), table, type_="foreignkey", schema="proxi")
        op.drop_column(table, column, schema="proxi")
