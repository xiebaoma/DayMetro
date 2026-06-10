from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from server.database import get_connection, init_database
from server.npc_agent.services.factory import build_services

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


@app.on_event("startup")
def _startup() -> None:
    init_database()


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
    return {"status": result["status"]}


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
