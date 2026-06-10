from __future__ import annotations

import os

import pytest

from server.adapters.llm.deepseek_client import generate_action_plan
from server.npc_agent.services.action_system import parse_action_plan_json


def test_deepseek_action_plan_integration() -> None:
    if os.getenv("RUN_DEEPSEEK_INTEGRATION") != "1":
        pytest.skip("Set RUN_DEEPSEEK_INTEGRATION=1 to call the real DeepSeek API.")
    if not os.getenv("NPC_AGENT_DEEPSEEK_API_KEY"):
        pytest.skip("Set NPC_AGENT_DEEPSEEK_API_KEY to call the real DeepSeek API.")

    prompt = """
你是DayMetro中的NPC。只能输出JSON，不要输出解释。
输出格式必须是一个数组，每个元素都是一个动作对象。
只能使用这些动作：
- say(content)
- remember(event)
- update_relationship(target, delta)

场景：早上7点，宿舍。
NPC：室友A，外向，爱打游戏，嘴硬心软。
玩家刚走近你。
请输出一个动作计划，至少包含一个say动作。
示例：[{"action":"say","content":"早啊，今天又去实习？"}]
"""
    raw_plan = generate_action_plan(prompt)

    assert raw_plan is not None
    actions = parse_action_plan_json(raw_plan)
    assert any(action["action"] == "say" for action in actions)
