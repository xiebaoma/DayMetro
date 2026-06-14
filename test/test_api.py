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
    assert {
        "energy",
        "mood",
        "stress",
        "focus",
        "learning",
        "code",
        "social",
        "health",
        "sleep_quality",
    } <= set(body["player_state"].keys())
    assert len(body["npcs"]) >= 6
    roommate_profiles = {item["id"]: item for item in body["npcs"] if item["role"] == "roommate"}
    assert {"roommate_a", "roommate_b", "roommate_c"} <= set(roommate_profiles.keys())
    assert "成绩" in " ".join(roommate_profiles["roommate_a"]["identity_profile"]["long_term_goals"])
    assert "汽车" in " ".join(roommate_profiles["roommate_b"]["identity_profile"]["daily_routine"])
    assert "打游戏" in " ".join(roommate_profiles["roommate_c"]["identity_profile"]["daily_routine"])
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
        "trust_with_player",
        "conflict_with_player",
        "familiarity_with_player",
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
        memory_response = client.get("/npc/memory?npc_id=mentor&limit=10")

    assert dialogue_response.status_code == 200
    assert dialogue_response.json()["npc_id"] == "mentor"
    assert "我今天会修复接口超时问题" in dialogue_response.json()["reply"]
    assert dialogue_response.json()["actions"][0]["action"] == "say"
    assert "我今天会修复接口超时问题" in dialogue_response.json()["actions"][0]["content"]
    assert world_response.status_code == 200

    memories = memory_response.json()["memories"]
    assert any(item["related_event_id"] is not None for item in memories)
    assert any(item["memory_type"] == "日常聊天" for item in memories)


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
    assert morning_locations["roommate_c"] == "宿舍"
    assert noon_locations["coworker_a"] == "食堂"
    assert noon_locations["coworker_b"] == "食堂"
    assert afternoon_locations["coworker_a"] == "公司"
    assert afternoon_locations["mentor"] == "公司"
    assert night_locations["roommate_b"] == "宿舍"
    assert night_locations["roommate_c"] == "宿舍"


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
    assert choice_response.json()["actions"][0]["action"] == "say"
    assert any(
        action["action"] == "update_relationship"
        for action in choice_response.json()["actions"]
    )
    after_relation = {
        item["id"]: item["relation_with_player"] for item in after_state["npcs"]
    }["roommate_a"]
    assert after_relation >= before_relation + 2

    event_types = [event["event_type"] for event in logs_response.json()["events"]]
    assert "dialogue_care_mood" in event_types


