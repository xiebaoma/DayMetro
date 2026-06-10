from __future__ import annotations

from typing import Optional

from server.adapters.content.json_schedule import get_npc_schedule_slot
from server.adapters.daymetro.time_points import KEY_TIME_POINTS, get_world_time_label


def get_npc_location(npc_id: str, game_time: str) -> Optional[str]:
    slot = get_npc_schedule_slot(npc_id, game_time)
    return slot.get("location") if slot else None
