from __future__ import annotations

from pathlib import Path

from server.adapters.daymetro.factory import build_services
from server.database import get_connection, init_database
from server.npc_agent.domain.decision import NpcIntent


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


def test_event_pipeline_writes_perception_memory_and_relation(monkeypatch, tmp_path: Path) -> None:
    _setup_env(monkeypatch, tmp_path)
    init_database()

    with get_connection() as conn:
        services = build_services(conn)
        before = services["relation"].get_profile("coworker_a")
        result = services["event_pipeline"].record_event(
            event_type="help_npc",
            location="公司",
            payload={"npc_id": "coworker_a", "description": "玩家帮同事A修好了接口问题。"},
            game_time="09:30",
        )
        conn.commit()
        after = services["relation"].get_profile("coworker_a")
        memory_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM npc_memory
            WHERE npc_id = 'coworker_a' AND memory_type = '帮助'
            """
        ).fetchone()["count"]
        perception_count = conn.execute(
            "SELECT COUNT(*) AS count FROM npc_perception WHERE event_id = ?",
            (result["event_id"],),
        ).fetchone()["count"]

    assert after.trust_value >= before.trust_value + 5
    assert memory_count >= 1
    assert perception_count >= 1


def test_cognition_service_builds_belief_from_state(monkeypatch, tmp_path: Path) -> None:
    _setup_env(monkeypatch, tmp_path)
    init_database()

    with get_connection() as conn:
        services = build_services(conn)
        npc = [
            state
            for state in services["npc_state"].compute_npc_states("09:30")
            if state.id == "coworker_a"
        ][0]
        memory_context = services["memory"].system.build_context("coworker_a", query="", per_layer=1)
        belief = services["cognition"].build_belief(
            npc=npc,
            memory_context=memory_context,
            perceptions=[],
            player_state={"stress": 70, "energy": 80, "sleep_quality": 80, "mood": 60},
        )

    assert belief.npc_id == "coworker_a"
    assert belief.player_state_signal == "stressed"
    assert belief.emotion.mood == "concerned"


def test_execution_service_maps_intent_to_action_plan(monkeypatch, tmp_path: Path) -> None:
    _setup_env(monkeypatch, tmp_path)
    init_database()

    with get_connection() as conn:
        services = build_services(conn)
        result = services["execution"].execute_intent(
            NpcIntent(
                npc_id="coworker_a",
                npc_name="同事A",
                intent_type="current_state_invite",
                reason="test",
                speech="中午一起吃饭吗？",
                parameters={"question": "要不要一起去食堂？"},
            )
        )

    assert result.executed is False
    assert [item["action"] for item in result.actions] == ["look_at", "say", "ask_question"]
