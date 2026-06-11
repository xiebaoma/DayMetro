from __future__ import annotations

from typing import Protocol

from server.npc_agent.domain.actions import ActionResult
from server.npc_agent.domain.decision import NpcIntent


class ActionExecutorPort(Protocol):
    def execute(self, intent: NpcIntent, actions: list[dict]) -> ActionResult: ...
