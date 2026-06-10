from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from server.logging_service import get_logger
from server.adapters.daymetro.player_actions import (
    action_label,
    apply_player_action,
    normalize_player_state,
)

logger = get_logger("daymetro.player_state")


class PlayerStateService:
    def __init__(self, save_repo, event_repo):
        self.save_repo = save_repo
        self.event_repo = event_repo

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

        before = normalize_player_state(json.loads(save_state["player_state"]))
        after, effects = apply_player_action(before, action_type)
        now = datetime.now(timezone.utc).isoformat()

        if game_time:
            self.save_repo.update_save_state(game_time, location, now)
        self.save_repo.update_player_state(after, now)
        event_id = self.event_repo.append_event(
            event_type=f"player_action_{action_type}",
            location=location,
            payload={
                "action_type": action_type,
                "action_label": action_label(action_type),
                "description": payload.get("description", action_label(action_type)),
                "before_state": before,
                "after_state": after,
                "effects": effects,
                **payload,
            },
            created_at=now,
        )
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
            "action_label": action_label(action_type),
            "effects": effects,
            "before_state": before,
            "player_state": after,
            "created_at": now,
        }
