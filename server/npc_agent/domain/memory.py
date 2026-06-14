from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MemoryRecord:
    id: int
    npc_id: str
    layer: str
    content: str
    importance: int
    created_at: str
    memory_type: str
    last_used_at: str
    related_event_id: int | None
    source_type: str
    tags: list[str]
    related_entity: str
    metadata: dict[str, Any]


@dataclass
class MemoryContext:
    working: list[MemoryRecord]
    episodic: list[MemoryRecord]
    semantic: list[MemoryRecord]
    relationship: list[MemoryRecord]
    reflection: list[MemoryRecord]


@dataclass(frozen=True)
class EventMemoryMapping:
    content: str
    memory_type: str
    importance: int
    tags: list[str]
    relation_delta: dict[str, int]
