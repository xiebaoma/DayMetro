from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional


def generate_short_reply(prompt: str) -> Optional[str]:
    # NPC Agent-level switch; default is disabled.
    if os.getenv("NPC_AGENT_LLM_ENABLED", "0") != "1":
        return None

    api_key = os.getenv("NPC_AGENT_DEEPSEEK_API_KEY")
    if not api_key:
        return None

    payload = {
        "model": os.getenv("NPC_AGENT_DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 80,
    }
    request = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    choices = body.get("choices", [])
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content", "")
    if not isinstance(content, str):
        return None
    stripped = content.strip()
    return stripped[:50] if stripped else None


def generate_action_plan(prompt: str) -> Optional[str]:
    # NPC Agent-level switch; default is disabled.
    if os.getenv("NPC_AGENT_LLM_ENABLED", "0") != "1":
        return None

    api_key = os.getenv("NPC_AGENT_DEEPSEEK_API_KEY")
    if not api_key:
        return None

    payload = {
        "model": os.getenv("NPC_AGENT_DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 260,
    }
    request = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    choices = body.get("choices", [])
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content", "")
    if not isinstance(content, str):
        return None
    stripped = content.strip()
    return stripped or None
