from __future__ import annotations

from typing import Any

from server.npc_agent.ports.repositories import NpcRepository, RelationRepository, RuntimeStateRepository
from server.npc_agent.pipeline.event_pipeline import EventPipeline
from server.npc_agent.services.interaction_use_cases import (
    DialogueOptionsUseCase,
    DialogueTurnUseCase,
    InteractionEffectsUseCase,
)
from server.npc_agent.services.memory_system import MemorySystem
from server.npc_agent.services.presentation_service import PresentationService


class InteractionService:
    def __init__(
        self,
        npc_repo: NpcRepository,
        relation_repo: RelationRepository,
        runtime_repo: RuntimeStateRepository,
        memory_system: MemorySystem,
        event_pipeline: EventPipeline,
        perception_service,
        dialogue_engine,
        options_provider,
    ):
        presentation = PresentationService()
        self.options_use_case = DialogueOptionsUseCase(
            npc_repo=npc_repo,
            options_provider=options_provider,
            presentation=presentation,
        )
        self.turn_use_case = DialogueTurnUseCase(
            npc_repo=npc_repo,
            memory_system=memory_system,
            perception_service=perception_service,
            dialogue_engine=dialogue_engine,
        )
        self.effects_use_case = InteractionEffectsUseCase(
            relation_repo=relation_repo,
            runtime_repo=runtime_repo,
            memory_system=memory_system,
            event_pipeline=event_pipeline,
            presentation=presentation,
        )

    def get_dialogue_options(self, npc_id: str) -> dict[str, Any] | None:
        return self.options_use_case.execute(npc_id)

    def apply_choice(self, npc_id: str, option_id: str, use_llm: bool) -> dict[str, Any] | None:
        turn = self.turn_use_case.apply_choice(npc_id, option_id, use_llm)
        if turn is None:
            return None
        context, result = turn
        return self.effects_use_case.apply_choice_effects(
            context=context,
            option_id=option_id,
            result=result,
        )

    def free_talk(self, npc_id: str, message: str) -> dict[str, Any] | None:
        turn = self.turn_use_case.free_talk(npc_id, message)
        if turn is None:
            return None
        context, result = turn
        return self.effects_use_case.apply_free_talk_effects(
            context=context,
            message=message,
            result=result,
        )
