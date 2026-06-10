from __future__ import annotations

from typing import Any


DEFAULT_PLAYER_STATE = {
    "energy": 100,
    "mood": 70,
    "stress": 20,
    "focus": 60,
    "learning": 0,
    "code": 0,
    "social": 0,
    "health": 70,
    "sleep_quality": 80,
}


PLAYER_ACTION_EFFECTS: dict[str, dict[str, int]] = {
    "morning_prepare": {"energy": -5, "focus": 5},
    "commute_rest": {"energy": 8, "stress": -3, "focus": 4},
    "morning_meeting": {"stress": 6, "focus": 4, "social": 1},
    "work": {"energy": -14, "stress": 8, "focus": -5, "code": 6},
    "debug_bug": {"energy": -12, "stress": 10, "code": 8, "focus": -6},
    "lunch_chat": {"energy": 8, "mood": 4, "social": 6, "stress": -3},
    "nap": {"energy": 15, "focus": 6, "stress": -4},
    "study": {"energy": -8, "focus": -6, "learning": 7, "sleep_quality": -2},
    "play_game": {"mood": 8, "stress": -6, "focus": -4},
    "walk_playground": {"mood": 8, "stress": -10, "health": 5},
    "shower": {"health": 3, "stress": -4, "mood": 2},
    "late_browse": {"energy": -8, "mood": 5, "focus": -8, "sleep_quality": -10},
    "sleep": {"energy": 10, "stress": -5, "sleep_quality": 8},
}


ACTION_LABELS = {
    "morning_prepare": "晨间整理",
    "commute_rest": "通勤休息",
    "morning_meeting": "参加早会",
    "work": "推进工作",
    "debug_bug": "调试问题",
    "lunch_chat": "午饭聊天",
    "nap": "午休",
    "study": "学习",
    "play_game": "玩游戏放松",
    "walk_playground": "操场散步",
    "shower": "洗澡",
    "late_browse": "深夜浏览",
    "sleep": "睡觉",
}


def normalize_player_state(raw_state: dict[str, Any]) -> dict[str, int]:
    state = DEFAULT_PLAYER_STATE.copy()
    for key, value in raw_state.items():
        if key in state:
            state[key] = _clamp(int(value))
    return state


def apply_player_action(state: dict[str, int], action_type: str) -> tuple[dict[str, int], dict[str, int]]:
    effects = PLAYER_ACTION_EFFECTS.get(action_type)
    if effects is None:
        effects = {}
    next_state = state.copy()
    for key, delta in effects.items():
        next_state[key] = _clamp(next_state.get(key, DEFAULT_PLAYER_STATE.get(key, 0)) + delta)
    return next_state, effects


def action_label(action_type: str) -> str:
    return ACTION_LABELS.get(action_type, action_type)


def _clamp(value: int) -> int:
    return max(0, min(100, value))
