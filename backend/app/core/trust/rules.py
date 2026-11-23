from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...schs.intent import Action
from ..behaviour.rules import Rule

Score = Annotated[int, Field(strict=True, ge=0, le=100)]
Penalty = Annotated[int, Field(strict=True, ge=-100, le=0)]
Window = Annotated[int, Field(strict=True, ge=1, le=86_400)]
Repetitions = Annotated[int, Field(strict=True, ge=2, le=100)]


class Band(StrEnum):
    NORMAL = "normal"
    MONITORED = "enhanced_monitoring"
    RESTRICTED = "restricted"
    SUSPENDED = "suspended_pending_review"


class Weights(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    unusual_action: Penalty = -5
    denied_action: Penalty = -5
    restricted_resource_attempt: Penalty = -15
    permission_boundary_violation: Penalty = -15
    unexpected_action_sequence: Penalty = -5
    repeated_denied_action: Penalty = -25
    repeated_approval_requests: Penalty = -5
    sustained_compliant_behaviour: Annotated[int, Field(strict=True, ge=1, le=100)] = 5

    def for_rule(self, rule: Rule) -> int:
        return getattr(self, rule.value, 0)


class TrustRules(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    initial_score: Score = 100
    normal_min: Score = 80
    monitored_min: Score = 50
    restricted_min: Score = 20
    restricted_actions: tuple[Action, ...] = ()
    predecessors: dict[Action, tuple[Action, ...]] = Field(default_factory=dict)
    repeat_window_seconds: Window = 300
    denied_threshold: Repetitions = 3
    approval_threshold: Repetitions = 3
    recovery_successes: Repetitions = 5
    recovery_cooldown_seconds: Window = 300
    weights: Weights = Field(default_factory=Weights)

    @model_validator(mode="after")
    def ordered_bands(self) -> Self:
        if not 0 < self.restricted_min < self.monitored_min < self.normal_min <= 100:
            raise ValueError("Trust band minima must strictly increase above zero")
        if any(not values for values in self.predecessors.values()):
            raise ValueError("Each configured sequence must have at least one predecessor")
        return self

    def band(self, score: int) -> Band:
        if score >= self.normal_min:
            return Band.NORMAL
        if score >= self.monitored_min:
            return Band.MONITORED
        if score >= self.restricted_min:
            return Band.RESTRICTED
        return Band.SUSPENDED


def bounded_score(score: int, delta: int) -> int:
    return max(0, min(100, score + delta))
