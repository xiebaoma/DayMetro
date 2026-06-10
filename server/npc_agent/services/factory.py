from __future__ import annotations

import sqlite3

from server.adapters.content.json_schedule import get_npc_schedule_slot
from server.adapters.persistence.sqlite_repositories import (
    SqliteEventRepository,
    SqliteMemoryRepository,
    SqliteNpcRepository,
    SqlitePerceptionRepository,
    SqliteRelationRepository,
    SqliteRuntimeStateRepository,
    SqliteSaveStateRepository,
)
from server.dialogue import DayMetroDialogueEngine
from server.adapters.daymetro.dialogue_effects import get_dialogue_options
from server.npc_agent.services.event_service import EventService
from server.npc_agent.services.interaction_service import InteractionService
from server.npc_agent.services.memory_service import MemoryService
from server.npc_agent.services.memory_system import MemorySystem
from server.npc_agent.services.npc_state_service import NpcStateService
from server.npc_agent.services.perception_service import PerceptionService
from server.npc_agent.services.world_service import WorldService


def build_services(conn: sqlite3.Connection) -> dict:
    npc_repo = SqliteNpcRepository(conn)
    runtime_repo = SqliteRuntimeStateRepository(conn)
    relation_repo = SqliteRelationRepository(conn)
    save_repo = SqliteSaveStateRepository(conn)
    memory_repo = SqliteMemoryRepository(conn)
    memory_system = MemorySystem(memory_repo)
    event_repo = SqliteEventRepository(conn)
    perception_repo = SqlitePerceptionRepository(conn)

    npc_state_service = NpcStateService(
        npc_repo=npc_repo,
        runtime_repo=runtime_repo,
        event_repo=event_repo,
        schedule_slot_provider=get_npc_schedule_slot,
    )
    world_service = WorldService(save_repo=save_repo, npc_state_service=npc_state_service)
    perception_service = PerceptionService(
        perception_repo=perception_repo,
        npc_state_service=npc_state_service,
    )
    interaction_service = InteractionService(
        npc_repo=npc_repo,
        relation_repo=relation_repo,
        runtime_repo=runtime_repo,
        memory_system=memory_system,
        event_repo=event_repo,
        perception_service=perception_service,
        dialogue_engine=DayMetroDialogueEngine(),
        options_provider=get_dialogue_options,
    )
    event_service = EventService(event_repo=event_repo, save_repo=save_repo)
    memory_service = MemoryService(memory_repo=memory_repo)
    return {
        "world": world_service,
        "interaction": interaction_service,
        "event": event_service,
        "perception": perception_service,
        "memory": memory_service,
        "npc_state": npc_state_service,
    }
