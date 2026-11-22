"""Persist agent identity metadata and lifecycle.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("type", sa.String()), schema="proxi")
    op.add_column("agents", sa.Column("description", sa.String()), schema="proxi")
    op.add_column("agents", sa.Column("last_seen_at", sa.DateTime(timezone=True)), schema="proxi")
    op.drop_constraint(op.f("ck_agents_status"), "agents", type_="check", schema="proxi")
    op.execute("UPDATE proxi.agents SET status = 'inactive' WHERE status = 'disabled'")
    op.execute("UPDATE proxi.agents SET status = 'revoked' WHERE status = 'deleted'")
    op.create_check_constraint(
        op.f("ck_agents_status"), "agents", "status IN ('active', 'inactive', 'suspended', 'revoked')",
        schema="proxi",
    )
    op.create_check_constraint(
        op.f("ck_agents_type"), "agents", "type IN ('browser', 'mcp', 'local', 'coding')", schema="proxi",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_agents_status"), "agents", type_="check", schema="proxi")
    op.execute("UPDATE proxi.agents SET status = 'disabled' WHERE status IN ('inactive', 'suspended')")
    op.execute("UPDATE proxi.agents SET status = 'deleted' WHERE status = 'revoked'")
    op.create_check_constraint(
        op.f("ck_agents_status"), "agents", "status IN ('active', 'disabled', 'deleted')", schema="proxi",
    )
    op.drop_constraint(op.f("ck_agents_type"), "agents", type_="check", schema="proxi")
    for column in ("last_seen_at", "description", "type"):
        op.drop_column("agents", column, schema="proxi")
