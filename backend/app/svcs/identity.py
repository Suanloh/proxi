from dataclasses import replace
from typing import TypedDict, Unpack
from uuid import UUID

from ..core.events import NO_EVENTS, EventBus, EventType
from ..core.identity.lifecycle import require_active, validate_update
from ..core.repositories import AgentRepository, RecordRepository
from ..models.records import Agent, AgentStatus, AgentType, User


class AgentNotFound(LookupError):
    pass


class OwnerNotAuthorized(PermissionError):
    pass


class AgentChanges(TypedDict, total=False):
    name: str
    type: AgentType
    description: str | None
    status: AgentStatus


class AgentIdentityService:
    def __init__(self, agents: AgentRepository, users: RecordRepository[User], *, events: EventBus = NO_EVENTS) -> None:
        self._agents = agents
        self._users = users
        self.events = events

    def require_active_owner(self, owner_id: UUID) -> None:
        user = self._users.get(owner_id)
        if user is None or user.status != "active":
            raise OwnerNotAuthorized("An active application user is required")

    def register(self, owner_id: UUID, name: str, agent_type: AgentType, description: str | None = None) -> Agent:
        agent = self._agents.add(Agent(owner_id=owner_id, name=name, type=agent_type, description=description))
        self.events.owner(EventType.AGENT_REGISTERED, owner_id, agent.id)
        return agent

    def list_owned(self, owner_id: UUID) -> list[Agent]:
        return self._agents.list_owned(owner_id)

    def get_owned(self, owner_id: UUID, agent_id: UUID, *, for_update: bool = False) -> Agent:
        agent = self._agents.get_owned(owner_id, agent_id, for_update=for_update)
        if agent is None:
            raise AgentNotFound("Agent not found")
        return agent

    def update(self, owner_id: UUID, agent_id: UUID, **changes: Unpack[AgentChanges]) -> Agent:
        agent = self.get_owned(owner_id, agent_id, for_update=True)
        validate_update(agent.status, changes.get("status"))
        updated = self._agents.update(replace(
            agent,
            name=changes.get("name", agent.name),
            type=changes.get("type", agent.type),
            description=changes.get("description", agent.description),
            status=changes.get("status", agent.status),
        ))
        if updated != agent:
            kind = (EventType.AGENT_SUSPENDED if updated.status == AgentStatus.SUSPENDED and updated.status != agent.status
                    else EventType.AGENT_UPDATED)
            self.events.owner(kind, owner_id, agent.id)
        return updated

    def suspend(self, owner_id: UUID, agent_id: UUID) -> Agent:
        return self.update(owner_id, agent_id, status=AgentStatus.SUSPENDED)

    def revoke(self, owner_id: UUID, agent_id: UUID) -> Agent:
        agent = self.get_owned(owner_id, agent_id, for_update=True)
        if agent.status == AgentStatus.REVOKED:
            return agent
        revoked = self._agents.update(replace(agent, status=AgentStatus.REVOKED))
        self.events.owner(EventType.AGENT_REVOKED, owner_id, agent.id)
        return revoked

    def resolve(self, agent_id: UUID, *, for_update: bool = False) -> Agent:
        agent = self._agents.get_for_update(agent_id) if for_update else self._agents.get(agent_id)
        if agent is None:
            raise AgentNotFound("Agent not found")
        return agent

    def validate_active(self, agent_id: UUID, *, for_update: bool = False) -> Agent:
        """Check status of an independently identified agent; a UUID is not authentication."""
        agent = self.resolve(agent_id, for_update=for_update)
        require_active(agent.status)
        return agent
