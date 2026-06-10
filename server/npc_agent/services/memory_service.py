from __future__ import annotations

from server.npc_agent.ports.repositories import MemoryRepository
from server.npc_agent.services.memory_system import MemorySystem


class MemoryService:
    def __init__(self, memory_repo: MemoryRepository):
        self.system = MemorySystem(memory_repo)

    def add_memory(self, npc_id: str, content: str, importance: int = 1) -> None:
        self.system.episodic.add(npc_id, content, importance=importance, source_type="manual")

    def get_recent_memories(self, npc_id: str, limit: int = 3) -> list[str]:
        return self.system.get_recent_memories(npc_id, limit)
