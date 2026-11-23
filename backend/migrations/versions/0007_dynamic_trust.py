"""Persist behaviour observations and explainable trust adjustments."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_SCHEMA = "proxi"
_BEHAVIOUR = "behaviour_events"
_SCORES = "trust_scores"
_EVENTS = "trust_events"


def upgrade() -> None:
    for column in (
        sa.Column("observed_at", sa.DateTime(timezone=True)), sa.Column("request_id", sa.Uuid()),
        sa.Column("session_id", sa.Uuid()), sa.Column("task_id", sa.Uuid()), sa.Column("action", sa.String()),
        sa.Column("reason_code", sa.String()), sa.Column("band", sa.String()), sa.Column("reviewer_id", sa.Uuid()),
    ):
        op.add_column(_BEHAVIOUR, column, schema=_SCHEMA)
    op.create_foreign_key(op.f("fk_behaviour_events_reviewer_id"), _BEHAVIOUR, "users", ["reviewer_id"], ["id"],
                          source_schema=_SCHEMA, referent_schema=_SCHEMA, ondelete="RESTRICT")
    op.create_index("ix_behaviour_events_agent_reason_observed", _BEHAVIOUR,
                    ["agent_id", "reason_code", "observed_at"], schema=_SCHEMA)
    op.create_index("ix_behaviour_events_scope_type_observed", _BEHAVIOUR,
                    ["agent_id", "session_id", "task_id", "event_type", "observed_at"], schema=_SCHEMA)
    op.create_index("ix_behaviour_events_agent_request", _BEHAVIOUR, ["agent_id", "request_id"], schema=_SCHEMA)
    op.add_column(_SCORES, sa.Column("compliant_count", sa.Integer(), nullable=False, server_default="0"), schema=_SCHEMA)
    op.add_column(_SCORES, sa.Column("last_adjusted_at", sa.DateTime(timezone=True)), schema=_SCHEMA)
    op.add_column(_SCORES, sa.Column("last_violation_at", sa.DateTime(timezone=True)), schema=_SCHEMA)
    op.create_check_constraint(op.f("ck_trust_scores_compliant_count"), _SCORES, "compliant_count >= 0", schema=_SCHEMA)
    for column in (sa.Column("behaviour_event_id", sa.Uuid()), sa.Column("previous_score", sa.Integer()),
                   sa.Column("new_score", sa.Integer()), sa.Column("rule", sa.String())):
        op.add_column(_EVENTS, column, schema=_SCHEMA)
    op.create_foreign_key(op.f("fk_trust_events_behaviour_event_id"), _EVENTS, _BEHAVIOUR,
                          ["behaviour_event_id"], ["id"], source_schema=_SCHEMA,
                          referent_schema=_SCHEMA, ondelete="RESTRICT")
    op.create_unique_constraint(op.f("uq_trust_events_behaviour_event_id"), _EVENTS, ["behaviour_event_id"], schema=_SCHEMA)


def downgrade() -> None:
    op.drop_constraint(op.f("uq_trust_events_behaviour_event_id"), _EVENTS, type_="unique", schema=_SCHEMA)
    op.drop_constraint(op.f("fk_trust_events_behaviour_event_id"), _EVENTS, type_="foreignkey", schema=_SCHEMA)
    op.drop_constraint(op.f("ck_trust_scores_compliant_count"), _SCORES, type_="check", schema=_SCHEMA)
    op.drop_constraint(op.f("fk_behaviour_events_reviewer_id"), _BEHAVIOUR, type_="foreignkey", schema=_SCHEMA)
    for index in ("ix_behaviour_events_agent_request", "ix_behaviour_events_scope_type_observed",
                  "ix_behaviour_events_agent_reason_observed"):
        op.drop_index(index, table_name=_BEHAVIOUR, schema=_SCHEMA)
    for table, columns in (
        (_EVENTS, ("behaviour_event_id", "previous_score", "new_score", "rule")),
        (_SCORES, ("compliant_count", "last_adjusted_at", "last_violation_at")),
        (_BEHAVIOUR, ("observed_at", "request_id", "session_id", "task_id", "action", "reason_code", "band", "reviewer_id")),
    ):
        for column in columns:
            op.drop_column(table, column, schema=_SCHEMA)
