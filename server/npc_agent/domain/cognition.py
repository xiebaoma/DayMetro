from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EmotionState:
    mood: str
    intensity: int
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GoalState:
    current_goal: str
    priority: int
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BeliefState:
    npc_id: str
    emotion: EmotionState
    goal: GoalState
    relationship_signal: str
    player_state_signal: str
    facts: list[str]
    memory_highlights: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
