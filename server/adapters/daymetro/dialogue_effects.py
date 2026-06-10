from __future__ import annotations

from typing import Any


def get_dialogue_options() -> list[dict[str, str]]:
    return [
        {"id": "ask_status", "label": "问今天在忙什么"},
        {"id": "invite_lunch", "label": "邀请一起吃饭"},
        {"id": "complain_meeting", "label": "吐槽早会"},
        {"id": "care_mood", "label": "关心对方状态"},
        {"id": "end_chat", "label": "结束对话"},
    ]


def effects_by_option(option_id: str, current_location: str) -> dict[str, Any]:
    if option_id == "ask_status":
        return {
            "choice_text": "问今天在忙什么",
            "relation_delta": 1,
            "mood_override": None,
            "write_memory": True,
            "trigger_event": "dialogue_ask_status",
        }
    if option_id == "invite_lunch":
        relation_delta = 2 if current_location in {"公司", "食堂"} else 0
        mood_override = "social" if relation_delta > 0 else None
        return {
            "choice_text": "邀请一起吃饭",
            "relation_delta": relation_delta,
            "mood_override": mood_override,
            "write_memory": True,
            "trigger_event": "dialogue_invite_lunch",
        }
    if option_id == "complain_meeting":
        return {
            "choice_text": "吐槽早会",
            "relation_delta": -1,
            "mood_override": "irritated",
            "write_memory": False,
            "trigger_event": "dialogue_complain_meeting",
        }
    if option_id == "care_mood":
        return {
            "choice_text": "关心对方状态",
            "relation_delta": 2,
            "mood_override": "calm",
            "write_memory": True,
            "trigger_event": "dialogue_care_mood",
        }
    return {
        "choice_text": "结束对话",
        "relation_delta": 0,
        "mood_override": None,
        "write_memory": False,
        "trigger_event": "dialogue_end",
    }


def rule_based_reply(
    *,
    npc_name: str,
    option_id: str,
    mood: str,
    relation_with_player: int,
    current_action: str,
    goal: str,
    memory_hint: str,
) -> str:
    if option_id == "end_chat":
        return f"{npc_name}点点头：先这样，等会再聊。"

    if relation_with_player >= 12:
        tone = "亲近"
    elif relation_with_player >= 5:
        tone = "自然"
    else:
        tone = "克制"

    if mood in {"stressed", "irritated", "strict"}:
        mood_line = "我现在状态一般，先把手头事做完。"
    elif mood in {"calm", "social", "relaxed"}:
        mood_line = "今天状态还不错，聊两句没问题。"
    else:
        mood_line = "我在按计划推进。"

    if option_id == "ask_status":
        core = f"我在{current_action}，目标是{goal}。"
    elif option_id == "invite_lunch":
        if mood in {"stressed", "irritated", "strict"}:
            core = "这会儿任务卡得紧，中午可能来不及。"
        else:
            core = "可以，等到饭点我们一起去。"
    elif option_id == "complain_meeting":
        core = "早会确实有压力，但还是得把进展拿出来。"
    else:
        core = "谢谢你关心，我会调整一下节奏。"

    memory_line = f" 另外我记得：{memory_hint}" if memory_hint else ""
    return f"{npc_name}（{tone}语气）：{mood_line}{core}{memory_line}"
