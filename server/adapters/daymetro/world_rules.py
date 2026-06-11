from __future__ import annotations


def location_matches(npc_location: str, requested_location: str) -> bool:
    if npc_location == requested_location:
        return True
    return requested_location == "公司" and npc_location == "会议室"
