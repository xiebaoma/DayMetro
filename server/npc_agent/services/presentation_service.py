from __future__ import annotations

from typing import Any


class PresentationService:
    def dialogue_options(self, context, options: list[dict[str, str]]) -> dict[str, Any]:
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
                "trust_with_player": context.trust_with_player,
                "conflict_with_player": context.conflict_with_player,
                "familiarity_with_player": context.familiarity_with_player,
                "avatar": "placeholder",
            },
            "options": options[:4],
        }

    def dialogue_choice_result(self, npc_id: str, result: dict[str, Any], relation_profile) -> dict[str, Any]:
        return {
            "npc_id": npc_id,
            "reply": result["reply"],
            "actions": result["actions"],
            "effects": {
                "relation_delta": result["effects"]["relation_delta"],
                "new_relation": relation_profile.relation_value,
                "new_trust": relation_profile.trust_value,
                "new_conflict": relation_profile.conflict_value,
                "new_familiarity": relation_profile.familiarity_value,
                "new_mood": result["new_mood"],
                "write_memory": result["write_memory"],
            },
        }

    def free_talk_result(self, npc_id: str, result: dict[str, Any]) -> dict[str, Any]:
        return {"npc_id": npc_id, "reply": result["reply"], "actions": result["actions"]}
