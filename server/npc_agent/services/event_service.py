from __future__ import annotations

from datetime import datetime, timezone

from server.npc_agent.ports.repositories import EventRepository, SaveStateRepository


class EventService:
    def __init__(self, event_repo: EventRepository, save_repo: SaveStateRepository):
        self.event_repo = event_repo
        self.save_repo = save_repo

    def log_event(self, event_type: str, location: str, payload: dict, game_time: str | None) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        event_id = self.event_repo.append_event(event_type, location, payload, now)
        if game_time:
            self.save_repo.update_save_state(game_time, location, now)
        return {"status": "logged", "event_id": event_id, "created_at": now}

    def list_logs(self, limit: int) -> dict:
        safe_limit = min(max(limit, 1), 500)
        return {"events": self.event_repo.list_recent(safe_limit)}
