from __future__ import annotations

from server.npc_agent.domain.models import NpcState


class PerceptionService:
    def __init__(self, perception_repo, npc_state_service):
        self.perception_repo = perception_repo
        self.npc_state_service = npc_state_service

    def distribute_event_perception(
        self,
        *,
        event_id: int,
        event_type: str,
        location: str,
        payload: dict,
        game_time: str,
        observed_at: str,
    ) -> None:
        npc_states = self.npc_state_service.compute_npc_states(game_time)
        visible_npcs = [state for state in npc_states if state.current_location == location]

        event_fact = self._compose_fact(event_type, location, payload)
        source_type = self._source_type_for_event(event_type, payload)
        confidence = 0.9 if source_type in {"seen", "experienced"} else 0.7

        for npc in visible_npcs:
            self.perception_repo.add_perception(
                npc_id=npc.id,
                event_id=event_id,
                source_type=source_type,
                perceived_fact=event_fact,
                confidence=confidence,
                observed_at=observed_at,
            )

        for npc_id in payload.get("told_to_npc_ids", []):
            self.perception_repo.add_perception(
                npc_id=npc_id,
                event_id=event_id,
                source_type="told",
                perceived_fact=payload.get("shared_fact", event_fact),
                confidence=0.6,
                observed_at=observed_at,
            )

    def get_recent_perceptions(self, npc_id: str, limit: int = 5) -> list[dict]:
        return self.perception_repo.list_recent_perceptions(npc_id, limit)

    @staticmethod
    def _source_type_for_event(event_type: str, payload: dict) -> str:
        if payload.get("broadcast", False):
            return "heard"
        if event_type.startswith("dialogue_"):
            return "experienced"
        return "seen"

    @staticmethod
    def _compose_fact(event_type: str, location: str, payload: dict) -> str:
        if payload.get("description"):
            return str(payload["description"])
        return f"{location}发生事件：{event_type}"
