from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from server.logging_service import get_logger
from server.adapters.daymetro.player_actions import normalize_player_state
from server.npc_agent.domain.models import MemoryRecord, NpcState
from server.npc_agent.services.action_system import say, validate_action, validate_action_plan
from server.npc_agent.services.memory_system import MemorySystem
from server.npc_agent.services.npc_state_service import NpcStateService

logger = get_logger("daymetro.proactive")


class ProactiveAgentService:
    def __init__(self, save_repo, event_repo, memory_system: MemorySystem, npc_state_service: NpcStateService):
        self.save_repo = save_repo
        self.event_repo = event_repo
        self.memory_system = memory_system
        self.npc_state_service = npc_state_service

    def get_proactive_actions(self, location: str | None = None, limit: int = 3) -> dict[str, Any] | None:
        save_state = self.save_repo.get_save_state()
        if save_state is None:
            return None

        game_time = save_state["game_time"]
        current_location = location or save_state["current_location"]
        player_state = normalize_player_state(json.loads(save_state["player_state"]))
        npc_states = [
            npc
            for npc in self.npc_state_service.compute_npc_states(game_time)
            if _location_matches(npc.current_location, current_location)
        ]
        recent_events = self.event_repo.list_recent(30)

        decisions: list[dict[str, Any]] = []
        for npc in npc_states:
            memory = self._most_relevant_memory(npc)
            decision = self._decide(
                npc=npc,
                location=current_location,
                game_time=game_time,
                player_state=player_state,
                memory=memory,
                recent_events=recent_events,
            )
            if decision is not None:
                decisions.append(decision)
            if len(decisions) >= limit:
                break

        now = datetime.now(timezone.utc).isoformat()
        for decision in decisions:
            self.event_repo.append_event(
                event_type="npc_proactive_action",
                location=current_location,
                payload={
                    "npc_id": decision["npc_id"],
                    "proactive_type": decision["proactive_type"],
                    "reason": decision["reason"],
                    "actions": decision["actions"],
                },
                created_at=now,
            )
            logger.info(
                "proactive_action npc_id=%s type=%s reason=%s location=%s",
                decision["npc_id"],
                decision["proactive_type"],
                decision["reason"],
                current_location,
            )

        return {
            "location": current_location,
            "game_time": game_time,
            "proactive_actions": decisions,
        }

    def _decide(
        self,
        *,
        npc: NpcState,
        location: str,
        game_time: str,
        player_state: dict[str, int],
        memory: MemoryRecord | None,
        recent_events: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if self._recently_triggered(npc.id, recent_events):
            return None

        minutes = _time_to_minutes(game_time)
        if memory is not None:
            memory_decision = self._memory_followup(npc, memory)
            if memory_decision is not None and not self._recently_triggered(
                npc.id, recent_events, memory_decision["proactive_type"]
            ):
                return memory_decision

        if npc.role == "mentor" and location == "公司" and 570 <= minutes <= 660:
            return _decision(
                npc,
                proactive_type="reminder",
                reason="mentor_morning_goal",
                text="早会前先把昨天进展和今天要卡的点想清楚，等会我会问。",
                extra_actions=[
                    validate_action({"action": "start_task", "task": "准备早会汇报"}),
                ],
            )

        if npc.role == "roommate" and location == "宿舍" and minutes >= 1320:
            if player_state["sleep_quality"] < 75 or player_state["energy"] < 80:
                return _decision(
                    npc,
                    proactive_type="state_check",
                    reason="late_dorm_low_recovery",
                    text="你今天回来有点晚，明天还要去实习的话，今晚别刷太久。",
                    extra_actions=[
                        validate_action(
                            {"action": "ask_question", "target": "player", "question": "今天是不是又挺累？"}
                        )
                    ],
                )

        if npc.role == "coworker" and location in {"公司", "食堂"} and player_state["stress"] >= 45:
            return _decision(
                npc,
                proactive_type="current_state_invite",
                reason="workday_stress",
                text="看你今天压力有点上来，中午要不要一起吃饭，顺便缓一下？",
                extra_actions=[
                    validate_action({"action": "ask_question", "target": "player", "question": "中午一起吃饭吗？"})
                ],
            )

        if npc.relation_with_player >= 8 and npc.conflict_with_player <= 2:
            return _decision(
                npc,
                proactive_type="greeting",
                reason="positive_relation",
                text="嘿，刚好碰到你。今天节奏怎么样？",
                extra_actions=[
                    validate_action({"action": "look_at", "target": "player"}),
                ],
            )

        return None

    def _memory_followup(self, npc: NpcState, memory: MemoryRecord) -> dict[str, Any] | None:
        content = memory.content
        if memory.memory_type == "帮助" and npc.role == "coworker":
            return _decision(
                npc,
                proactive_type="memory_followup_help",
                reason=f"memory:{memory.id}",
                text=f"昨天那件事我还记着，{_shorten(content)}。中午我请你吃饭吧。",
                memory=memory,
                extra_actions=[
                    validate_action({"action": "ask_question", "target": "player", "question": "中午一起吃饭吗？"})
                ],
            )
        if memory.memory_type == "冲突" and npc.role == "roommate":
            return _decision(
                npc,
                proactive_type="memory_followup_conflict",
                reason=f"memory:{memory.id}",
                text=f"我还记得上次那事，{_shorten(content)}。今天你别又临时消失啊。",
                memory=memory,
                extra_actions=[
                    validate_action({"action": "ask_question", "target": "player", "question": "今晚还一起吗？"})
                ],
            )
        if memory.memory_type == "任务进展" and npc.role == "mentor":
            return _decision(
                npc,
                proactive_type="memory_followup_task",
                reason=f"memory:{memory.id}",
                text=f"你之前的进展我看到了，{_shorten(content)}。今天继续把风险讲清楚。",
                memory=memory,
                extra_actions=[
                    validate_action({"action": "start_task", "task": "整理任务风险"}),
                ],
            )
        return None

    def _most_relevant_memory(self, npc: NpcState) -> MemoryRecord | None:
        context = self.memory_system.build_context(
            npc.id,
            query="帮助 冲突 任务进展 承诺 爽约 修复",
            per_layer=3,
        )
        memories = [*context.episodic, *context.relationship, *context.reflection]
        if not memories:
            return None
        memories.sort(key=lambda item: (item.importance, item.id), reverse=True)
        return memories[0]

    @staticmethod
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


def _decision(
    npc: NpcState,
    *,
    proactive_type: str,
    reason: str,
    text: str,
    extra_actions: list[dict[str, Any]] | None = None,
    memory: MemoryRecord | None = None,
) -> dict[str, Any]:
    actions = validate_action_plan(
        [
            validate_action({"action": "look_at", "target": "player"}),
            say(text),
            *(extra_actions or []),
        ]
    )
    result = {
        "npc_id": npc.id,
        "npc_name": npc.name,
        "proactive_type": proactive_type,
        "reason": reason,
        "actions": actions,
    }
    if memory is not None:
        result["memory"] = {
            "id": memory.id,
            "memory_type": memory.memory_type,
            "content": memory.content,
            "related_event_id": memory.related_event_id,
        }
    return result


def _time_to_minutes(game_time: str) -> int:
    hour, minute = game_time.split(":")
    return int(hour) * 60 + int(minute)


def _location_matches(npc_location: str, requested_location: str) -> bool:
    if npc_location == requested_location:
        return True
    return requested_location == "公司" and npc_location == "会议室"


def _shorten(text: str, limit: int = 24) -> str:
    return text if len(text) <= limit else text[:limit] + "..."
