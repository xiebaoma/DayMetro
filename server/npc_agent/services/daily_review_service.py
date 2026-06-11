from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from server.logging_service import get_logger

logger = get_logger("daymetro.daily_review")


class DailyReviewService:
    def __init__(self, save_repo, event_repo, review_repo, player_state_normalizer):
        self.save_repo = save_repo
        self.event_repo = event_repo
        self.review_repo = review_repo
        self.player_state_normalizer = player_state_normalizer

    def generate_review(self, limit: int = 200) -> dict[str, Any] | None:
        save_state = self.save_repo.get_save_state()
        if save_state is None:
            return None

        events = list(reversed(self.event_repo.list_recent(limit)))
        route = _route_from_events(events, save_state["current_location"])
        important_events = _important_events(events)
        npc_interactions = _npc_interactions(events)
        relation_changes = _relation_changes(events)
        state_snapshot = self.player_state_normalizer(json.loads(save_state["player_state"]))
        keywords = _keywords(route, important_events, npc_interactions, state_snapshot)
        summary = _summary(route, important_events, npc_interactions, state_snapshot)
        tomorrow_hint = _tomorrow_hint(state_snapshot, important_events)

        now = datetime.now(timezone.utc).isoformat()
        review_id = self.review_repo.add_review(
            review_date=save_state["game_time"],
            route=route,
            important_events=important_events,
            npc_interactions=npc_interactions,
            relation_changes=relation_changes,
            state_snapshot=state_snapshot,
            keywords=keywords,
            summary=summary,
            tomorrow_hint=tomorrow_hint,
            created_at=now,
        )
        event_id = self.event_repo.append_event(
            event_type="daily_review",
            location=save_state["current_location"],
            payload={
                "review_id": review_id,
                "description": summary,
                "keywords": keywords,
            },
            created_at=now,
        )
        logger.info(
            "daily_review_generated review_id=%s event_id=%s keywords=%s",
            review_id,
            event_id,
            keywords,
        )
        review = self.review_repo.latest_review()
        if review is None:
            return None
        review["event_id"] = event_id
        return review

    def latest_review(self) -> dict[str, Any] | None:
        return self.review_repo.latest_review()


def _route_from_events(events: list[dict[str, Any]], current_location: str) -> list[str]:
    route: list[str] = []
    for event in events:
        location = event["location"]
        if location and (not route or route[-1] != location):
            route.append(location)
    if current_location and (not route or route[-1] != current_location):
        route.append(current_location)
    return route


def _important_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    important_prefixes = ("player_action_", "dialogue_", "help_", "promise_", "task_", "no_show")
    result = []
    for event in events:
        event_type = event["event_type"]
        if event_type == "npc_state_changed" or event_type == "tick":
            continue
        if event_type.startswith(important_prefixes) or event_type in {"daily_review"}:
            payload = event["payload"]
            result.append(
                {
                    "id": event["id"],
                    "event_type": event_type,
                    "location": event["location"],
                    "description": payload.get("description") or payload.get("choice_text") or event_type,
                    "created_at": event["created_at"],
                }
            )
    return result[-12:]


def _npc_interactions(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    interactions = []
    for event in events:
        payload = event["payload"]
        npc_id = payload.get("npc_id")
        if not npc_id:
            continue
        if event["event_type"].startswith("dialogue_") or event["event_type"] in {
            "help_npc",
            "no_show",
            "promise_made",
            "task_completed",
        }:
            interactions.append(
                {
                    "event_id": event["id"],
                    "npc_id": npc_id,
                    "event_type": event["event_type"],
                    "description": payload.get("description") or payload.get("choice_text") or event["event_type"],
                }
            )
    return interactions[-10:]


def _relation_changes(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes = []
    for event in events:
        payload = event["payload"]
        if "relation_delta" not in payload:
            continue
        changes.append(
            {
                "event_id": event["id"],
                "npc_id": payload.get("npc_id", ""),
                "relation_delta": payload.get("relation_delta", 0),
                "new_relation": payload.get("new_relation"),
            }
        )
    return changes[-10:]


def _keywords(
    route: list[str],
    important_events: list[dict[str, Any]],
    npc_interactions: list[dict[str, Any]],
    state_snapshot: dict[str, int],
) -> list[str]:
    keywords = list(dict.fromkeys(route))
    for event in important_events:
        event_type = event["event_type"]
        if event_type.startswith("player_action_"):
            keywords.append(event_type.removeprefix("player_action_"))
        elif event_type.startswith("dialogue_"):
            keywords.append("NPC互动")
    if npc_interactions:
        keywords.append("关系")
    if state_snapshot["stress"] >= 60:
        keywords.append("压力")
    if state_snapshot["code"] >= 10:
        keywords.append("代码")
    if state_snapshot["learning"] >= 5:
        keywords.append("学习")
    return list(dict.fromkeys(keywords))[:10]


def _summary(
    route: list[str],
    important_events: list[dict[str, Any]],
    npc_interactions: list[dict[str, Any]],
    state_snapshot: dict[str, int],
) -> str:
    route_text = " → ".join(route) if route else "未知路线"
    interaction_text = f"你和 {len(npc_interactions)} 次 NPC 互动留下了记录" if npc_interactions else "今天 NPC 互动较少"
    state_text = (
        f"最终精力 {state_snapshot['energy']}，心情 {state_snapshot['mood']}，"
        f"压力 {state_snapshot['stress']}，代码值 {state_snapshot['code']}，学习值 {state_snapshot['learning']}。"
    )
    event_text = f"系统记录了 {len(important_events)} 个关键事件。"
    return f"今日路线：{route_text}。{event_text}{interaction_text}。{state_text}"


def _tomorrow_hint(state_snapshot: dict[str, int], important_events: list[dict[str, Any]]) -> str:
    if state_snapshot["sleep_quality"] < 60:
        return "明天优先补睡眠，减少深夜浏览。"
    if state_snapshot["stress"] > 60:
        return "明天可以安排一次散步或午休，把压力先降下来。"
    if state_snapshot["code"] > state_snapshot["learning"] + 8:
        return "明天可以把工作中的问题整理成学习笔记。"
    if not important_events:
        return "明天可以多记录几个关键选择，让复盘更有连续性。"
    return "明天继续沿着今天的关键事件推进，优先处理最消耗精力的事情。"
