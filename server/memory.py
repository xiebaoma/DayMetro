from __future__ import annotations

from server.database import get_connection
from server.npc_agent.services.factory import build_services


def add_memory(npc_id: str, content: str, importance: int = 1) -> None:
    with get_connection() as conn:
        services = build_services(conn)
        services["memory"].add_memory(npc_id, content, importance)
        conn.commit()


def get_recent_memories(npc_id: str, limit: int = 3) -> list[str]:
    with get_connection() as conn:
        services = build_services(conn)
        return services["memory"].get_recent_memories(npc_id, limit)
