from __future__ import annotations

from server.adapters.daymetro.factory import build_services
from server.database import get_connection
from server.npc_agent.domain.models import NpcState


def compute_npc_states(game_time: str) -> list[NpcState]:
    with get_connection() as conn:
        services = build_services(conn)
        return services["npc_state"].compute_npc_states(game_time)


def sync_runtime_state(game_time: str) -> None:
    with get_connection() as conn:
        services = build_services(conn)
        states = services["npc_state"].compute_npc_states(game_time)
        services["npc_state"].sync_runtime_state(states)
        conn.commit()


def get_npc_states(game_time: str) -> list[NpcState]:
    # Backward compatible wrapper.
    return compute_npc_states(game_time)
