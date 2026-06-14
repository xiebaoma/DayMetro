from __future__ import annotations

from typing import Protocol

from server.npc_agent.domain.decision import DecisionContext, NpcIntent


class DecisionPolicyPort(Protocol):
    def decide(self, context: DecisionContext) -> NpcIntent | None: ...
