from __future__ import annotations

from pathlib import Path

from server.database import get_connection, init_database
from server.npc_agent.services.factory import build_services


def _setup_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DAYMETRO_DB_PATH", str(tmp_path / "service_test.db"))
    monkeypatch.setenv(
        "DAYMETRO_DATA_DIR",
        str(Path(__file__).resolve().parent.parent / "data"),
    )


def test_interaction_service_choice_persists_effects(monkeypatch, tmp_path: Path) -> None:
    _setup_env(monkeypatch, tmp_path)
    init_database()

    with get_connection() as conn:
        services = build_services(conn)
        before = services["interaction"].get_dialogue_options("roommate_a")
        result = services["interaction"].apply_choice("roommate_a", "care_mood", use_llm=False)
        after = services["interaction"].get_dialogue_options("roommate_a")
        conn.commit()

    assert before is not None
    assert result is not None
    assert after is not None
    assert before["npc"]["identity_profile"]["occupation"] != ""
    assert result["effects"]["new_relation"] >= before["npc"]["relation_with_player"] + 2
    assert after["npc"]["mood"] == "calm"


def test_world_service_read_is_side_effect_free(monkeypatch, tmp_path: Path) -> None:
    _setup_env(monkeypatch, tmp_path)
    init_database()

    with get_connection() as conn:
        services = build_services(conn)
        initial_count = conn.execute("SELECT COUNT(*) AS count FROM event_log").fetchone()["count"]
        _ = services["world"].get_world_state()
        after_count = conn.execute("SELECT COUNT(*) AS count FROM event_log").fetchone()["count"]

    assert initial_count == after_count


def test_npc_state_service_sync_writes_state_change_event(monkeypatch, tmp_path: Path) -> None:
    _setup_env(monkeypatch, tmp_path)
    init_database()

    with get_connection() as conn:
        services = build_services(conn)
        services["event"].log_event("tick", "公司", {}, "10:00")
        states = services["npc_state"].compute_npc_states("10:00")
        services["npc_state"].sync_runtime_state(states)
        conn.commit()
        changed_count = conn.execute(
            "SELECT COUNT(*) AS count FROM event_log WHERE event_type = 'npc_state_changed'"
        ).fetchone()["count"]

    assert changed_count > 0


def test_memory_system_writes_layered_memories(monkeypatch, tmp_path: Path) -> None:
    _setup_env(monkeypatch, tmp_path)
    init_database()

    with get_connection() as conn:
        services = build_services(conn)
        services["interaction"].free_talk("mentor", "我工作日经常坐7:30地铁去公司，和室友关系不错")
        services["interaction"].apply_choice("mentor", "care_mood", use_llm=False)
        conn.commit()
        layers = {
            row["layer"]
            for row in conn.execute(
                "SELECT DISTINCT layer FROM npc_memory WHERE npc_id = 'mentor'"
            ).fetchall()
        }

    assert {"working", "episodic", "relationship", "semantic"} <= layers
