from __future__ import annotations

import pytest

from server.npc_agent.services.action_system import (
    ActionValidationError,
    parse_action_plan_json,
    validate_action,
)


def test_validate_action_allows_known_action_shape() -> None:
    action = validate_action({"action": "say", "content": "早啊，今天又去实习？"})

    assert action == {"action": "say", "content": "早啊，今天又去实习？"}


def test_validate_action_rejects_unknown_action() -> None:
    with pytest.raises(ActionValidationError):
        validate_action({"action": "teleport", "target": "公司"})


def test_validate_action_rejects_extra_fields() -> None:
    with pytest.raises(ActionValidationError):
        validate_action({"action": "say", "content": "早", "spell": "不存在的行为"})


def test_parse_action_plan_json_accepts_actions_object() -> None:
    actions = parse_action_plan_json(
        '{"actions":[{"action":"look_at","target":"player"},{"action":"ask_question","target":"player","question":"今天去实习吗？"}]}'
    )

    assert actions == [
        {"action": "look_at", "target": "player"},
        {"action": "ask_question", "target": "player", "question": "今天去实习吗？"},
    ]
