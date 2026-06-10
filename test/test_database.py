from __future__ import annotations

from pathlib import Path

from server.database import get_connection, init_database


def test_init_database_creates_core_tables(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DAYMETRO_DB_PATH", str(tmp_path / "test_save.db"))
    monkeypatch.setenv(
        "DAYMETRO_DATA_DIR",
        str(Path(__file__).resolve().parent.parent / "data"),
    )

    init_database()

    with get_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        npc_count = conn.execute("SELECT COUNT(*) AS count FROM npc").fetchone()["count"]
        npc_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(npc)").fetchall()
        }
        memory_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(npc_memory)").fetchall()
        }
        relation_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(player_relation)").fetchall()
        }

    assert {
        "npc",
        "npc_memory",
        "player_relation",
        "event_log",
        "save_state",
        "npc_runtime_state",
        "npc_perception",
        "daily_review",
    } <= tables
    assert "role" in npc_columns
    assert {
        "age",
        "occupation",
        "base_location",
        "personality_traits",
        "long_term_goals",
        "daily_routine",
        "social_relations",
        "behavior_constraints",
    } <= npc_columns
    assert npc_count >= 5
    assert {
        "layer",
        "memory_type",
        "source_type",
        "tags",
        "related_entity",
        "related_event_id",
        "metadata",
        "last_used_at",
    } <= memory_columns
    assert {"trust_value", "conflict_value", "familiarity_value"} <= relation_columns
