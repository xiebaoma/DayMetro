from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


def _resolve_data_dir() -> Path:
    return Path(os.getenv("DAYMETRO_DATA_DIR", str(DEFAULT_DATA_DIR)))


def _read_json(filename: str) -> Any:
    with (_resolve_data_dir() / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


def _time_to_minutes(game_time: str) -> int:
    hour, minute = game_time.split(":")
    return int(hour) * 60 + int(minute)


def get_npc_schedule_slot(npc_id: str, game_time: str) -> dict | None:
    schedules = _read_json("schedules.json")
    npc_schedule = schedules.get(npc_id, [])
    current_minutes = _time_to_minutes(game_time)
    for slot in npc_schedule:
        start = _time_to_minutes(slot["start"])
        end = _time_to_minutes(slot["end"])
        if start <= current_minutes < end:
            return slot
    return None
