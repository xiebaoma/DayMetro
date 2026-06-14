from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WorldEvent:
    id: int | None
    event_type: str
    location: str
    payload: dict[str, Any]
    created_at: str
    game_time: str | None = None


@dataclass(frozen=True)
class PerceivedFact:
    npc_id: str
    event_id: int | None
    source_type: str
    fact: str
    confidence: float
    observed_at: str
    metadata: dict[str, Any] = field(default_factory=dict)
