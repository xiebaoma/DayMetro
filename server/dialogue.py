from __future__ import annotations

from typing import Any

from server.adapters.content.json_dialogue_rules import generate_template_reply
from server.adapters.daymetro.dialogue_effects import (
    effects_by_option,
    get_dialogue_options,
    rule_based_reply,
)
from server.adapters.llm.deepseek_client import generate_short_reply


class DayMetroDialogueEngine:
    def generate_free_reply(
        self,
        *,
        npc_id: str,
        npc_name: str,
        personality: str,
        message: str,
        identity_profile,
        recent_memory: str,
        recent_perceptions: list[dict],
    ) -> str:
        memory_hint = f" 我还记得你之前说过：{recent_memory}" if recent_memory else ""
        perception_hint = ""
        if recent_perceptions:
            perception_hint = f" 我最近注意到：{recent_perceptions[0].get('perceived_fact', '')}"
        return (
            generate_template_reply(npc_name, personality, message)
            + f"（{identity_profile.occupation}）"
            + memory_hint
            + perception_hint
        )

    def apply_choice(
        self,
        *,
        npc_id: str,
        npc_name: str,
        personality: str,
        current_location: str,
        current_action: str,
        mood: str,
        goal: str,
        relation_with_player: int,
        identity_profile,
        option_id: str,
        game_time: str,
        recent_memory: str,
        recent_perceptions: list[dict],
        use_llm: bool = False,
    ) -> dict[str, Any]:
        boundary_block = _check_behavior_boundary(identity_profile.behavior_constraints, option_id)
        if boundary_block:
            return {
                "reply": f"{npc_name}：{boundary_block}",
                "effects": {
                    "choice_text": "触发行为边界",
                    "relation_delta": 0,
                    "mood_override": mood,
                    "write_memory": False,
                    "trigger_event": "dialogue_boundary_block",
                },
                "new_relation": relation_with_player,
                "new_mood": mood,
                "write_memory": False,
                "trigger_event": "dialogue_boundary_block",
                "choice_text": "触发行为边界",
            }

        effects = effects_by_option(option_id, current_location)
        new_relation = relation_with_player + effects["relation_delta"]
        new_mood = effects["mood_override"] or mood

        reply = None
        if use_llm:
            prompt = (
                "你是DayMetro中的NPC，请根据状态给出不超过50字的口语化回复，不要改变系统状态。\n"
                f"NPC:{npc_name} 性格:{personality} 地点:{current_location} "
                f"时间:{game_time} 心情:{new_mood} 目标:{goal} 关系:{new_relation} "
                f"玩家选择:{effects['choice_text']} 相关记忆:{recent_memory or '无'} "
                f"身份:{identity_profile.occupation} 长期目标:{','.join(identity_profile.long_term_goals[:2])} "
                f"最近感知:{recent_perceptions[0].get('perceived_fact', '无') if recent_perceptions else '无'}"
            )
            reply = generate_short_reply(prompt)

        if not reply:
            reply = rule_based_reply(
                npc_name=npc_name,
                option_id=option_id,
                mood=new_mood,
                relation_with_player=new_relation,
                current_action=current_action,
                goal=goal,
                memory_hint=recent_memory,
            )
        return {
            "reply": reply,
            "effects": effects,
            "new_relation": new_relation,
            "new_mood": new_mood,
            "write_memory": effects["write_memory"],
            "trigger_event": effects["trigger_event"],
            "choice_text": effects["choice_text"],
        }


def _check_behavior_boundary(constraints: list[str], option_id: str) -> str | None:
    if option_id == "invite_lunch":
        for item in constraints:
            if "工作时不离岗" in item or "不在工作时间外出" in item:
                return "我有自己的原则，工作时不会离开岗位。"
    if option_id == "complain_meeting":
        for item in constraints:
            if "不公开抱怨团队" in item:
                return "我不会公开抱怨团队，这是底线。"
    return None
