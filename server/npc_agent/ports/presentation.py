from __future__ import annotations

from typing import Any, Protocol


class DialoguePort(Protocol):
    def generate_free_reply(
        self,
        *,
        npc_id: str,
        npc_name: str,
        personality: str,
        message: str,
        identity_profile: Any,
        recent_memory: str,
        recent_perceptions: list[dict],
    ) -> dict[str, Any]: ...

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
        identity_profile: Any,
        option_id: str,
        game_time: str,
        recent_memory: str,
        recent_perceptions: list[dict],
        use_llm: bool = False,
    ) -> dict[str, Any]: ...


class DialogueOptionsProviderPort(Protocol):
    def __call__(self) -> list[dict[str, str]]: ...
