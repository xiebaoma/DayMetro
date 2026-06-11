from __future__ import annotations

from datetime import datetime, timezone

from server.logging_service import get_logger
from server.npc_agent.ports.repositories import EventRepository

logger = get_logger("daymetro.event")


class EventService:
    def __init__(
        self,
        event_repo: EventRepository,
        save_repo=None,
        memory_system=None,
        relation_repo=None,
    ):
        self.event_repo = event_repo

    def log_event(self, event_type: str, location: str, payload: dict, game_time: str | None) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        event_id = self.event_repo.append_event(event_type, location, payload, now)
        logger.info("event_logged event_id=%s type=%s location=%s game_time=%s", event_id, event_type, location, game_time)
        return {"status": "logged", "event_id": event_id, "created_at": now}

    def list_logs(self, limit: int) -> dict:
        safe_limit = min(max(limit, 1), 500)
        return {"events": self.event_repo.list_recent(safe_limit)}
