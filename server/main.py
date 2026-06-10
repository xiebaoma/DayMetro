from __future__ import annotations

from typing import Optional
from time import perf_counter

from fastapi import FastAPI, HTTPException
from fastapi import Request
from pydantic import BaseModel, Field

from server.database import get_connection, init_database
from server.logging_service import configure_logging, get_logger
from server.npc_agent.services.factory import build_services
from server.npc_agent.services.action_system import allowed_action_specs

configure_logging()
logger = get_logger("daymetro.api")
app = FastAPI(title="DayMetro Server", version="0.1.0")


class DialogueRequest(BaseModel):
    npc_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class EventRequest(BaseModel):
    event_type: str = Field(min_length=1)
    location: str = Field(min_length=1)
    payload: dict = Field(default_factory=dict)
    game_time: Optional[str] = None


class DialogueChoiceRequest(BaseModel):
    npc_id: str = Field(min_length=1)
    option_id: str = Field(min_length=1)
    use_llm: bool = False


class PlayerActionRequest(BaseModel):
    action_type: str = Field(min_length=1)
    location: str = Field(min_length=1)
    payload: dict = Field(default_factory=dict)
    game_time: Optional[str] = None


@app.on_event("startup")
def _startup() -> None:
    init_database()
    logger.info("server startup complete")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request failed method=%s path=%s", request.method, request.url.path)
        raise
    elapsed_ms = (perf_counter() - start) * 1000
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/world/state")
def world_state() -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        state = services["world"].get_world_state()
    if state is None:
        raise HTTPException(status_code=500, detail="save_state is not initialized")
    return state


@app.post("/dialogue")
def dialogue(payload: DialogueRequest) -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        result = services["interaction"].free_talk(payload.npc_id, payload.message)
        conn.commit()
    if result is None:
        raise HTTPException(status_code=404, detail="npc not found")
    logger.info("dialogue npc_id=%s message_len=%s", payload.npc_id, len(payload.message))
    return result


@app.get("/dialogue/options")
def dialogue_options(npc_id: str) -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        result = services["interaction"].get_dialogue_options(npc_id)
    if result is None:
        raise HTTPException(status_code=404, detail="npc not found")
    return result


@app.post("/dialogue/choice")
def dialogue_choice(payload: DialogueChoiceRequest) -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        result = services["interaction"].apply_choice(
            payload.npc_id, payload.option_id, payload.use_llm
        )
        conn.commit()
    if result is None:
        raise HTTPException(status_code=404, detail="npc not found")
    logger.info(
        "dialogue_choice npc_id=%s option_id=%s use_llm=%s",
        payload.npc_id,
        payload.option_id,
        payload.use_llm,
    )
    return result


@app.post("/event")
def event(payload: EventRequest) -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        result = services["event"].log_event(
            payload.event_type, payload.location, payload.payload, payload.game_time
        )
        if payload.game_time:
            services["perception"].distribute_event_perception(
                event_id=result["event_id"],
                event_type=payload.event_type,
                location=payload.location,
                payload=payload.payload,
                game_time=payload.game_time,
                observed_at=result["created_at"],
            )
        # Explicit sync point: state transitions are advanced by clock tick events.
        if payload.event_type == "tick":
            services["world"].sync_npc_runtime()
        conn.commit()
    logger.info(
        "event event_id=%s type=%s location=%s game_time=%s",
        result["event_id"],
        payload.event_type,
        payload.location,
        payload.game_time,
    )
    return {
        "status": result["status"],
        "event_id": result["event_id"],
        "created_at": result["created_at"],
    }


@app.get("/event/logs")
def event_logs(limit: int = 50) -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        return services["event"].list_logs(limit)


@app.get("/npc/perception")
def npc_perception(npc_id: str, limit: int = 10) -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        items = services["perception"].get_recent_perceptions(npc_id, limit)
        return {"npc_id": npc_id, "perceptions": items}


@app.get("/npc/actions")
def npc_actions() -> dict:
    return {"actions": allowed_action_specs()}


@app.get("/npc/memory")
def npc_memory(npc_id: str, limit: int = 10) -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        items = services["memory"].get_recent_memory_records(npc_id, limit)
    return {"npc_id": npc_id, "memories": items}


@app.get("/npc/relation")
def npc_relation(npc_id: str) -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        profile = services["relation"].get_profile(npc_id)
    return {
        "npc_id": npc_id,
        "relation_with_player": profile.relation_value,
        "trust_with_player": profile.trust_value,
        "conflict_with_player": profile.conflict_value,
        "familiarity_with_player": profile.familiarity_value,
    }


@app.post("/player/action")
def player_action(payload: PlayerActionRequest) -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        result = services["player_state"].apply_action(
            action_type=payload.action_type,
            location=payload.location,
            game_time=payload.game_time,
            payload=payload.payload,
        )
        conn.commit()
    logger.info(
        "player_action action_type=%s location=%s event_id=%s",
        payload.action_type,
        payload.location,
        result.get("event_id"),
    )
    return result


@app.post("/daily/review")
def daily_review() -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        result = services["daily_review"].generate_review()
        conn.commit()
    if result is None:
        raise HTTPException(status_code=500, detail="save_state is not initialized")
    logger.info("daily_review id=%s event_id=%s", result.get("id"), result.get("event_id"))
    return result


@app.get("/daily/review/latest")
def latest_daily_review() -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        result = services["daily_review"].latest_review()
    if result is None:
        raise HTTPException(status_code=404, detail="daily review not found")
    return result


@app.get("/npc/proactive")
def npc_proactive(location: Optional[str] = None, limit: int = 3) -> dict:
    with get_connection() as conn:
        services = build_services(conn)
        result = services["proactive"].get_proactive_actions(location, limit)
        conn.commit()
    if result is None:
        raise HTTPException(status_code=500, detail="save_state is not initialized")
    logger.info(
        "npc_proactive location=%s count=%s",
        result.get("location"),
        len(result.get("proactive_actions", [])),
    )
    return result
