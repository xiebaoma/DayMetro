from __future__ import annotations

from server.npc_agent.domain.memory import EventMemoryMapping


class DayMetroEventMemoryMapper:
    def map_event(self, event_type: str, location: str, payload: dict) -> EventMemoryMapping | None:
        description = payload.get("description")
        task = payload.get("task", "一件事")

        if event_type in {"help_npc", "npc_helped", "help_completed"}:
            return EventMemoryMapping(
                content=description or f"玩家在{location}帮我处理了{task}。",
                memory_type="帮助",
                importance=4,
                tags=["help", "帮助", str(task)],
                relation_delta={"relation_delta": 2, "trust_delta": 5, "familiarity_delta": 1},
            )
        if event_type in {"promise_made", "player_promise"}:
            return EventMemoryMapping(
                content=description or f"玩家承诺会完成{task}。",
                memory_type="承诺",
                importance=4,
                tags=["promise", "承诺", str(task)],
                relation_delta={"familiarity_delta": 1},
            )
        if event_type in {"promise_broken", "no_show", "invitation_rejected"}:
            return EventMemoryMapping(
                content=description or f"玩家在{location}没有兑现约定：{task}。",
                memory_type="冲突",
                importance=5,
                tags=["conflict", "冲突", str(task)],
                relation_delta={"relation_delta": -2, "trust_delta": -5, "conflict_delta": 3},
            )
        if event_type in {"task_completed", "npc_task_completed"}:
            return EventMemoryMapping(
                content=description or f"玩家完成了{task}。",
                memory_type="任务进展",
                importance=4,
                tags=["task", "任务", str(task)],
                relation_delta={"relation_delta": 1, "trust_delta": 3, "familiarity_delta": 1},
            )
        if event_type in {"player_state_changed", "daily_state"}:
            return EventMemoryMapping(
                content=description or f"玩家在{location}的状态发生变化。",
                memory_type="玩家状态",
                importance=2,
                tags=["state", "状态"],
                relation_delta={"familiarity_delta": 1},
            )
        if event_type == "daily_review":
            return EventMemoryMapping(
                content=description or "玩家完成了一次每日复盘。",
                memory_type="共同经历",
                importance=3,
                tags=["review", "复盘"],
                relation_delta={"familiarity_delta": 1},
            )
        return None
