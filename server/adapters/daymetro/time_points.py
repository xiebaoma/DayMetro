from __future__ import annotations

KEY_TIME_POINTS = [
    {"time": "07:00", "label": "起床"},
    {"time": "08:00", "label": "去地铁"},
    {"time": "09:30", "label": "到公司"},
    {"time": "10:00", "label": "早会"},
    {"time": "12:00", "label": "午饭"},
    {"time": "14:00", "label": "下午工作"},
    {"time": "18:00", "label": "晚饭"},
    {"time": "19:00", "label": "返校"},
    {"time": "20:30", "label": "操场"},
    {"time": "22:00", "label": "洗澡"},
    {"time": "23:00", "label": "深夜浏览"},
    {"time": "24:00", "label": "睡觉"},
]


def _time_to_minutes(game_time: str) -> int:
    hour, minute = game_time.split(":")
    return int(hour) * 60 + int(minute)


def get_world_time_label(game_time: str) -> str:
    current_minutes = _time_to_minutes(game_time)
    latest_label = KEY_TIME_POINTS[0]["label"]
    for point in KEY_TIME_POINTS:
        if _time_to_minutes(point["time"]) <= current_minutes:
            latest_label = point["label"]
        else:
            break
    return latest_label
