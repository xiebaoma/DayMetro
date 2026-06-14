from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from server.npc_agent.ports.presentation import DialogueOptionsProviderPort, DialoguePort
from server.npc_agent.ports.repositories import NpcRepository, RelationRepository, RuntimeStateRepository
from server.npc_agent.pipeline.event_pipeline import EventPipeline
from server.npc_agent.services.memory_system import MemorySystem
from server.npc_agent.services.perception_service import PerceptionService
from server.npc_agent.services.presentation_service import PresentationService


class DialogueOptionsUseCase:
    def __init__(
        self,
        *,
        npc_repo: NpcRepository,
        options_provider: DialogueOptionsProviderPort,
        presentation: PresentationService,
    ):
        self.npc_repo = npc_repo
        self.options_provider = options_provider
        self.presentation = presentation

    def execute(self, npc_id: str) -> dict[str, Any] | None:
        context = self.npc_repo.get_dialogue_context(npc_id)
        if context is None:
            return None
        return self.presentation.dialogue_options(context, self.options_provider())


class DialogueTurnUseCase:
    def __init__(
        self,
        *,
        npc_repo: NpcRepository,
        memory_system: MemorySystem,
        perception_service: PerceptionService,
        dialogue_engine: DialoguePort,
    ):
        self.npc_repo = npc_repo
        self.memory_system = memory_system
        self.perception_service = perception_service
        self.dialogue_engine = dialogue_engine

    def apply_choice(self, npc_id: str, option_id: str, use_llm: bool) -> tuple[Any, dict[str, Any]] | None:
        context = self.npc_repo.get_dialogue_context(npc_id)
        if context is None:
            return None
        memory_context = self.memory_system.build_context(npc_id, query=option_id, per_layer=1)
        memory_hint = self.memory_system.render_context_for_prompt(memory_context)
        recent_perceptions = self.perception_service.get_recent_perceptions(npc_id, 5)
        result = self.dialogue_engine.apply_choice(
            npc_id=context.npc_id,
            npc_name=context.name,
            personality=context.personality,
            current_location=context.current_location,
            current_action=context.current_action,
            mood=context.mood,
            goal=context.goal,
            relation_with_player=context.relation_with_player,
            identity_profile=context.identity_profile,
            option_id=option_id,
            game_time=context.game_time,
            recent_memory=memory_hint,
            recent_perceptions=recent_perceptions,
            use_llm=use_llm,
        )
        return context, result

    def free_talk(self, npc_id: str, message: str) -> tuple[Any, dict[str, Any]] | None:
        context = self.npc_repo.get_dialogue_context(npc_id)
        if context is None:
            return None
        memory_context = self.memory_system.build_context(npc_id, query=message, per_layer=1)
        memory_hint = self.memory_system.render_context_for_prompt(memory_context)
        recent_perceptions = self.perception_service.get_recent_perceptions(npc_id, 5)
        result = self.dialogue_engine.generate_free_reply(
            npc_id=npc_id,
            npc_name=context.name,
            personality=context.personality,
            message=message,
            identity_profile=context.identity_profile,
            recent_memory=memory_hint,
            recent_perceptions=recent_perceptions,
        )
        return context, result


class InteractionEffectsUseCase:
    def __init__(
        self,
        *,
        relation_repo: RelationRepository,
        runtime_repo: RuntimeStateRepository,
        memory_system: MemorySystem,
        event_pipeline: EventPipeline,
        presentation: PresentationService,
    ):
        self.relation_repo = relation_repo
        self.runtime_repo = runtime_repo
        self.memory_system = memory_system
        self.event_pipeline = event_pipeline
        self.presentation = presentation

    def apply_choice_effects(self, *, context, option_id: str, result: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        next_relation = self.relation_repo.apply_delta(
            context.npc_id,
            relation_delta=result["effects"]["relation_delta"],
            familiarity_delta=1,
        )
        self.runtime_repo.update_mood(context.npc_id, result["new_mood"], now)
        event_result = self.event_pipeline.record_event(
            event_type=result["trigger_event"],
            location=context.current_location,
            payload={
                "npc_id": context.npc_id,
                "option_id": option_id,
                "choice_text": result["choice_text"],
                "actions": result["actions"],
                "relation_delta": result["effects"]["relation_delta"],
                "new_relation": next_relation.relation_value,
                "new_trust": next_relation.trust_value,
                "new_conflict": next_relation.conflict_value,
                "new_familiarity": next_relation.familiarity_value,
                "new_mood": result["new_mood"],
            },
            game_time=context.game_time,
        )
        self.memory_system.remember_choice_outcome(
            npc_id=context.npc_id,
            choice_text=result["choice_text"],
            new_relation=next_relation.relation_value,
            new_mood=result["new_mood"],
            relation_delta=result["effects"]["relation_delta"],
            related_event_id=event_result["event_id"],
        )
        return self.presentation.dialogue_choice_result(context.npc_id, result, next_relation)

    def apply_free_talk_effects(self, *, context, message: str, result: dict[str, Any]) -> dict[str, Any]:
        event_result = self.event_pipeline.record_event(
            event_type="dialogue_free_talk",
            location=context.current_location,
            payload={
                "npc_id": context.npc_id,
                "message": message,
                "actions": result["actions"],
            },
            game_time=context.game_time,
        )
        self.relation_repo.apply_delta(context.npc_id, familiarity_delta=1)
        self.memory_system.remember_dialogue(
            npc_id=context.npc_id,
            message=message,
            related_event_id=event_result["event_id"],
        )
        return self.presentation.free_talk_result(context.npc_id, result)
