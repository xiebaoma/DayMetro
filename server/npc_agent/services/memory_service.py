from __future__ import annotations

from server.npc_agent.ports.repositories import MemoryRepository
from server.npc_agent.services.memory_system import MemorySystem


class MemoryService:
    def __init__(self, memory_repo: MemoryRepository | None = None, system: MemorySystem | None = None):
        if system is None:
            if memory_repo is None:
                raise ValueError("memory_repo is required when system is not provided")
            system = MemorySystem(memory_repo)
        self.system = system

    def add_memory(self, npc_id: str, content: str, importance: int = 1) -> None:
        self.system.episodic.add(npc_id, content, importance=importance, source_type="manual")

    def get_recent_memories(self, npc_id: str, limit: int = 3) -> list[str]:
        return self.system.get_recent_memories(npc_id, limit)

    def get_recent_memory_records(self, npc_id: str, limit: int = 10) -> list[dict]:
        safe_limit = min(max(limit, 1), 100)
        context = self.system.build_context(npc_id, query="", per_layer=safe_limit)
        records = [
            *context.working,
            *context.episodic,
            *context.relationship,
            *context.semantic,
            *context.reflection,
        ]
        unique = {}
        for record in records:
            unique[record.id] = record
        ordered = sorted(unique.values(), key=lambda item: item.id, reverse=True)[:safe_limit]
        return [
            {
                "id": item.id,
                "npc_id": item.npc_id,
                "layer": item.layer,
                "content": item.content,
                "memory_type": item.memory_type,
                "importance": item.importance,
                "created_at": item.created_at,
                "last_used_at": item.last_used_at,
                "related_event_id": item.related_event_id,
                "source_type": item.source_type,
                "tags": item.tags,
                "related_entity": item.related_entity,
                "metadata": item.metadata,
            }
            for item in ordered
        ]
