from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


def _resolve_data_dir() -> Path:
    return Path(os.getenv("DAYMETRO_DATA_DIR", str(DEFAULT_DATA_DIR)))


def generate_template_reply(npc_name: str, personality: str, message: str) -> str:
    rules_path = _resolve_data_dir() / "dialogue_rules.json"
    with rules_path.open("r", encoding="utf-8") as file:
        rules = json.load(file)
    templates = rules.get(personality) or rules["default"]
    return templates["reply"].format(name=npc_name, message=message)
