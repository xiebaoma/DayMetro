from __future__ import annotations

from typing import Any, Protocol

from server.npc_agent.domain.models import (
    DialogueNpcContext,
    MemoryRecord,
    NpcProfile,
    NpcRuntimeState,
    PlayerRelationProfile,
)


class NpcRepository(Protocol):
    def list_profiles_with_relation(self) -> list[dict[str, Any]]: ...

    def get_dialogue_context(self, npc_id: str) -> DialogueNpcContext | None: ...


class RuntimeStateRepository(Protocol):
    def get_runtime_state(self, npc_id: str) -> NpcRuntimeState | None: ...

    def upsert_runtime_state(self, state: NpcRuntimeState, updated_at: str) -> None: ...

    def update_mood(self, npc_id: str, mood: str, updated_at: str) -> None: ...


class RelationRepository(Protocol):
    def get_relation(self, npc_id: str) -> int: ...

    def get_profile(self, npc_id: str) -> PlayerRelationProfile: ...

    def update_relation(self, npc_id: str, value: int) -> None: ...

    def apply_delta(
        self,
        npc_id: str,
        *,
        relation_delta: int = 0,
        trust_delta: int = 0,
        conflict_delta: int = 0,
        familiarity_delta: int = 0,
    ) -> PlayerRelationProfile: ...


class SaveStateRepository(Protocol):
    def get_save_state(self) -> dict[str, Any] | None: ...

    def update_save_state(self, game_time: str, location: str, updated_at: str) -> None: ...

    def update_player_state(self, player_state: dict[str, Any], updated_at: str) -> None: ...


class DailyReviewRepository(Protocol):
    def add_review(
        self,
        *,
        review_date: str,
        route: list[str],
        important_events: list[dict[str, Any]],
        npc_interactions: list[dict[str, Any]],
        relation_changes: list[dict[str, Any]],
        state_snapshot: dict[str, Any],
        keywords: list[str],
        summary: str,
        tomorrow_hint: str,
        created_at: str,
    ) -> int: ...

    def latest_review(self) -> dict[str, Any] | None: ...


class MemoryRepository(Protocol):
    def add_memory(self, npc_id: str, content: str, importance: int, created_at: str) -> None: ...

    def add_memory_entry(
        self,
        npc_id: str,
        layer: str,
        content: str,
        importance: int,
        created_at: str,
        source_type: str,
        tags: list[str],
        related_entity: str,
        metadata: dict[str, Any],
        memory_type: str = "日常聊天",
        related_event_id: int | None = None,
    ) -> None: ...

    def get_recent_memories(self, npc_id: str, limit: int, layer: str | None = None) -> list[str]: ...

    def list_recent_memory_entries(
        self, npc_id: str, limit: int, layer: str | None = None
    ) -> list[MemoryRecord]: ...

    def search_memory_entries(
        self, npc_id: str, query: str, limit: int, layers: list[str] | None = None
    ) -> list[MemoryRecord]: ...


class EventRepository(Protocol):
    def append_event(self, event_type: str, location: str, payload: dict[str, Any], created_at: str) -> int: ...

    def list_recent(self, limit: int) -> list[dict[str, Any]]: ...


class PerceptionRepository(Protocol):
    def add_perception(
        self,
        npc_id: str,
        event_id: int | None,
        source_type: str,
        perceived_fact: str,
        confidence: float,
        observed_at: str,
    ) -> None: ...

    def list_recent_perceptions(self, npc_id: str, limit: int) -> list[dict[str, Any]]: ...
