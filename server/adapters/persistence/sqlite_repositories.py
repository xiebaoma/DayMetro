from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from server.npc_agent.domain.models import (
    DialogueNpcContext,
    MemoryRecord,
    NpcIdentityProfile,
    NpcRuntimeState,
)


def _parse_identity_profile(row: sqlite3.Row) -> NpcIdentityProfile:
    return NpcIdentityProfile(
        age=int(row["age"] or 20),
        occupation=row["occupation"] or "",
        base_location=row["base_location"] or row["initial_location"] or "",
        personality_traits=json.loads(row["personality_traits"] or "{}"),
        long_term_goals=json.loads(row["long_term_goals"] or "[]"),
        daily_routine=json.loads(row["daily_routine"] or "[]"),
        social_relations=json.loads(row["social_relations"] or "[]"),
        behavior_constraints=json.loads(row["behavior_constraints"] or "[]"),
    )


class SqliteNpcRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_profiles_with_relation(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT n.npc_id, n.name, n.role, n.personality, n.initial_location,
                   n.age, n.occupation, n.base_location, n.personality_traits,
                   n.long_term_goals, n.daily_routine, n.social_relations, n.behavior_constraints,
                   pr.relation_value
            FROM npc n
            LEFT JOIN player_relation pr ON pr.npc_id = n.npc_id
            ORDER BY n.id ASC
            """
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["identity_profile"] = _parse_identity_profile(row)
            result.append(item)
        return result

    def get_dialogue_context(self, npc_id: str) -> DialogueNpcContext | None:
        row = self.conn.execute(
            """
            SELECT n.npc_id, n.name, n.role, n.personality, n.initial_location,
                   n.age, n.occupation, n.base_location, n.personality_traits,
                   n.long_term_goals, n.daily_routine, n.social_relations, n.behavior_constraints,
                   rs.current_location, rs.current_action, rs.mood, rs.goal,
                   pr.relation_value, ss.game_time
            FROM npc n
            LEFT JOIN npc_runtime_state rs ON rs.npc_id = n.npc_id
            LEFT JOIN player_relation pr ON pr.npc_id = n.npc_id
            LEFT JOIN save_state ss ON ss.id = 1
            WHERE n.npc_id = ?
            """,
            (npc_id,),
        ).fetchone()
        if not row:
            return None
        return DialogueNpcContext(
            npc_id=row["npc_id"],
            name=row["name"],
            role=row["role"],
            personality=row["personality"],
            current_location=row["current_location"] or "未知地点",
            current_action=row["current_action"] or "日常活动",
            mood=row["mood"] or "neutral",
            goal=row["goal"] or "推进计划",
            identity_profile=_parse_identity_profile(row),
            relation_with_player=int(row["relation_value"] or 0),
            game_time=row["game_time"] or "07:00",
        )


class SqliteRuntimeStateRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_runtime_state(self, npc_id: str) -> NpcRuntimeState | None:
        row = self.conn.execute(
            """
            SELECT npc_id, current_location, current_action, mood, goal
            FROM npc_runtime_state
            WHERE npc_id = ?
            """,
            (npc_id,),
        ).fetchone()
        if not row:
            return None
        return NpcRuntimeState(
            npc_id=row["npc_id"],
            current_location=row["current_location"],
            current_action=row["current_action"],
            mood=row["mood"],
            goal=row["goal"],
        )

    def upsert_runtime_state(self, state: NpcRuntimeState, updated_at: str) -> None:
        existing = self.get_runtime_state(state.npc_id)
        if existing is None:
            self.conn.execute(
                """
                INSERT INTO npc_runtime_state
                (npc_id, current_location, current_action, mood, goal, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    state.npc_id,
                    state.current_location,
                    state.current_action,
                    state.mood,
                    state.goal,
                    updated_at,
                ),
            )
            return

        self.conn.execute(
            """
            UPDATE npc_runtime_state
            SET current_location = ?, current_action = ?, mood = ?, goal = ?, updated_at = ?
            WHERE npc_id = ?
            """,
            (
                state.current_location,
                state.current_action,
                state.mood,
                state.goal,
                updated_at,
                state.npc_id,
            ),
        )

    def update_mood(self, npc_id: str, mood: str, updated_at: str) -> None:
        self.conn.execute(
            """
            UPDATE npc_runtime_state
            SET mood = ?, updated_at = ?
            WHERE npc_id = ?
            """,
            (mood, updated_at, npc_id),
        )


class SqliteRelationRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_relation(self, npc_id: str) -> int:
        row = self.conn.execute(
            """
            SELECT relation_value
            FROM player_relation
            WHERE npc_id = ?
            """,
            (npc_id,),
        ).fetchone()
        return int(row["relation_value"] if row else 0)

    def update_relation(self, npc_id: str, value: int) -> None:
        self.conn.execute(
            """
            UPDATE player_relation
            SET relation_value = ?
            WHERE npc_id = ?
            """,
            (value, npc_id),
        )


class SqliteSaveStateRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_save_state(self) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT game_time, current_location, player_state
            FROM save_state
            WHERE id = 1
            """
        ).fetchone()
        return dict(row) if row else None

    def update_save_state(self, game_time: str, location: str, updated_at: str) -> None:
        self.conn.execute(
            """
            UPDATE save_state
            SET game_time = ?, current_location = ?, updated_at = ?
            WHERE id = 1
            """,
            (game_time, location, updated_at),
        )


class SqliteMemoryRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add_memory(self, npc_id: str, content: str, importance: int, created_at: str) -> None:
        self.add_memory_entry(
            npc_id=npc_id,
            layer="episodic",
            content=content,
            importance=importance,
            created_at=created_at,
            source_type="legacy",
            tags=[],
            related_entity="",
            metadata={},
        )

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
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO npc_memory
            (npc_id, layer, content, importance, source_type, tags, related_entity, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                npc_id,
                layer,
                content,
                importance,
                source_type,
                json.dumps(tags, ensure_ascii=False),
                related_entity,
                json.dumps(metadata, ensure_ascii=False),
                created_at,
            ),
        )

    def get_recent_memories(self, npc_id: str, limit: int, layer: str | None = None) -> list[str]:
        rows = self.list_recent_memory_entries(npc_id=npc_id, limit=limit, layer=layer)
        return [row.content for row in rows]

    def list_recent_memory_entries(
        self, npc_id: str, limit: int, layer: str | None = None
    ) -> list[MemoryRecord]:
        if layer:
            rows = self.conn.execute(
                """
                SELECT id, npc_id, layer, content, importance, source_type, tags, related_entity, metadata, created_at
                FROM npc_memory
                WHERE npc_id = ? AND layer = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (npc_id, layer, limit),
            ).fetchall()
            return [self._to_memory_record(row) for row in rows]

        rows = self.conn.execute(
            """
            SELECT id, npc_id, layer, content, importance, source_type, tags, related_entity, metadata, created_at
            FROM npc_memory
            WHERE npc_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (npc_id, limit),
        ).fetchall()
        return [self._to_memory_record(row) for row in rows]

    def search_memory_entries(
        self, npc_id: str, query: str, limit: int, layers: list[str] | None = None
    ) -> list[MemoryRecord]:
        candidates = self._fetch_search_candidates(npc_id=npc_id, layers=layers, limit=max(limit * 8, 24))
        if not query.strip():
            return candidates[:limit]
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return candidates[:limit]

        scored: list[tuple[float, MemoryRecord]] = []
        for item in candidates:
            item_tokens = self._tokenize(f"{item.content} {' '.join(item.tags)} {item.related_entity}")
            overlap = len(item_tokens.intersection(query_tokens))
            if overlap == 0:
                continue
            score = overlap * 1.5 + item.importance * 0.35
            scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def _fetch_search_candidates(
        self, npc_id: str, layers: list[str] | None, limit: int
    ) -> list[MemoryRecord]:
        if layers:
            placeholders = ",".join("?" for _ in layers)
            sql = f"""
                SELECT id, npc_id, layer, content, importance, source_type, tags, related_entity, metadata, created_at
                FROM npc_memory
                WHERE npc_id = ? AND layer IN ({placeholders})
                ORDER BY importance DESC, id DESC
                LIMIT ?
            """
            params: tuple[Any, ...] = (npc_id, *layers, limit)
            rows = self.conn.execute(sql, params).fetchall()
            return [self._to_memory_record(row) for row in rows]

        rows = self.conn.execute(
            """
            SELECT id, npc_id, layer, content, importance, source_type, tags, related_entity, metadata, created_at
            FROM npc_memory
            WHERE npc_id = ?
            ORDER BY importance DESC, id DESC
            LIMIT ?
            """,
            (npc_id, limit),
        ).fetchall()
        return [self._to_memory_record(row) for row in rows]

    def _to_memory_record(self, row: sqlite3.Row) -> MemoryRecord:
        tags_raw = row["tags"] or "[]"
        metadata_raw = row["metadata"] or "{}"
        return MemoryRecord(
            id=int(row["id"]),
            npc_id=row["npc_id"],
            layer=row["layer"] or "episodic",
            content=row["content"],
            importance=int(row["importance"] or 1),
            created_at=row["created_at"],
            source_type=row["source_type"] or "system",
            tags=json.loads(tags_raw),
            related_entity=row["related_entity"] or "",
            metadata=json.loads(metadata_raw),
        )

    def _tokenize(self, text: str) -> set[str]:
        return {item.lower() for item in re.findall(r"[\w\u4e00-\u9fff]+", text) if len(item) > 1}


class SqliteEventRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def append_event(self, event_type: str, location: str, payload: dict[str, Any], created_at: str) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO event_log (event_type, location, payload, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (event_type, location, json.dumps(payload, ensure_ascii=False), created_at),
        )
        return int(cursor.lastrowid)

    def list_recent(self, limit: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id, event_type, location, payload, created_at
            FROM event_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "location": row["location"],
                    "payload": json.loads(row["payload"]) if row["payload"] else {},
                    "created_at": row["created_at"],
                }
            )
        return result


class SqlitePerceptionRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add_perception(
        self,
        npc_id: str,
        event_id: int | None,
        source_type: str,
        perceived_fact: str,
        confidence: float,
        observed_at: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO npc_perception
            (npc_id, event_id, source_type, perceived_fact, confidence, observed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (npc_id, event_id, source_type, perceived_fact, confidence, observed_at),
        )

    def list_recent_perceptions(self, npc_id: str, limit: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id, npc_id, event_id, source_type, perceived_fact, confidence, observed_at
            FROM npc_perception
            WHERE npc_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (npc_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
