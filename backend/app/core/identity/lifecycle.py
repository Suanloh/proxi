from ...models.records import AgentStatus


class InvalidAgentStatus(ValueError):
    pass


def validate_update(current: AgentStatus, requested: AgentStatus | None) -> None:
    if current == AgentStatus.REVOKED or requested == AgentStatus.REVOKED:
        raise InvalidAgentStatus("Revocation is terminal and requires the revoke operation")


def require_active(status: AgentStatus) -> None:
    if status != AgentStatus.ACTIVE:
        raise InvalidAgentStatus("Agent is not active")
