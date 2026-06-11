from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from server.logging_service import get_logger

logger = get_logger("daymetro.player_state")


class PlayerStateService:
    def __init__(
        self,
        save_repo,
        event_repo,
        player_state_normalizer,
        player_action_applier,
        action_labeler,
        event_pipeline=None,
    ):
        self.save_repo = save_repo
        self.event_repo = event_repo
        self.player_state_normalizer = player_state_normalizer
        self.player_action_applier = player_action_applier
        self.action_labeler = action_labeler
        self.event_pipeline = event_pipeline

    def apply_action(
        self,
        *,
        action_type: str,
        location: str,
        game_time: str | None,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        save_state = self.save_repo.get_save_state()
        if save_state is None:
            return {"status": "missing_save_state"}

        before = self.player_state_normalizer(json.loads(save_state["player_state"]))
        after, effects = self.player_action_applier(before, action_type)
        now = datetime.now(timezone.utc).isoformat()

        if game_time:
            self.save_repo.update_save_state(game_time, location, now)
        self.save_repo.update_player_state(after, now)
        event_payload = {
            "action_type": action_type,
            "action_label": self.action_labeler(action_type),
            "description": payload.get("description", self.action_labeler(action_type)),
            "before_state": before,
            "after_state": after,
            "effects": effects,
            **payload,
        }
        if self.event_pipeline is not None:
            event_result = self.event_pipeline.record_event(
                event_type=f"player_action_{action_type}",
                location=location,
                payload=event_payload,
                game_time=game_time,
            )
            event_id = event_result["event_id"]
            created_at = event_result["created_at"]
        else:
            event_id = self.event_repo.append_event(
                event_type=f"player_action_{action_type}",
                location=location,
                payload=event_payload,
                created_at=now,
            )
            created_at = now
        logger.info(
            "player_state_updated action_type=%s location=%s event_id=%s effects=%s",
            action_type,
            location,
            event_id,
            effects,
        )

        return {
            "status": "applied",
            "event_id": event_id,
            "action_type": action_type,
            "action_label": self.action_labeler(action_type),
            "effects": effects,
            "before_state": before,
            "player_state": after,
            "created_at": created_at,
        }
