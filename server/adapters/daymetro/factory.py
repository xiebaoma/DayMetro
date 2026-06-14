from __future__ import annotations

import sqlite3

from server.adapters.content.json_schedule import get_npc_schedule_slot
from server.adapters.daymetro.dialogue_effects import get_dialogue_options
from server.adapters.daymetro.dialogue_engine import DayMetroDialogueEngine
from server.adapters.daymetro.event_memory_mapper import DayMetroEventMemoryMapper
from server.adapters.daymetro.player_actions import action_label, apply_player_action, normalize_player_state
from server.adapters.daymetro.proactive_policy import DayMetroProactivePolicy
from server.adapters.daymetro.serializers import world_state_response
from server.adapters.daymetro.world_rules import location_matches
from server.adapters.persistence.sqlite_repositories import (
    SqliteDailyReviewRepository,
    SqliteEventRepository,
    SqliteMemoryRepository,
    SqliteNpcRepository,
    SqlitePerceptionRepository,
    SqliteRelationRepository,
    SqliteRuntimeStateRepository,
    SqliteSaveStateRepository,
)
from server.npc_agent.services.factory import build_npc_agent_core


def build_services(conn: sqlite3.Connection) -> dict:
    return build_npc_agent_core(
        npc_repo=SqliteNpcRepository(conn),
        runtime_repo=SqliteRuntimeStateRepository(conn),
        relation_repo=SqliteRelationRepository(conn),
        save_repo=SqliteSaveStateRepository(conn),
        review_repo=SqliteDailyReviewRepository(conn),
        memory_repo=SqliteMemoryRepository(conn),
        event_repo=SqliteEventRepository(conn),
        perception_repo=SqlitePerceptionRepository(conn),
        schedule_slot_provider=get_npc_schedule_slot,
        world_state_serializer=world_state_response,
        player_state_normalizer=normalize_player_state,
        player_action_applier=apply_player_action,
        action_labeler=action_label,
        dialogue_engine=DayMetroDialogueEngine(),
        options_provider=get_dialogue_options,
        event_memory_mapper=DayMetroEventMemoryMapper(),
        decision_policy=DayMetroProactivePolicy(),
        location_matcher=location_matches,
    )
