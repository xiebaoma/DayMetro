from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from server.npc_agent.domain.models import MemoryContext, MemoryRecord
from server.npc_agent.ports.repositories import MemoryRepository

WORKING_LAYER = "working"
EPISODIC_LAYER = "episodic"
SEMANTIC_LAYER = "semantic"
RELATIONSHIP_LAYER = "relationship"
REFLECTION_LAYER = "reflection"


def _tokenize(text: str) -> set[str]:
    return {item.lower() for item in re.findall(r"[\w\u4e00-\u9fff]+", text) if len(item) > 1}


def _to_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LayeredMemory:
    repo: MemoryRepository
    layer: str

    def add(
        self,
        npc_id: str,
        content: str,
        *,
        importance: int = 1,
        source_type: str = "system",
        tags: list[str] | None = None,
        related_entity: str = "",
        memory_type: str = "日常聊天",
        related_event_id: int | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.repo.add_memory_entry(
            npc_id=npc_id,
            layer=self.layer,
            content=content,
            importance=importance,
            created_at=_to_now(),
            source_type=source_type,
            tags=tags or [],
            related_entity=related_entity,
            memory_type=memory_type,
            related_event_id=related_event_id,
            metadata=metadata or {},
        )

    def recent(self, npc_id: str, limit: int = 3) -> list[MemoryRecord]:
        return self.repo.list_recent_memory_entries(npc_id=npc_id, limit=limit, layer=self.layer)

    def search(self, npc_id: str, query: str, limit: int = 3) -> list[MemoryRecord]:
        return self.repo.search_memory_entries(
            npc_id=npc_id, query=query, limit=limit, layers=[self.layer]
        )


class MemorySystem:
    def __init__(self, memory_repo: MemoryRepository):
        self.memory_repo = memory_repo
        self.working = LayeredMemory(memory_repo, WORKING_LAYER)
        self.episodic = LayeredMemory(memory_repo, EPISODIC_LAYER)
        self.semantic = LayeredMemory(memory_repo, SEMANTIC_LAYER)
        self.relationship = LayeredMemory(memory_repo, RELATIONSHIP_LAYER)
        self.reflection = LayeredMemory(memory_repo, REFLECTION_LAYER)

    def remember_dialogue(self, npc_id: str, message: str, related_event_id: int | None = None) -> None:
        tags = list(_tokenize(message))[:6]
        self.working.add(
            npc_id,
            f"玩家刚说：{message}",
            importance=1,
            source_type="dialogue",
            tags=tags,
            related_entity="player",
            memory_type="日常聊天",
            related_event_id=related_event_id,
        )
        self.episodic.add(
            npc_id,
            f"对话事件：玩家提到“{message}”",
            importance=2,
            source_type="dialogue",
            tags=tags,
            related_entity="player",
            memory_type="日常聊天",
            related_event_id=related_event_id,
        )
        self._update_semantic_from_dialogue(npc_id, message, tags)
        self._update_relationship_from_dialogue(npc_id, message, tags)
        self.reflect_if_needed(npc_id)

    def remember_choice_outcome(
        self,
        npc_id: str,
        *,
        choice_text: str,
        new_relation: int,
        new_mood: str,
        relation_delta: int,
        related_event_id: int | None = None,
    ) -> None:
        tags = list(_tokenize(choice_text))[:6]
        self.working.add(
            npc_id,
            f"最近互动：玩家选择“{choice_text}”，当前好感 {new_relation}。",
            importance=1,
            source_type="choice",
            tags=tags,
            related_entity="player",
            memory_type="日常聊天",
            related_event_id=related_event_id,
        )
        self.episodic.add(
            npc_id,
            f"事件记录：玩家选择“{choice_text}”，关系变化 {relation_delta:+d}，心情变为 {new_mood}。",
            importance=2,
            source_type="choice",
            tags=tags,
            related_entity="player",
            memory_type=_memory_type_for_choice(choice_text),
            related_event_id=related_event_id,
        )
        self.relationship.add(
            npc_id,
            f"我和玩家当前关系值约为 {new_relation}，最近一次变化 {relation_delta:+d}。",
            importance=2,
            source_type="relation",
            tags=["relation", *tags[:3]],
            related_entity="player",
            memory_type="关系变化",
            related_event_id=related_event_id,
        )
        self.reflect_if_needed(npc_id)

    def remember_event(
        self,
        npc_id: str,
        *,
        content: str,
        memory_type: str,
        importance: int,
        related_event_id: int,
        tags: list[str] | None = None,
        source_type: str = "event",
        related_entity: str = "player",
        metadata: dict | None = None,
    ) -> None:
        self.episodic.add(
            npc_id,
            content,
            importance=importance,
            source_type=source_type,
            tags=tags or list(_tokenize(content))[:6],
            related_entity=related_entity,
            memory_type=memory_type,
            related_event_id=related_event_id,
            metadata=metadata,
        )
        if memory_type in {"承诺", "帮助", "冲突", "任务进展"}:
            self.relationship.add(
                npc_id,
                f"关系线索：{content}",
                importance=max(1, importance - 1),
                source_type=source_type,
                tags=["relationship", memory_type],
                related_entity=related_entity,
                memory_type=memory_type,
                related_event_id=related_event_id,
                metadata=metadata,
            )
        self.reflect_if_needed(npc_id)

    def build_context(self, npc_id: str, query: str, per_layer: int = 2) -> MemoryContext:
        return MemoryContext(
            working=self._fallback(self.working.search(npc_id, query, per_layer), self.working, npc_id, per_layer),
            episodic=self._fallback(
                self.episodic.search(npc_id, query, per_layer), self.episodic, npc_id, per_layer
            ),
            semantic=self._fallback(
                self.semantic.search(npc_id, query, per_layer), self.semantic, npc_id, per_layer
            ),
            relationship=self._fallback(
                self.relationship.search(npc_id, query, per_layer),
                self.relationship,
                npc_id,
                per_layer,
            ),
            reflection=self._fallback(
                self.reflection.search(npc_id, query, per_layer), self.reflection, npc_id, per_layer
            ),
        )

    def render_context_for_prompt(self, context: MemoryContext) -> str:
        lines: list[str] = []
        lines.extend(self._to_lines("短期记忆", context.working))
        lines.extend(self._to_lines("情景记忆", context.episodic))
        lines.extend(self._to_lines("长期画像", context.semantic))
        lines.extend(self._to_lines("关系记忆", context.relationship))
        lines.extend(self._to_lines("反思总结", context.reflection))
        return "；".join(lines[:8])

    def get_recent_memories(self, npc_id: str, limit: int = 3) -> list[str]:
        context = self.build_context(npc_id, query="", per_layer=max(1, limit))
        merged: list[str] = []
        for item in [
            *context.working,
            *context.episodic,
            *context.relationship,
            *context.semantic,
            *context.reflection,
        ]:
            merged.append(item.content)
            if len(merged) >= limit:
                break
        return merged

    def reflect_if_needed(self, npc_id: str) -> None:
        episodic_items = self.episodic.recent(npc_id, 6)
        if len(episodic_items) < 4:
            return
        latest_reflection = self.reflection.recent(npc_id, 1)
        recent_snippets = [item.content for item in episodic_items[:3]]
        summary = f"阶段反思：最近互动集中在 {' / '.join(recent_snippets)}。"
        if latest_reflection and latest_reflection[0].content == summary:
            return
        self.reflection.add(
            npc_id,
            summary,
            importance=3,
            source_type="reflection",
            tags=["reflection"],
            related_entity="player",
        )

    def _fallback(
        self, candidates: list[MemoryRecord], memory_layer: LayeredMemory, npc_id: str, limit: int
    ) -> list[MemoryRecord]:
        if candidates:
            return candidates
        return memory_layer.recent(npc_id, limit)

    def _to_lines(self, title: str, entries: Iterable[MemoryRecord]) -> list[str]:
        return [f"{title}:{item.content}" for item in entries]

    def _update_semantic_from_dialogue(self, npc_id: str, message: str, tags: list[str]) -> None:
        if not any(word in message for word in ("经常", "总是", "每天", "通常", "喜欢", "不喜欢", "工作日", "周末")):
            return
        self.semantic.add(
            npc_id,
            f"稳定认知：{message}",
            importance=3,
            source_type="summary",
            tags=["profile", *tags[:4]],
            related_entity="player",
            memory_type="玩家状态",
        )

    def _update_relationship_from_dialogue(self, npc_id: str, message: str, tags: list[str]) -> None:
        if not any(word in message for word in ("室友", "同事", "导师", "主管", "朋友", "关系")):
            return
        self.relationship.add(
            npc_id,
            f"关系观察：{message}",
            importance=2,
            source_type="dialogue_relation",
            tags=["relationship", *tags[:4]],
            related_entity="player",
            memory_type="关系变化",
        )


def _memory_type_for_choice(choice_text: str) -> str:
    if "邀请" in choice_text:
        return "共同经历"
    if "关心" in choice_text:
        return "帮助"
    if "吐槽" in choice_text:
        return "冲突"
    return "日常聊天"