def test_npc_actions_exposes_allowed_action_catalog(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        response = client.get("/npc/actions")

    assert response.status_code == 200
    action_names = {item["action"] for item in response.json()["actions"]}
    assert {
        "say",
        "move_to",
        "look_at",
        "give_item",
        "take_item",
        "start_task",
        "stop_task",
        "update_relationship",
        "remember",
        "ask_question",
    } <= action_names


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


def test_help_event_generates_traceable_memory_and_trust(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        event_response = client.post(
            "/event",
            json={
                "event_type": "help_npc",
                "location": "公司",
                "payload": {
                    "npc_id": "coworker_a",
                    "task": "接口超时排查",
                    "description": "玩家帮同事A排查了接口超时问题",
                },
                "game_time": "15:00",
            },
        )
        relation_response = client.get("/npc/relation?npc_id=coworker_a")
        memory_response = client.get("/npc/memory?npc_id=coworker_a&limit=10")

    assert event_response.status_code == 200
    event_id = event_response.json()["event_id"]
    relation = relation_response.json()
    assert relation["trust_with_player"] >= 5
    assert relation["relation_with_player"] >= 10

    memories = memory_response.json()["memories"]
    assert any(
        item["memory_type"] == "帮助"
        and item["related_event_id"] == event_id
        and "接口超时" in item["content"]
        for item in memories
    )


def test_broken_promise_increases_conflict_and_affects_next_reply(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        client.post(
            "/event",
            json={
                "event_type": "no_show",
                "location": "宿舍",
                "payload": {
                    "npc_id": "roommate_a",
                    "task": "晚上一起打游戏",
                    "description": "玩家昨晚答应室友A一起打游戏但爽约了",
                },
                "game_time": "23:00",
            },
        )
        relation_response = client.get("/npc/relation?npc_id=roommate_a")
        dialogue_response = client.post(
            "/dialogue",
            json={"npc_id": "roommate_a", "message": "早啊，今天一起吃饭吗"},
        )

    relation = relation_response.json()
    assert relation["trust_with_player"] <= -5
    assert relation["conflict_with_player"] >= 3
    assert "爽约" in dialogue_response.json()["reply"]


def test_player_action_updates_state_and_logs_event(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        before_state = client.get("/world/state").json()["player_state"]
        action_response = client.post(
            "/player/action",
            json={
                "action_type": "work",
                "location": "公司",
                "game_time": "14:30",
                "payload": {"description": "下午推进后端开发"},
            },
        )
        after_state = client.get("/world/state").json()["player_state"]
        logs_response = client.get("/event/logs?limit=5")

    assert action_response.status_code == 200
    body = action_response.json()
    assert body["status"] == "applied"
    assert body["effects"]["code"] == 6
    assert after_state["code"] == before_state["code"] + 6
    assert after_state["energy"] < before_state["energy"]
    assert any(
        event["event_type"] == "player_action_work"
        for event in logs_response.json()["events"]
    )


def test_daily_review_summarizes_full_day_and_is_saved(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    route_events = [
        ("enter_dorm", "宿舍", "07:00"),
        ("arrive_metro", "地铁", "08:20"),
        ("arrive_company", "公司", "09:30"),
        ("enter_canteen", "食堂", "12:00"),
        ("return_company", "公司", "14:00"),
        ("arrive_playground", "操场", "20:30"),
        ("back_to_dorm", "宿舍", "23:00"),
    ]
    actions = [
        ("morning_prepare", "宿舍", "07:20"),
        ("commute_rest", "地铁", "08:40"),
        ("morning_meeting", "公司", "10:00"),
        ("work", "公司", "14:30"),
        ("lunch_chat", "食堂", "12:20"),
        ("walk_playground", "操场", "20:40"),
        ("late_browse", "宿舍", "23:20"),
    ]

    with TestClient(app) as client:
        for event_type, location, game_time in route_events:
            client.post(
                "/event",
                json={
                    "event_type": event_type,
                    "location": location,
                    "payload": {"from_test": True},
                    "game_time": game_time,
                },
            )
        client.post(
            "/dialogue/choice",
            json={"npc_id": "coworker_a", "option_id": "care_mood"},
        )
        for action_type, location, game_time in actions:
            client.post(
                "/player/action",
                json={
                    "action_type": action_type,
                    "location": location,
                    "game_time": game_time,
                    "payload": {"description": action_type},
                },
            )
        review_response = client.post("/daily/review")
        latest_response = client.get("/daily/review/latest")

    assert review_response.status_code == 200
    review = review_response.json()
    assert review["route"][:3] == ["宿舍", "地铁", "公司"]
    assert "操场" in review["route"]
    assert len(review["important_events"]) >= 5
    assert any(item["npc_id"] == "coworker_a" for item in review["npc_interactions"])
    assert {"宿舍", "公司"} <= set(review["keywords"])
    assert "今日路线" in review["summary"]
    assert review["tomorrow_hint"]
    assert latest_response.status_code == 200
    assert latest_response.json()["id"] == review["id"]


def test_proactive_actions_include_memory_current_state_and_throttle(monkeypatch, tmp_path: Path) -> None:
    _set_test_env(monkeypatch, tmp_path)
    from server.main import app

    with TestClient(app) as client:
        client.post(
            "/event",
            json={
                "event_type": "help_npc",
                "location": "公司",
                "payload": {
                    "npc_id": "coworker_a",
                    "task": "修复接口超时",
                    "description": "玩家昨天帮同事A修复接口超时",
                },
                "game_time": "11:30",
            },
        )
        client.post(
            "/event",
            json={"event_type": "tick", "location": "食堂", "payload": {}, "game_time": "12:00"},
        )
        coworker_response = client.get("/npc/proactive?location=食堂&limit=3")
        repeated_response = client.get("/npc/proactive?location=食堂&limit=3")

        client.post(
            "/event",
            json={"event_type": "tick", "location": "公司", "payload": {}, "game_time": "10:00"},
        )
        mentor_response = client.get("/npc/proactive?location=公司&limit=3")

        client.post(
            "/player/action",
            json={
                "action_type": "late_browse",
                "location": "宿舍",
                "game_time": "22:30",
                "payload": {"description": "深夜继续刷信息流"},
            },
        )
        roommate_response = client.get("/npc/proactive?location=宿舍&limit=3")

    coworker_actions = coworker_response.json()["proactive_actions"]
    assert any(item["npc_id"] == "coworker_a" for item in coworker_actions)
    assert any(item["proactive_type"] == "memory_followup_help" for item in coworker_actions)
    assert any("memory" in item for item in coworker_actions)
    assert repeated_response.json()["proactive_actions"] == []

    mentor_actions = mentor_response.json()["proactive_actions"]
    assert any(item["npc_id"] == "mentor" for item in mentor_actions)
    assert any(item["proactive_type"] == "reminder" for item in mentor_actions)

    roommate_actions = roommate_response.json()["proactive_actions"]
    assert any(item["npc_id"].startswith("roommate_") for item in roommate_actions)
    assert any(item["proactive_type"] == "state_check" for item in roommate_actions)
    assert all(
        action["action"] in {"look_at", "say", "ask_question", "start_task"}
        for item in coworker_actions + mentor_actions + roommate_actions
        for action in item["actions"]
    )
