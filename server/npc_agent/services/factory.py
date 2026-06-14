from __future__ import annotations

from server.npc_agent.pipeline.event_pipeline import EventPipeline
from server.npc_agent.services.cognition_service import CognitionService
from server.npc_agent.services.daily_review_service import DailyReviewService
from server.npc_agent.services.decision_service import DecisionService
from server.npc_agent.services.event_service import EventService
from server.npc_agent.services.execution_service import ExecutionService
from server.npc_agent.services.interaction_service import InteractionService
from server.npc_agent.services.memory_service import MemoryService
from server.npc_agent.services.memory_system import MemorySystem
from server.npc_agent.services.npc_state_service import NpcStateService
from server.npc_agent.services.perception_service import PerceptionService
from server.npc_agent.services.player_state_service import PlayerStateService
from server.npc_agent.services.proactive_agent_service import ProactiveAgentService
from server.npc_agent.services.world_service import WorldService


def build_npc_agent_core(
    *,
    npc_repo,
    runtime_repo,
    relation_repo,
    save_repo,
    review_repo,
    memory_repo,
    event_repo,
    perception_repo,
    schedule_slot_provider,
    world_state_serializer,
    player_state_normalizer,
    player_action_applier,
    action_labeler,
    dialogue_engine,
    options_provider,
    event_memory_mapper=None,
    decision_policy=None,
    cognition_policy=None,
    action_executor=None,
    location_matcher=None,
) -> dict:
    memory_system = MemorySystem(memory_repo)
    npc_state_service = NpcStateService(
        npc_repo=npc_repo,
        runtime_repo=runtime_repo,
        event_repo=event_repo,
        schedule_slot_provider=schedule_slot_provider,
    )
    world_service = WorldService(
        save_repo=save_repo,
        npc_state_service=npc_state_service,
        player_state_normalizer=player_state_normalizer,
        serializer=world_state_serializer,
    )
    perception_service = PerceptionService(
        perception_repo=perception_repo,
        npc_state_service=npc_state_service,
    )
    event_service = EventService(event_repo=event_repo)
    event_pipeline = EventPipeline(
        event_service=event_service,
        save_repo=save_repo,
        perception_service=perception_service,
        memory_system=memory_system,
        relation_repo=relation_repo,
        npc_state_service=npc_state_service,
        event_memory_mapper=event_memory_mapper,
    )
    interaction_service = InteractionService(
        npc_repo=npc_repo,
        relation_repo=relation_repo,
        runtime_repo=runtime_repo,
        memory_system=memory_system,
        event_pipeline=event_pipeline,
        perception_service=perception_service,
        dialogue_engine=dialogue_engine,
        options_provider=options_provider,
    )
    memory_service = MemoryService(system=memory_system)
    player_state_service = PlayerStateService(
        save_repo=save_repo,
        event_repo=event_repo,
        player_state_normalizer=player_state_normalizer,
        player_action_applier=player_action_applier,
        action_labeler=action_labeler,
        event_pipeline=event_pipeline,
    )
    daily_review_service = DailyReviewService(
        save_repo=save_repo,
        event_repo=event_repo,
        review_repo=review_repo,
        player_state_normalizer=player_state_normalizer,
    )
    cognition_service = CognitionService(cognition_policy)
    decision_service = DecisionService(decision_policy)
    execution_service = ExecutionService(action_executor)
    proactive_agent_service = ProactiveAgentService(
        save_repo=save_repo,
        event_repo=event_repo,
        memory_system=memory_system,
        npc_state_service=npc_state_service,
        perception_service=perception_service,
        cognition_service=cognition_service,
        decision_service=decision_service,
        execution_service=execution_service,
        event_pipeline=event_pipeline,
        player_state_normalizer=player_state_normalizer,
        location_matcher=location_matcher or (lambda npc_location, requested_location: npc_location == requested_location),
    )
    return {
        "world": world_service,
        "interaction": interaction_service,
        "event": event_service,
        "event_pipeline": event_pipeline,
        "perception": perception_service,
        "memory": memory_service,
        "npc_state": npc_state_service,
        "relation": relation_repo,
        "player_state": player_state_service,
        "daily_review": daily_review_service,
        "proactive": proactive_agent_service,
        "cognition": cognition_service,
        "decision": decision_service,
        "execution": execution_service,
    }
