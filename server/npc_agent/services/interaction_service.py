from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from server.npc_agent.ports.repositories import (
    EventRepository,
    NpcRepository,
    RelationRepository,
    RuntimeStateRepository,
)
from server.npc_agent.services.memory_system import MemorySystem


class InteractionService:
    def __init__(
        self,
        npc_repo: NpcRepository,
        relation_repo: RelationRepository,
        runtime_repo: RuntimeStateRepository,
        memory_system: MemorySystem,
        event_repo: EventRepository,
        perception_service,
        dialogue_engine,
        options_provider,
    ):
        self.npc_repo = npc_repo
        self.relation_repo = relation_repo
        self.runtime_repo = runtime_repo
        self.memory_system = memory_system
        self.event_repo = event_repo
        self.perception_service = perception_service
        self.dialogue_engine = dialogue_engine
        self.options_provider = options_provider

    def get_dialogue_options(self, npc_id: str) -> dict[str, Any] | None:
        context = self.npc_repo.get_dialogue_context(npc_id)
        if context is None:
            return None
        return {
            "npc": {
                "id": context.npc_id,
                "name": context.name,
                "role": context.role,
                "personality": context.personality,
                "identity_profile": {
                    "age": context.identity_profile.age,
                    "occupation": context.identity_profile.occupation,
                    "base_location": context.identity_profile.base_location,
                    "personality_traits": context.identity_profile.personality_traits,
                    "long_term_goals": context.identity_profile.long_term_goals,
                    "daily_routine": context.identity_profile.daily_routine,
                    "social_relations": context.identity_profile.social_relations,
                    "behavior_constraints": context.identity_profile.behavior_constraints,
                },
                "current_location": context.current_location,
                "current_action": context.current_action,
                "mood": context.mood,
                "goal": context.goal,
                "relation_with_player": context.relation_with_player,
                "avatar": "placeholder",
            },
            "options": self.options_provider()[:4],
        }

    def apply_choice(self, npc_id: str, option_id: str, use_llm: bool) -> dict[str, Any] | None:
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

        now = datetime.now(timezone.utc).isoformat()
        self.relation_repo.update_relation(npc_id, result["new_relation"])
        self.runtime_repo.update_mood(npc_id, result["new_mood"], now)
        self.event_repo.append_event(
            event_type=result["trigger_event"],
            location=context.current_location,
            payload={
                "npc_id": npc_id,
                "option_id": option_id,
                "choice_text": result["choice_text"],
                "relation_delta": result["effects"]["relation_delta"],
                "new_relation": result["new_relation"],
                "new_mood": result["new_mood"],
            },
            created_at=now,
        )
        self.memory_system.remember_choice_outcome(
            npc_id=npc_id,
            choice_text=result["choice_text"],
            new_relation=result["new_relation"],
            new_mood=result["new_mood"],
            relation_delta=result["effects"]["relation_delta"],
        )

        return {
            "npc_id": npc_id,
            "reply": result["reply"],
            "effects": {
                "relation_delta": result["effects"]["relation_delta"],
                "new_relation": result["new_relation"],
                "new_mood": result["new_mood"],
                "write_memory": result["write_memory"],
            },
        }

    def free_talk(self, npc_id: str, message: str) -> dict[str, Any] | None:
        context = self.npc_repo.get_dialogue_context(npc_id)
        if context is None:
            return None
        memory_context = self.memory_system.build_context(npc_id, query=message, per_layer=1)
        memory_hint = self.memory_system.render_context_for_prompt(memory_context)
        recent_perceptions = self.perception_service.get_recent_perceptions(npc_id, 5)
        reply = self.dialogue_engine.generate_free_reply(
            npc_id=npc_id,
            npc_name=context.name,
            personality=context.personality,
            message=message,
            identity_profile=context.identity_profile,
            recent_memory=memory_hint,
            recent_perceptions=recent_perceptions,
        )
        self.memory_system.remember_dialogue(npc_id=npc_id, message=message)
        return {"npc_id": npc_id, "reply": reply}
