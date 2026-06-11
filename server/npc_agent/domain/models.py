from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from server.npc_agent.domain.actions import ActionPlan, ActionResult
from server.npc_agent.domain.cognition import BeliefState, EmotionState, GoalState
from server.npc_agent.domain.decision import DecisionContext, NpcIntent
from server.npc_agent.domain.events import PerceivedFact, WorldEvent
from server.npc_agent.domain.memory import EventMemoryMapping, MemoryContext, MemoryRecord


@dataclass
class NpcIdentityProfile:
    age: int
    occupation: str
    base_location: str
    personality_traits: dict[str, str]
    long_term_goals: list[str]
    daily_routine: list[str]
    social_relations: list[dict[str, str]]
    behavior_constraints: list[str]


@dataclass
class NpcProfile:
    npc_id: str
    name: str
    role: str
    personality: str
    initial_location: str


@dataclass
class NpcRuntimeState:
    npc_id: str
    current_location: str
    current_action: str
    mood: str
    goal: str


@dataclass
class PlayerRelationProfile:
    relation_value: int
    trust_value: int
    conflict_value: int
    familiarity_value: int


@dataclass
class NpcState:
    id: str
    name: str
    role: str
    personality: str
    current_location: str
    current_action: str
    mood: str
    goal: str
    identity_profile: NpcIdentityProfile
    schedule: list[dict[str, Any]]
    relation_with_player: int
    trust_with_player: int
    conflict_with_player: int
    familiarity_with_player: int


@dataclass
class DialogueNpcContext:
    npc_id: str
    name: str
    role: str
    personality: str
    current_location: str
    current_action: str
    mood: str
    goal: str
    identity_profile: NpcIdentityProfile
    relation_with_player: int
    trust_with_player: int
    conflict_with_player: int
    familiarity_with_player: int
    game_time: str


__all__ = [
    "ActionPlan",
    "ActionResult",
    "BeliefState",
    "DialogueNpcContext",
    "EmotionState",
    "EventMemoryMapping",
    "GoalState",
    "MemoryContext",
    "MemoryRecord",
    "NpcIdentityProfile",
    "NpcIntent",
    "NpcProfile",
    "NpcRuntimeState",
    "NpcState",
    "PerceivedFact",
    "PlayerRelationProfile",
    "DecisionContext",
    "WorldEvent",
]
