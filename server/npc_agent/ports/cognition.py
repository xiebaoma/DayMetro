from __future__ import annotations

from typing import Any, Protocol

from server.npc_agent.domain.cognition import BeliefState
from server.npc_agent.domain.memory import MemoryContext


class CognitionPolicyPort(Protocol):
    def build_belief(
        self,
        *,
        npc: Any,
        memory_context: MemoryContext,
        perceptions: list[dict],
        player_state: dict[str, int],
    ) -> BeliefState: ...
