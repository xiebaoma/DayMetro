from __future__ import annotations

from server.npc_agent.domain.decision import DecisionContext, NpcIntent
from server.npc_agent.ports.decision import DecisionPolicyPort


class NoopDecisionPolicy:
    def decide(self, context: DecisionContext) -> NpcIntent | None:
        return None


class CompositeDecisionPolicy:
    def __init__(self, policies: list[DecisionPolicyPort]):
        self.policies = policies

    def decide(self, context: DecisionContext) -> NpcIntent | None:
        for policy in self.policies:
            intent = policy.decide(context)
            if intent is not None:
                return intent
        return None


class DecisionService:
    def __init__(self, policy: DecisionPolicyPort | None = None):
        self.policy = policy or NoopDecisionPolicy()

    def decide(self, context: DecisionContext) -> NpcIntent | None:
        return self.policy.decide(context)
