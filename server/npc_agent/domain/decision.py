from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from server.npc_agent.domain.cognition import BeliefState
from server.npc_agent.domain.memory import MemoryRecord


@dataclass(frozen=True)
class DecisionContext:
    npc: Any
    location: str
    game_time: str
    player_state: dict[str, int]
    belief: BeliefState
    memory: MemoryRecord | None
    recent_events: list[dict[str, Any]]


@dataclass(frozen=True)
class NpcIntent:
    npc_id: str
    npc_name: str
    intent_type: str
    reason: str
    speech: str
    target: str = "player"
    priority: int = 0
    parameters: dict[str, Any] = field(default_factory=dict)
    memory: MemoryRecord | None = None
