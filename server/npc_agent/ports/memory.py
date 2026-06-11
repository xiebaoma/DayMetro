from __future__ import annotations

from typing import Protocol

from server.npc_agent.domain.memory import EventMemoryMapping, MemoryContext


class EventMemoryMapperPort(Protocol):
    def map_event(self, event_type: str, location: str, payload: dict) -> EventMemoryMapping | None: ...


class MemoryExtractorPort(Protocol):
    def extract_dialogue(self, npc_id: str, message: str, context: MemoryContext) -> list[str]: ...


class ReflectionPort(Protocol):
    def summarize(self, npc_id: str, context: MemoryContext) -> str | None: ...
