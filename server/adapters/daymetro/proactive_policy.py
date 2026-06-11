from __future__ import annotations

from typing import Any

from server.npc_agent.domain.decision import DecisionContext, NpcIntent


class DayMetroProactivePolicy:
    def decide(self, context: DecisionContext) -> NpcIntent | None:
        if _recently_triggered(context.npc.id, context.recent_events):
            return None

        minutes = _time_to_minutes(context.game_time)
        if context.memory is not None:
            memory_intent = self._memory_followup(context)
            if memory_intent is not None and not _recently_triggered(
                context.npc.id, context.recent_events, memory_intent.intent_type
            ):
                return memory_intent

        npc = context.npc
        if npc.role == "mentor" and context.location == "公司" and 570 <= minutes <= 660:
            return _intent(
                context,
                intent_type="reminder",
                reason="mentor_morning_goal",
                speech="早会前先把昨天进展和今天要卡的点想清楚，等会我会问。",
                parameters={"task": "准备早会汇报"},
            )

        if npc.role == "roommate" and context.location == "宿舍" and minutes >= 1320:
            if context.player_state["sleep_quality"] < 75 or context.player_state["energy"] < 80:
                return _intent(
                    context,
                    intent_type="state_check",
                    reason="late_dorm_low_recovery",
                    speech="你今天回来有点晚，明天还要去实习的话，今晚别刷太久。",
                    parameters={"question": "今天是不是又挺累？"},
                )

        if npc.role == "coworker" and context.location in {"公司", "食堂"} and context.player_state["stress"] >= 45:
            return _intent(
                context,
                intent_type="current_state_invite",
                reason="workday_stress",
                speech="看你今天压力有点上来，中午要不要一起吃饭，顺便缓一下？",
                parameters={"question": "中午一起吃饭吗？"},
            )

        if context.belief.relationship_signal in {"close", "friendly"} and npc.conflict_with_player <= 2:
            return _intent(
                context,
                intent_type="greeting",
                reason="positive_relation",
                speech="嘿，刚好碰到你。今天节奏怎么样？",
            )

        return None

    def _memory_followup(self, context: DecisionContext) -> NpcIntent | None:
        memory = context.memory
        if memory is None:
            return None
        npc = context.npc
        if memory.memory_type == "帮助" and npc.role == "coworker":
            return _intent(
                context,
                intent_type="memory_followup_help",
                reason=f"memory:{memory.id}",
                speech=f"昨天那件事我还记着，{_shorten(memory.content)}。中午我请你吃饭吧。",
                parameters={"question": "中午一起吃饭吗？"},
                memory=memory,
            )
        if memory.memory_type == "冲突" and npc.role == "roommate":
            return _intent(
                context,
                intent_type="memory_followup_conflict",
                reason=f"memory:{memory.id}",
                speech=f"我还记得上次那事，{_shorten(memory.content)}。今天你别又临时消失啊。",
                parameters={"question": "今晚还一起吗？"},
                memory=memory,
            )
        if memory.memory_type == "任务进展" and npc.role == "mentor":
            return _intent(
                context,
                intent_type="memory_followup_task",
                reason=f"memory:{memory.id}",
                speech=f"你之前的进展我看到了，{_shorten(memory.content)}。今天继续把风险讲清楚。",
                parameters={"task": "整理任务风险"},
                memory=memory,
            )
        return None


def _intent(
    context: DecisionContext,
    *,
    intent_type: str,
    reason: str,
    speech: str,
    parameters: dict[str, Any] | None = None,
    memory=None,
) -> NpcIntent:
    return NpcIntent(
        npc_id=context.npc.id,
        npc_name=context.npc.name,
        intent_type=intent_type,
        reason=reason,
        speech=speech,
        parameters=parameters or {},
        memory=memory,
    )


def _recently_triggered(
    npc_id: str,
    recent_events: list[dict[str, Any]],
    proactive_type: str | None = None,
) -> bool:
    for event in recent_events:
        if event["event_type"] != "npc_proactive_action":
            continue
        payload = event["payload"]
        if payload.get("npc_id") != npc_id:
            continue
        if proactive_type is None or payload.get("proactive_type") == proactive_type:
            return True
    return False


def _time_to_minutes(game_time: str) -> int:
    hour, minute = game_time.split(":")
    return int(hour) * 60 + int(minute)


def _shorten(text: str, limit: int = 24) -> str:
    return text if len(text) <= limit else text[:limit] + "..."
