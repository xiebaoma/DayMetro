from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "save.db"
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _resolve_db_path() -> Path:
    return Path(os.getenv("DAYMETRO_DB_PATH", str(DEFAULT_DB_PATH)))


def _resolve_data_dir() -> Path:
    return Path(os.getenv("DAYMETRO_DATA_DIR", str(DEFAULT_DATA_DIR)))


def get_connection() -> sqlite3.Connection:
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS npc (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'unknown',
                personality TEXT NOT NULL,
                initial_location TEXT NOT NULL,
                age INTEGER NOT NULL DEFAULT 20,
                occupation TEXT NOT NULL DEFAULT '',
                base_location TEXT NOT NULL DEFAULT '',
                personality_traits TEXT NOT NULL DEFAULT '{}',
                long_term_goals TEXT NOT NULL DEFAULT '[]',
                daily_routine TEXT NOT NULL DEFAULT '[]',
                social_relations TEXT NOT NULL DEFAULT '[]',
                behavior_constraints TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS npc_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_id TEXT NOT NULL,
                layer TEXT NOT NULL DEFAULT 'episodic',
                content TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 1,
                source_type TEXT NOT NULL DEFAULT 'system',
                tags TEXT NOT NULL DEFAULT '[]',
                related_entity TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS player_relation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_id TEXT NOT NULL UNIQUE,
                relation_value INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                location TEXT NOT NULL,
                payload TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS save_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                game_time TEXT NOT NULL,
                current_location TEXT NOT NULL,
                player_state TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS npc_runtime_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_id TEXT NOT NULL UNIQUE,
                current_location TEXT NOT NULL,
                current_action TEXT NOT NULL,
                mood TEXT NOT NULL,
                goal TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS npc_perception (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_id TEXT NOT NULL,
                event_id INTEGER,
                source_type TEXT NOT NULL,
                perceived_fact TEXT NOT NULL,
                confidence REAL NOT NULL,
                observed_at TEXT NOT NULL
            );
            """
        )
        _migrate_schema(conn)
        _seed_default_data(conn)
        conn.commit()


def _migrate_schema(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(npc)").fetchall()
    }
    if "role" not in columns:
        conn.execute("ALTER TABLE npc ADD COLUMN role TEXT NOT NULL DEFAULT 'unknown'")
    if "age" not in columns:
        conn.execute("ALTER TABLE npc ADD COLUMN age INTEGER NOT NULL DEFAULT 20")
    if "occupation" not in columns:
        conn.execute("ALTER TABLE npc ADD COLUMN occupation TEXT NOT NULL DEFAULT ''")
    if "base_location" not in columns:
        conn.execute("ALTER TABLE npc ADD COLUMN base_location TEXT NOT NULL DEFAULT ''")
    if "personality_traits" not in columns:
        conn.execute("ALTER TABLE npc ADD COLUMN personality_traits TEXT NOT NULL DEFAULT '{}'")
    if "long_term_goals" not in columns:
        conn.execute("ALTER TABLE npc ADD COLUMN long_term_goals TEXT NOT NULL DEFAULT '[]'")
    if "daily_routine" not in columns:
        conn.execute("ALTER TABLE npc ADD COLUMN daily_routine TEXT NOT NULL DEFAULT '[]'")
    if "social_relations" not in columns:
        conn.execute("ALTER TABLE npc ADD COLUMN social_relations TEXT NOT NULL DEFAULT '[]'")
    if "behavior_constraints" not in columns:
        conn.execute("ALTER TABLE npc ADD COLUMN behavior_constraints TEXT NOT NULL DEFAULT '[]'")

    memory_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(npc_memory)").fetchall()
    }
    if "layer" not in memory_columns:
        conn.execute("ALTER TABLE npc_memory ADD COLUMN layer TEXT NOT NULL DEFAULT 'episodic'")
    if "source_type" not in memory_columns:
        conn.execute("ALTER TABLE npc_memory ADD COLUMN source_type TEXT NOT NULL DEFAULT 'system'")
    if "tags" not in memory_columns:
        conn.execute("ALTER TABLE npc_memory ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'")
    if "related_entity" not in memory_columns:
        conn.execute("ALTER TABLE npc_memory ADD COLUMN related_entity TEXT NOT NULL DEFAULT ''")
    if "metadata" not in memory_columns:
        conn.execute("ALTER TABLE npc_memory ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'")


def _seed_default_data(conn: sqlite3.Connection) -> None:
    npcs = _read_json("npcs.json")
    for npc in npcs:
        conn.execute(
            """
            INSERT OR IGNORE INTO npc (
                npc_id, name, role, personality, initial_location,
                age, occupation, base_location, personality_traits,
                long_term_goals, daily_routine, social_relations, behavior_constraints
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                npc["npc_id"],
                npc["name"],
                npc.get("role", "unknown"),
                npc["personality"],
                npc["initial_location"],
                int(npc.get("age", 20)),
                npc.get("occupation", ""),
                npc.get("base_location", npc["initial_location"]),
                json.dumps(npc.get("personality_traits", {}), ensure_ascii=False),
                json.dumps(npc.get("long_term_goals", []), ensure_ascii=False),
                json.dumps(npc.get("daily_routine", []), ensure_ascii=False),
                json.dumps(npc.get("social_relations", []), ensure_ascii=False),
                json.dumps(npc.get("behavior_constraints", []), ensure_ascii=False),
            ),
        )
        conn.execute(
            """
            UPDATE npc
            SET name = ?, role = ?, personality = ?, initial_location = ?,
                age = ?, occupation = ?, base_location = ?, personality_traits = ?,
                long_term_goals = ?, daily_routine = ?, social_relations = ?, behavior_constraints = ?
            WHERE npc_id = ?
            """,
            (
                npc["name"],
                npc.get("role", "unknown"),
                npc["personality"],
                npc["initial_location"],
                int(npc.get("age", 20)),
                npc.get("occupation", ""),
                npc.get("base_location", npc["initial_location"]),
                json.dumps(npc.get("personality_traits", {}), ensure_ascii=False),
                json.dumps(npc.get("long_term_goals", []), ensure_ascii=False),
                json.dumps(npc.get("daily_routine", []), ensure_ascii=False),
                json.dumps(npc.get("social_relations", []), ensure_ascii=False),
                json.dumps(npc.get("behavior_constraints", []), ensure_ascii=False),
                npc["npc_id"],
            ),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO player_relation (npc_id, relation_value)
            VALUES (?, ?)
            """,
            (npc["npc_id"], int(npc.get("initial_relation", 0))),
        )

    state_count = conn.execute("SELECT COUNT(*) AS count FROM save_state").fetchone()["count"]
    if state_count == 0:
        default_player_state = json.dumps(
            {"energy": 100, "mood": 70, "stress": 20, "focus": 60}, ensure_ascii=False
        )
        conn.execute(
            """
            INSERT INTO save_state (id, game_time, current_location, player_state, updated_at)
            VALUES (1, '07:00', '宿舍', ?, DATETIME('now'))
            """,
            (default_player_state,),
        )

    runtime_count = conn.execute(
        "SELECT COUNT(*) AS count FROM npc_runtime_state"
    ).fetchone()["count"]
    if runtime_count == 0:
        for npc in npcs:
            conn.execute(
                """
                INSERT INTO npc_runtime_state
                (npc_id, current_location, current_action, mood, goal, updated_at)
                VALUES (?, ?, ?, ?, ?, DATETIME('now'))
                """,
                (
                    npc["npc_id"],
                    npc["initial_location"],
                    "等待中",
                    npc.get("initial_mood", "stable"),
                    npc.get("default_goal", "保持日常节奏"),
                ),
            )


def _read_json(filename: str) -> list[dict[str, Any]]:
    path = _resolve_data_dir() / filename
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
