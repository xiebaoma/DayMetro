from __future__ import annotations

import json
from typing import Any

from server.adapters.daymetro.serializers import world_state_response
from server.npc_agent.services.npc_state_service import NpcStateService


class WorldService:
    def __init__(self, save_repo, npc_state_service: NpcStateService):
        self.save_repo = save_repo
        self.npc_state_service = npc_state_service

    def get_world_state(self) -> dict[str, Any] | None:
        save_state = self.save_repo.get_save_state()
        if save_state is None:
            return None
        npc_states = self.npc_state_service.compute_npc_states(save_state["game_time"])
        return world_state_response(
            save_state=save_state,
            npc_states=npc_states,
            player_state=json.loads(save_state["player_state"]),
        )

    def sync_npc_runtime(self) -> None:
        save_state = self.save_repo.get_save_state()
        if save_state is None:
            return
        states = self.npc_state_service.compute_npc_states(save_state["game_time"])
        self.npc_state_service.sync_runtime_state(states)
