from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def _set_test_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DAYMETRO_DB_PATH", str(tmp_path / "test_save.db"))
    monkeypatch.setenv(
        "DAYMETRO_DATA_DIR",
        str(Path(__file__).resolve().parent.parent / "data"),
    )


def test_health(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_world_state_contains_seeded_npcs(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        response = client.get("/world/state")
    body = response.json()
    assert response.status_code == 200
    assert body["game_time"] == "07:00"
    assert body["current_location"] == "宿舍"
    assert "time_label" in body
    assert "time_points" in body
    assert len(body["npcs"]) >= 5
    first_npc = body["npcs"][0]
    assert {
        "id",
        "name",
        "role",
        "personality",
        "identity_profile",
        "current_location",
        "current_action",
        "mood",
        "goal",
        "schedule",
        "relation_with_player",
    } <= set(first_npc.keys())
    assert {
        "age",
        "occupation",
        "base_location",
        "personality_traits",
        "long_term_goals",
        "daily_routine",
        "social_relations",
        "behavior_constraints",
    } <= set(first_npc["identity_profile"].keys())


def test_dialogue_records_memory(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        dialogue_response = client.post(
            "/dialogue",
            json={"npc_id": "mentor", "message": "我今天会修复接口超时问题"},
        )
        world_response = client.get("/world/state")

    assert dialogue_response.status_code == 200
    assert dialogue_response.json()["npc_id"] == "mentor"
    assert "我今天会修复接口超时问题" in dialogue_response.json()["reply"]
    assert world_response.status_code == 200


def test_event_updates_world_state(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        event_response = client.post(
            "/event",
            json={
                "event_type": "arrive_company",
                "location": "公司",
                "payload": {"source": "metro"},
                "game_time": "10:00",
            },
        )
        world_response = client.get("/world/state")

    assert event_response.status_code == 200
    assert event_response.json()["status"] == "logged"
    assert world_response.status_code == 200
    assert world_response.json()["game_time"] == "10:00"
    assert world_response.json()["current_location"] == "公司"


def test_route_events_are_persisted(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    route_events = [
        ("enter_dorm", "宿舍", "07:00"),
        ("arrive_metro", "地铁", "08:20"),
        ("arrive_company", "公司", "10:00"),
        ("enter_canteen", "食堂", "12:00"),
        ("return_company", "公司", "13:00"),
        ("arrive_playground", "操场", "20:30"),
        ("back_to_dorm", "宿舍", "23:30"),
    ]

    with TestClient(app) as client:
        for event_type, location, game_time in route_events:
            event_response = client.post(
                "/event",
                json={
                    "event_type": event_type,
                    "location": location,
                    "payload": {"from_test": True},
                    "game_time": game_time,
                },
            )
            assert event_response.status_code == 200

        logs_response = client.get("/event/logs?limit=10")
        world_response = client.get("/world/state")

    assert logs_response.status_code == 200
    logged_types = [item["event_type"] for item in logs_response.json()["events"]]
    assert "back_to_dorm" in logged_types
    assert "arrive_company" in logged_types
    assert world_response.status_code == 200
    assert world_response.json()["current_location"] == "宿舍"
    assert world_response.json()["game_time"] == "23:30"


def test_npc_schedule_visibility_by_time(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        client.post(
            "/event",
            json={"event_type": "tick", "location": "宿舍", "payload": {}, "game_time": "07:00"},
        )
        morning_state = client.get("/world/state").json()

        client.post(
            "/event",
            json={"event_type": "tick", "location": "食堂", "payload": {}, "game_time": "12:00"},
        )
        noon_state = client.get("/world/state").json()

        client.post(
            "/event",
            json={"event_type": "tick", "location": "公司", "payload": {}, "game_time": "14:00"},
        )
        afternoon_state = client.get("/world/state").json()

        client.post(
            "/event",
            json={"event_type": "tick", "location": "宿舍", "payload": {}, "game_time": "22:30"},
        )
        night_state = client.get("/world/state").json()

    morning_locations = {item["id"]: item["current_location"] for item in morning_state["npcs"]}
    noon_locations = {item["id"]: item["current_location"] for item in noon_state["npcs"]}
    afternoon_locations = {item["id"]: item["current_location"] for item in afternoon_state["npcs"]}
    night_locations = {item["id"]: item["current_location"] for item in night_state["npcs"]}

    assert morning_locations["roommate_a"] == "宿舍"
    assert morning_locations["roommate_b"] == "宿舍"
    assert noon_locations["coworker_a"] == "食堂"
    assert noon_locations["coworker_b"] == "食堂"
    assert afternoon_locations["coworker_a"] == "公司"
    assert afternoon_locations["mentor"] == "公司"
    assert night_locations["roommate_b"] == "宿舍"


def test_npc_state_change_is_logged(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        client.post(
            "/event",
            json={"event_type": "tick", "location": "公司", "payload": {}, "game_time": "10:00"},
        )
        client.get("/world/state")
        client.post(
            "/event",
            json={"event_type": "tick", "location": "公司", "payload": {}, "game_time": "14:00"},
        )
        client.get("/world/state")
        logs_response = client.get("/event/logs?limit=50")

    assert logs_response.status_code == 200
    changed_events = [
        event for event in logs_response.json()["events"] if event["event_type"] == "npc_state_changed"
    ]
    assert len(changed_events) > 0


def test_dialogue_options_returns_npc_status(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        response = client.get("/dialogue/options?npc_id=mentor")

    assert response.status_code == 200
    body = response.json()
    assert body["npc"]["id"] == "mentor"
    assert body["npc"]["avatar"] == "placeholder"
    assert "identity_profile" in body["npc"]
    assert len(body["options"]) == 4


def test_dialogue_choice_updates_relation_and_logs(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        before_state = client.get("/world/state").json()
        before_relation = {
            item["id"]: item["relation_with_player"] for item in before_state["npcs"]
        }["roommate_a"]

        choice_response = client.post(
            "/dialogue/choice",
            json={"npc_id": "roommate_a", "option_id": "care_mood"},
        )
        after_state = client.get("/world/state").json()
        logs_response = client.get("/event/logs?limit=20")

    assert choice_response.status_code == 200
    assert "reply" in choice_response.json()
    after_relation = {
        item["id"]: item["relation_with_player"] for item in after_state["npcs"]
    }["roommate_a"]
    assert after_relation >= before_relation + 2

    event_types = [event["event_type"] for event in logs_response.json()["events"]]
    assert "dialogue_care_mood" in event_types


def test_same_choice_diff_npc_gets_diff_reply(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        mentor_reply = client.post(
            "/dialogue/choice",
            json={"npc_id": "mentor", "option_id": "ask_status"},
        ).json()["reply"]
        coworker_reply = client.post(
            "/dialogue/choice",
            json={"npc_id": "coworker_a", "option_id": "ask_status"},
        ).json()["reply"]

    assert mentor_reply != coworker_reply
    assert "导师" in mentor_reply
    assert "同事A" in coworker_reply


def test_perception_is_local_not_omniscient(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        client.post(
            "/event",
            json={"event_type": "tick", "location": "公司", "payload": {}, "game_time": "10:00"},
        )
        client.post(
            "/event",
            json={
                "event_type": "player_idle",
                "location": "公司",
                "payload": {"description": "玩家在公司工位摸鱼"},
                "game_time": "10:05",
            },
        )
        coworker_perception = client.get("/npc/perception?npc_id=coworker_a&limit=10").json()
        roommate_perception = client.get("/npc/perception?npc_id=roommate_a&limit=10").json()

    coworker_facts = [item["perceived_fact"] for item in coworker_perception["perceptions"]]
    roommate_facts = [item["perceived_fact"] for item in roommate_perception["perceptions"]]
    assert any("摸鱼" in fact for fact in coworker_facts)
    assert not any("摸鱼" in fact for fact in roommate_facts)


def test_perception_can_be_shared_by_telling(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        client.post(
            "/event",
            json={
                "event_type": "share_info",
                "location": "公司",
                "payload": {
                    "description": "同事告诉别人玩家在公司摸鱼",
                    "told_to_npc_ids": ["roommate_a"],
                    "shared_fact": "有人告诉我玩家今天在公司摸鱼",
                },
                "game_time": "11:00",
            },
        )
        roommate_perception = client.get("/npc/perception?npc_id=roommate_a&limit=10").json()

    facts = [item["perceived_fact"] for item in roommate_perception["perceptions"]]
    sources = [item["source_type"] for item in roommate_perception["perceptions"]]
    assert any("告诉我玩家今天在公司摸鱼" in fact for fact in facts)
    assert "told" in sources
