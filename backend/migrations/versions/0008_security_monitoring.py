"""Add structured audit and security monitoring fields."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_SCHEMA = "proxi"
_TABLES = ("audit_logs", "security_events")
_UUID_FIELDS = ("owner_id", "actor_id", "session_id", "resource_id", "request_id", "correlation_id")
_TEXT_FIELDS = ("actor_kind", "action", "outcome", "reason")


def upgrade() -> None:
    for table in _TABLES:
        for name in _UUID_FIELDS:
            op.add_column(table, sa.Column(name, sa.Uuid()), schema=_SCHEMA)
        for name in _TEXT_FIELDS:
            op.add_column(table, sa.Column(name, sa.String()), schema=_SCHEMA)
        op.create_index(f"ix_{table}_owner_time", table, ["owner_id", "created_at", "id"], schema=_SCHEMA)
    op.add_column("audit_logs", sa.Column("severity", sa.String()), schema=_SCHEMA)
    op.add_column("security_events", sa.Column("audit_event_id", sa.Uuid()), schema=_SCHEMA)
    op.create_foreign_key(op.f("fk_security_events_audit_event_id"), "security_events", "audit_logs",
                          ["audit_event_id"], ["id"], source_schema=_SCHEMA, referent_schema=_SCHEMA,
                          ondelete="RESTRICT")


def downgrade() -> None:
    op.drop_constraint(op.f("fk_security_events_audit_event_id"), "security_events", schema=_SCHEMA,
                       type_="foreignkey")
    op.drop_column("security_events", "audit_event_id", schema=_SCHEMA)
    op.drop_column("audit_logs", "severity", schema=_SCHEMA)
    for table in _TABLES:
        op.drop_index(f"ix_{table}_owner_time", table_name=table, schema=_SCHEMA)
        for name in (*_TEXT_FIELDS, *_UUID_FIELDS):
            op.drop_column(table, name, schema=_SCHEMA)
