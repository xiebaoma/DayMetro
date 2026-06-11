from __future__ import annotations

from typing import Any

from server.npc_agent.domain.actions import ActionResult
from server.npc_agent.domain.decision import NpcIntent
from server.npc_agent.ports.execution import ActionExecutorPort
from server.npc_agent.services.action_system import say, validate_action, validate_action_plan


class NoopActionExecutor:
    def execute(self, intent: NpcIntent, actions: list[dict[str, Any]]) -> ActionResult:
        return ActionResult(actions=actions, executed=False)


class ExecutionService:
    def __init__(self, executor: ActionExecutorPort | None = None):
        self.executor = executor or NoopActionExecutor()

    def execute_intent(self, intent: NpcIntent) -> ActionResult:
        actions = self._plan_actions(intent)
        return self.executor.execute(intent, actions)

    def _plan_actions(self, intent: NpcIntent) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = [
            validate_action({"action": "look_at", "target": intent.target}),
            say(intent.speech),
        ]
        question = intent.parameters.get("question")
        if question:
            actions.append(validate_action({"action": "ask_question", "target": intent.target, "question": question}))
        task = intent.parameters.get("task")
        if task:
            actions.append(validate_action({"action": "start_task", "task": task}))
        return validate_action_plan(actions)
