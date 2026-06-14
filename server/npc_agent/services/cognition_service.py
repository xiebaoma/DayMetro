from __future__ import annotations

from server.npc_agent.domain.cognition import BeliefState, EmotionState, GoalState
from server.npc_agent.domain.memory import MemoryContext
from server.npc_agent.ports.cognition import CognitionPolicyPort


class RuleBasedCognitionPolicy:
    def build_belief(
        self,
        *,
        npc,
        memory_context: MemoryContext,
        perceptions: list[dict],
        player_state: dict[str, int],
    ) -> BeliefState:
        memory_highlights = _memory_highlights(memory_context)
        facts = [str(item.get("perceived_fact", "")) for item in perceptions[:3] if item.get("perceived_fact")]
        relationship_signal = _relationship_signal(npc.relation_with_player, npc.conflict_with_player)
        player_state_signal = _player_state_signal(player_state)
        emotion = _emotion_state(npc.mood, player_state_signal, memory_highlights)
        goal = _goal_state(npc.goal, npc.role, player_state_signal, relationship_signal)
        return BeliefState(
            npc_id=npc.id,
            emotion=emotion,
            goal=goal,
            relationship_signal=relationship_signal,
            player_state_signal=player_state_signal,
            facts=facts,
            memory_highlights=memory_highlights,
            metadata={
                "role": npc.role,
                "location": npc.current_location,
                "relation": npc.relation_with_player,
                "conflict": npc.conflict_with_player,
            },
        )


class CognitionService:
    def __init__(self, policy: CognitionPolicyPort | None = None):
        self.policy = policy or RuleBasedCognitionPolicy()

    def build_belief(
        self,
        *,
        npc,
        memory_context: MemoryContext,
        perceptions: list[dict],
        player_state: dict[str, int],
    ) -> BeliefState:
        return self.policy.build_belief(
            npc=npc,
            memory_context=memory_context,
            perceptions=perceptions,
            player_state=player_state,
        )


def _memory_highlights(context: MemoryContext) -> list[str]:
    records = [*context.relationship, *context.reflection, *context.episodic, *context.semantic]
    records.sort(key=lambda item: (item.importance, item.id), reverse=True)
    return [item.content for item in records[:3]]


def _relationship_signal(relation: int, conflict: int) -> str:
    if conflict >= 5:
        return "tense"
    if relation >= 12:
        return "close"
    if relation >= 5:
        return "friendly"
    return "distant"


def _player_state_signal(player_state: dict[str, int]) -> str:
    if player_state.get("stress", 0) >= 60:
        return "stressed"
    if player_state.get("energy", 100) <= 45 or player_state.get("sleep_quality", 100) <= 55:
        return "tired"
    if player_state.get("mood", 70) >= 80:
        return "positive"
    return "stable"


def _emotion_state(base_mood: str, player_signal: str, memory_highlights: list[str]) -> EmotionState:
    reasons: list[str] = []
    mood = base_mood
    intensity = 3
    if player_signal in {"stressed", "tired"}:
        mood = "concerned"
        intensity = 6
        reasons.append(f"player:{player_signal}")
    if any("冲突" in item or "没有兑现" in item for item in memory_highlights):
        mood = "guarded"
        intensity = max(intensity, 7)
        reasons.append("memory:conflict")
    return EmotionState(mood=mood, intensity=intensity, reasons=reasons)


def _goal_state(base_goal: str, role: str, player_signal: str, relation_signal: str) -> GoalState:
    if player_signal in {"stressed", "tired"} and relation_signal in {"close", "friendly"}:
        return GoalState(current_goal="关心玩家当前状态", priority=7, reasons=[player_signal, relation_signal])
    if role == "mentor":
        return GoalState(current_goal="推动玩家整理工作目标", priority=6, reasons=[role])
    return GoalState(current_goal=base_goal, priority=4, reasons=["routine"])
