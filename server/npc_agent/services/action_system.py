from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActionSpec:
    name: str
    required: tuple[str, ...]
    optional: tuple[str, ...] = ()
    description: str = ""

    @property
    def allowed_fields(self) -> set[str]:
        return {"action", *self.required, *self.optional}


ALLOWED_ACTIONS: dict[str, ActionSpec] = {
    "say": ActionSpec("say", ("content",), description="NPC says visible dialogue text."),
    "move_to": ActionSpec("move_to", ("target",), description="NPC moves to a known scene target."),
    "look_at": ActionSpec("look_at", ("target",), description="NPC turns toward a target."),
    "give_item": ActionSpec(
        "give_item", ("item", "target"), description="NPC gives an existing item to a target."
    ),
    "take_item": ActionSpec("take_item", ("item",), description="NPC takes an existing item."),
    "start_task": ActionSpec("start_task", ("task",), description="NPC starts a known task."),
    "stop_task": ActionSpec("stop_task", ("task",), description="NPC stops a known task."),
    "update_relationship": ActionSpec(
        "update_relationship",
        ("target", "delta"),
        description="NPC relationship with a target changes by delta.",
    ),
    "remember": ActionSpec("remember", ("event",), description="NPC stores an event in memory."),
    "ask_question": ActionSpec(
        "ask_question", ("target", "question"), description="NPC asks a question to a target."
    ),
}


class ActionValidationError(ValueError):
    pass


def allowed_action_specs() -> list[dict[str, Any]]:
    return [
        {
            "action": spec.name,
            "required": list(spec.required),
            "optional": list(spec.optional),
            "description": spec.description,
        }
        for spec in ALLOWED_ACTIONS.values()
    ]


def action_catalog_for_prompt() -> str:
    lines = []
    for spec in ALLOWED_ACTIONS.values():
        fields = ", ".join(spec.required)
        lines.append(f"- {spec.name}({fields})")
    return "\n".join(lines)


def validate_action(action: dict[str, Any]) -> dict[str, Any]:
    action_name = action.get("action")
    if not isinstance(action_name, str) or not action_name:
        raise ActionValidationError("action must be a non-empty string")

    spec = ALLOWED_ACTIONS.get(action_name)
    if spec is None:
        raise ActionValidationError(f"unsupported action: {action_name}")

    missing = [field for field in spec.required if field not in action]
    if missing:
        raise ActionValidationError(f"{action_name} missing required fields: {', '.join(missing)}")

    extra = set(action.keys()) - spec.allowed_fields
    if extra:
        raise ActionValidationError(f"{action_name} has unsupported fields: {', '.join(sorted(extra))}")

    normalized = {"action": action_name}
    for field in (*spec.required, *spec.optional):
        if field in action:
            normalized[field] = action[field]
    return normalized


def validate_action_plan(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [validate_action(action) for action in actions]


def parse_action_plan_json(raw_text: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ActionValidationError("action plan is not valid JSON") from exc

    if isinstance(parsed, dict) and "actions" in parsed:
        parsed = parsed["actions"]
    if not isinstance(parsed, list):
        raise ActionValidationError("action plan must be a list or an object with actions")
    if not all(isinstance(item, dict) for item in parsed):
        raise ActionValidationError("each action must be an object")
    return validate_action_plan(parsed)


def say(content: str) -> dict[str, Any]:
    return validate_action({"action": "say", "content": content})


def remember(event: str) -> dict[str, Any]:
    return validate_action({"action": "remember", "event": event})


def update_relationship(target: str, delta: int) -> dict[str, Any]:
    return validate_action({"action": "update_relationship", "target": target, "delta": delta})
