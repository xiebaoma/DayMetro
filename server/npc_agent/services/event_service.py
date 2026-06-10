from __future__ import annotations

from datetime import datetime, timezone

from server.logging_service import get_logger
from server.npc_agent.ports.repositories import EventRepository, RelationRepository, SaveStateRepository
from server.npc_agent.services.memory_system import MemorySystem

logger = get_logger("daymetro.event")


class EventService:
    def __init__(
        self,
        event_repo: EventRepository,
        save_repo: SaveStateRepository,
        memory_system: MemorySystem | None = None,
        relation_repo: RelationRepository | None = None,
    ):
        self.event_repo = event_repo
        self.save_repo = save_repo
        self.memory_system = memory_system
        self.relation_repo = relation_repo

    def log_event(self, event_type: str, location: str, payload: dict, game_time: str | None) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        event_id = self.event_repo.append_event(event_type, location, payload, now)
        logger.info("event_logged event_id=%s type=%s location=%s game_time=%s", event_id, event_type, location, game_time)
        if game_time:
            self.save_repo.update_save_state(game_time, location, now)
        self._generate_memory_from_event(
            event_id=event_id,
            event_type=event_type,
            location=location,
            payload=payload,
        )
        return {"status": "logged", "event_id": event_id, "created_at": now}

    def list_logs(self, limit: int) -> dict:
        safe_limit = min(max(limit, 1), 500)
        return {"events": self.event_repo.list_recent(safe_limit)}

    def _generate_memory_from_event(
        self,
        *,
        event_id: int,
        event_type: str,
        location: str,
        payload: dict,
    ) -> None:
        if self.memory_system is None:
            return

        npc_id = payload.get("npc_id") or payload.get("target_npc_id")
        if not npc_id:
            return

        memory = _memory_from_event(event_type, location, payload)
        if memory is None:
            return

        self.memory_system.remember_event(
            npc_id=str(npc_id),
            content=memory["content"],
            memory_type=memory["memory_type"],
            importance=memory["importance"],
            related_event_id=event_id,
            tags=memory["tags"],
            metadata={"event_type": event_type, "location": location},
        )
        if self.relation_repo is not None:
            self.relation_repo.apply_delta(str(npc_id), **memory["relation_delta"])
        logger.info(
            "memory_generated_from_event event_id=%s npc_id=%s memory_type=%s",
            event_id,
            npc_id,
            memory["memory_type"],
        )


def _memory_from_event(event_type: str, location: str, payload: dict) -> dict | None:
    description = payload.get("description")
    task = payload.get("task", "一件事")

    if event_type in {"help_npc", "npc_helped", "help_completed"}:
        return {
            "content": description or f"玩家在{location}帮我处理了{task}。",
            "memory_type": "帮助",
            "importance": 4,
            "tags": ["help", "帮助", str(task)],
            "relation_delta": {"relation_delta": 2, "trust_delta": 5, "familiarity_delta": 1},
        }
    if event_type in {"promise_made", "player_promise"}:
        return {
            "content": description or f"玩家承诺会完成{task}。",
            "memory_type": "承诺",
            "importance": 4,
            "tags": ["promise", "承诺", str(task)],
            "relation_delta": {"familiarity_delta": 1},
        }
    if event_type in {"promise_broken", "no_show", "invitation_rejected"}:
        return {
            "content": description or f"玩家在{location}没有兑现约定：{task}。",
            "memory_type": "冲突",
            "importance": 5,
            "tags": ["conflict", "冲突", str(task)],
            "relation_delta": {"relation_delta": -2, "trust_delta": -5, "conflict_delta": 3},
        }
    if event_type in {"task_completed", "npc_task_completed"}:
        return {
            "content": description or f"玩家完成了{task}。",
            "memory_type": "任务进展",
            "importance": 4,
            "tags": ["task", "任务", str(task)],
            "relation_delta": {"relation_delta": 1, "trust_delta": 3, "familiarity_delta": 1},
        }
    if event_type in {"player_state_changed", "daily_state"}:
        return {
            "content": description or f"玩家在{location}的状态发生变化。",
            "memory_type": "玩家状态",
            "importance": 2,
            "tags": ["state", "状态"],
            "relation_delta": {"familiarity_delta": 1},
        }
    if event_type == "daily_review":
        return {
            "content": description or "玩家完成了一次每日复盘。",
            "memory_type": "共同经历",
            "importance": 3,
            "tags": ["review", "复盘"],
            "relation_delta": {"familiarity_delta": 1},
        }
    return None
