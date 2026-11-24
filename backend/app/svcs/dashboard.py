from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.trust.rules import Band, TrustRules
from ..infra.db.models import (
    ActionRequestRow, AgentRow, AgentSessionRow, ApprovalRecordRow, ApprovalRequestRow,
    AuthorizationDecisionRow, BehaviourEventRow, CapabilityRow, TaskRow, TrustEventRow, TrustScoreRow,
)
from ..integrations.browser.playwright import SUPPORTED_ACTIONS, PlaywrightBrowser
from ..schs.authz import Outcome
from ..schs.dashboard import (
    DashboardAgent, DashboardCapability, DashboardIntegration, DashboardOverview, DashboardSession,
    DashboardTask, DashboardTrust, TrustAdjustment, TrustRestrictions, TrustSummary,
)
from .access import session_status
from .identity import AgentNotFound
from .integrations import LOCAL_CATALOG, MCP_CATALOG, IntegrationRegistry


class DashboardQuery:
    def __init__(self, session: Session, rules: TrustRules) -> None:
        self._session = session
        self._rules = rules

    def overview(self, owner_id: UUID) -> DashboardOverview:
        now = datetime.now(UTC)
        active = (select(func.count()).select_from(AgentSessionRow)
                  .join(AgentRow, AgentRow.id == AgentSessionRow.agent_id)
                  .where(AgentRow.owner_id == owner_id, AgentSessionRow.revoked_at.is_(None),
                         AgentSessionRow.expires_at > now).scalar_subquery())
        pending = (select(func.count()).select_from(ApprovalRequestRow)
                   .join(AuthorizationDecisionRow, AuthorizationDecisionRow.id == ApprovalRequestRow.decision_id)
                   .join(ActionRequestRow, ActionRequestRow.id == AuthorizationDecisionRow.action_request_id)
                   .join(AgentSessionRow, AgentSessionRow.id == ActionRequestRow.session_id)
                   .join(AgentRow, AgentRow.id == AgentSessionRow.agent_id)
                   .outerjoin(ApprovalRecordRow, ApprovalRecordRow.approval_request_id == ApprovalRequestRow.id)
                   .where(ApprovalRequestRow.reviewer_id == owner_id, AgentRow.owner_id == owner_id,
                          AuthorizationDecisionRow.outcome == Outcome.HOLD, ApprovalRequestRow.snapshot.is_not(None),
                          ApprovalRecordRow.id.is_(None), ApprovalRequestRow.expires_at > now).scalar_subquery())
        sessions, approvals = self._session.execute(select(active, pending)).one()
        return DashboardOverview(active_sessions=sessions, pending_approvals=approvals)

    def agent(self, agent_id: UUID) -> DashboardAgent:
        now = datetime.now(UTC)
        sessions = self._session.scalars(select(AgentSessionRow).where(AgentSessionRow.agent_id == agent_id)
                                         .order_by(AgentSessionRow.created_at.desc(), AgentSessionRow.id.desc()))
        capabilities = self._session.execute(select(
            CapabilityRow.id, CapabilityRow.session_id, CapabilityRow.task_id, CapabilityRow.action,
            CapabilityRow.resource.label("resource_id"), CapabilityRow.expires_at, CapabilityRow.revoked_at,
        ).where(CapabilityRow.agent_id == agent_id).order_by(CapabilityRow.created_at.desc(), CapabilityRow.id.desc()))
        tasks = self._session.execute(select(TaskRow.id, TaskRow.objective.label("title"), TaskRow.status)
                                      .where(TaskRow.agent_id == agent_id)
                                      .order_by(TaskRow.created_at.desc(), TaskRow.id.desc()))
        return DashboardAgent(
            sessions=[DashboardSession(id=row.id, status=session_status(row, now), created_at=row.created_at,
                                       expires_at=row.expires_at) for row in sessions],
            capabilities=[DashboardCapability.model_validate(row) for row in capabilities],
            tasks=[DashboardTask.model_validate(row) for row in tasks],
            trust=self._agent_trust(agent_id),
        )

    def _effective_score(self, persisted: int | None) -> int:
        return self._rules.initial_score if persisted is None else persisted

    def _agent_trust(self, agent_id: UUID) -> DashboardTrust:
        persisted = self._session.scalar(select(TrustScoreRow.score).where(TrustScoreRow.agent_id == agent_id))
        score = self._effective_score(persisted)
        band = self._rules.band(score)
        if band == Band.SUSPENDED:
            restrictions = TrustRestrictions(mode="blocked", allowed_actions=[])
        elif band == Band.RESTRICTED:
            restrictions = TrustRestrictions(mode="allowlist", allowed_actions=list(self._rules.restricted_actions))
        else:
            restrictions = TrustRestrictions(mode="none", allowed_actions=[])
        history = self._session.scalars(select(TrustEventRow).outerjoin(
            BehaviourEventRow, BehaviourEventRow.id == TrustEventRow.behaviour_event_id,
        ).where(TrustEventRow.agent_id == agent_id).order_by(
            func.coalesce(BehaviourEventRow.observed_at, TrustEventRow.created_at).desc(),
            TrustEventRow.created_at.desc(), TrustEventRow.id.desc(),
        ))
        return DashboardTrust(score=score, score_persisted=persisted is not None, band=band,
                              history=[TrustAdjustment.model_validate(row) for row in history],
                              restrictions=restrictions)

    def trust(self, owner_id: UUID) -> list[TrustSummary]:
        active = (select(AgentSessionRow.agent_id, func.count().label("total"))
                  .where(AgentSessionRow.revoked_at.is_(None), AgentSessionRow.expires_at > datetime.now(UTC))
                  .group_by(AgentSessionRow.agent_id).subquery())
        scores = self._session.execute(
            select(AgentRow.id, TrustScoreRow.score, func.coalesce(active.c.total, 0))
            .outerjoin(TrustScoreRow, TrustScoreRow.agent_id == AgentRow.id)
            .outerjoin(active, active.c.agent_id == AgentRow.id)
            .where(AgentRow.owner_id == owner_id).order_by(AgentRow.created_at, AgentRow.id)
        )
        return [TrustSummary(agent_id=agent_id, score=self._effective_score(score), score_persisted=score is not None,
                             band=self._rules.band(self._effective_score(score)), active_sessions=total)
                for agent_id, score, total in scores]


def integration_status(browser: PlaywrightBrowser, registry: IntegrationRegistry) -> list[DashboardIntegration]:
    return [
        DashboardIntegration(
            id="browser", name="Browser", status="configured" if browser.has_allowed_pages else "disabled",
            operations=list(SUPPORTED_ACTIONS),
            detail=("At least one page is permitted by adapter configuration; browser availability is not checked."
                    if browser.has_allowed_pages else "No pages are permitted by adapter configuration."),
        ),
        DashboardIntegration(
            id="mcp", name="MCP", status="enabled" if registry.inspect(MCP_CATALOG).enabled else "disabled",
            operations=[MCP_CATALOG.action], detail="Built-in catalog tool; status reflects the process-local registry.",
        ),
        DashboardIntegration(
            id="local", name="Local", status="enabled" if registry.inspect(LOCAL_CATALOG).enabled else "disabled",
            operations=[LOCAL_CATALOG.action], detail="Built-in catalog tool; status reflects the process-local registry.",
        ),
    ]
