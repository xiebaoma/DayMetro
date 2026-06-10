from __future__ import annotations

from server.adapters.daymetro.time_points import KEY_TIME_POINTS, get_world_time_label
from server.npc_agent.domain.models import NpcState


def world_state_response(save_state: dict, npc_states: list[NpcState], player_state: dict) -> dict:
    game_time = save_state["game_time"]
    return {
        "game_time": game_time,
        "time_label": get_world_time_label(game_time),
        "time_points": KEY_TIME_POINTS,
        "current_location": save_state["current_location"],
        "player_state": player_state,
        "npcs": [
            {
                "id": npc.id,
                "name": npc.name,
                "role": npc.role,
                "personality": npc.personality,
                "identity_profile": {
                    "age": npc.identity_profile.age,
                    "occupation": npc.identity_profile.occupation,
                    "base_location": npc.identity_profile.base_location,
                    "personality_traits": npc.identity_profile.personality_traits,
                    "long_term_goals": npc.identity_profile.long_term_goals,
                    "daily_routine": npc.identity_profile.daily_routine,
                    "social_relations": npc.identity_profile.social_relations,
                    "behavior_constraints": npc.identity_profile.behavior_constraints,
                },
                "current_location": npc.current_location,
                "current_action": npc.current_action,
                "mood": npc.mood,
                "goal": npc.goal,
                "schedule": npc.schedule,
                "relation_with_player": npc.relation_with_player,
                "trust_with_player": npc.trust_with_player,
                "conflict_with_player": npc.conflict_with_player,
                "familiarity_with_player": npc.familiarity_with_player,
            }
            for npc in npc_states
        ],
    }


def dialogue_options_response(npc_context: dict, options: list[dict]) -> dict:
    return {"npc": npc_context, "options": options}
