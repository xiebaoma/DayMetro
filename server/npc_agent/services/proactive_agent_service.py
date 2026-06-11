from __future__ import annotations

import json
from typing import Any

from server.logging_service import get_logger
from server.npc_agent.domain.decision import DecisionContext, NpcIntent
from server.npc_agent.domain.models import MemoryContext, MemoryRecord
from server.npc_agent.pipeline.event_pipeline import EventPipeline
from server.npc_agent.services.cognition_service import CognitionService
from server.npc_agent.services.decision_service import DecisionService
from server.npc_agent.services.execution_service import ExecutionService
from server.npc_agent.services.memory_system import MemorySystem
from server.npc_agent.services.npc_state_service import NpcStateService
from server.npc_agent.services.perception_service import PerceptionService

logger = get_logger("daymetro.proactive")


class ProactiveAgentService:
    def __init__(
        self,
        save_repo,
        event_repo,
        memory_system: MemorySystem,
        npc_state_service: NpcStateService,
        perception_service: PerceptionService,
        cognition_service: CognitionService,
        decision_service: DecisionService,
        execution_service: ExecutionService,
        event_pipeline: EventPipeline,
        player_state_normalizer,
        location_matcher,
    ):
        self.save_repo = save_repo
        self.event_repo = event_repo
        self.memory_system = memory_system
        self.npc_state_service = npc_state_service
        self.perception_service = perception_service
        self.cognition_service = cognition_service
        self.decision_service = decision_service
        self.execution_service = execution_service
        self.event_pipeline = event_pipeline
        self.player_state_normalizer = player_state_normalizer
        self.location_matcher = location_matcher

    def get_proactive_actions(self, location: str | None = None, limit: int = 3) -> dict[str, Any] | None:
        save_state = self.save_repo.get_save_state()
        if save_state is None:
            return None

        game_time = save_state["game_time"]
        current_location = location or save_state["current_location"]
        player_state = self.player_state_normalizer(json.loads(save_state["player_state"]))
        npc_states = [
            npc
            for npc in self.npc_state_service.compute_npc_states(game_time)
            if self.location_matcher(npc.current_location, current_location)
        ]
        recent_events = self.event_repo.list_recent(30)

        decisions: list[dict[str, Any]] = []
        for npc in npc_states:
            memory_context = self.memory_system.build_context(
                npc.id,
                query="帮助 冲突 任务进展 承诺 爽约 修复",
                per_layer=3,
            )
            memory = self._most_relevant_memory(memory_context)
            belief = self.cognition_service.build_belief(
                npc=npc,
                memory_context=memory_context,
                perceptions=self.perception_service.get_recent_perceptions(npc.id, 5),
                player_state=player_state,
            )
            intent = self.decision_service.decide(
                DecisionContext(
                    npc=npc,
                    location=current_location,
                    game_time=game_time,
                    player_state=player_state,
                    belief=belief,
                    memory=memory,
                    recent_events=recent_events,
                )
            )
            if intent is None:
                continue
            decision = self._to_response(
                intent=intent,
                actions=self.execution_service.execute_intent(intent).actions,
            )
            decisions.append(decision)
            if len(decisions) >= limit:
                break

        for decision in decisions:
            self.event_pipeline.record_event(
                event_type="npc_proactive_action",
                location=current_location,
                payload={
                    "npc_id": decision["npc_id"],
                    "proactive_type": decision["proactive_type"],
                    "reason": decision["reason"],
                    "actions": decision["actions"],
                },
                game_time=game_time,
            )
            logger.info(
                "proactive_action npc_id=%s type=%s reason=%s location=%s",
                decision["npc_id"],
                decision["proactive_type"],
                decision["reason"],
                current_location,
            )

        return {
            "location": current_location,
            "game_time": game_time,
            "proactive_actions": decisions,
        }

    def _most_relevant_memory(self, context: MemoryContext) -> MemoryRecord | None:
        memories = [*context.episodic, *context.relationship, *context.reflection]
        if not memories:
            return None
        memories.sort(key=lambda item: (item.importance, item.id), reverse=True)
        return memories[0]

    def _to_response(
        self,
        *,
        intent: NpcIntent,
        actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        result = {
            "npc_id": intent.npc_id,
            "npc_name": intent.npc_name,
            "proactive_type": intent.intent_type,
            "reason": intent.reason,
            "actions": actions,
        }
        if intent.memory is not None:
            result["memory"] = {
                "id": intent.memory.id,
                "memory_type": intent.memory.memory_type,
                "content": intent.memory.content,
                "related_event_id": intent.memory.related_event_id,
            }
        return result
