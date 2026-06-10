from __future__ import annotations

from datetime import datetime, timezone

from server.npc_agent.domain.models import NpcRuntimeState, NpcState
from server.npc_agent.ports.repositories import EventRepository, NpcRepository, RuntimeStateRepository


class NpcStateService:
    def __init__(
        self,
        npc_repo: NpcRepository,
        runtime_repo: RuntimeStateRepository,
        event_repo: EventRepository,
        schedule_slot_provider,
    ):
        self.npc_repo = npc_repo
        self.runtime_repo = runtime_repo
        self.event_repo = event_repo
        self.schedule_slot_provider = schedule_slot_provider

    def compute_npc_states(self, game_time: str) -> list[NpcState]:
        rows = self.npc_repo.list_profiles_with_relation()
        npc_states: list[NpcState] = []
        for row in rows:
            slot = self.schedule_slot_provider(row["npc_id"], game_time) or {}
            if slot:
                runtime_state = NpcRuntimeState(
                    npc_id=row["npc_id"],
                    current_location=slot.get("location", row["initial_location"]),
                    current_action=slot.get("action", "日常活动"),
                    mood=slot.get("mood", "stable"),
                    goal=slot.get("goal", "推进今天计划"),
                )
                schedule = [slot]
            else:
                runtime_state = NpcRuntimeState(
                    npc_id=row["npc_id"],
                    current_location=row["initial_location"],
                    current_action="休息中",
                    mood="neutral",
                    goal="等待下一个时间段",
                )
                schedule = []

            npc_states.append(
                NpcState(
                    id=row["npc_id"],
                    name=row["name"],
                    role=row["role"],
                    personality=row["personality"],
                    current_location=runtime_state.current_location,
                    current_action=runtime_state.current_action,
                    mood=runtime_state.mood,
                    goal=runtime_state.goal,
                    identity_profile=row["identity_profile"],
                    schedule=schedule,
                    relation_with_player=int(row["relation_value"] or 0),
                )
            )
        return npc_states

    def sync_runtime_state(self, npc_states: list[NpcState]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for state in npc_states:
            existing = self.runtime_repo.get_runtime_state(state.id)
            next_runtime = NpcRuntimeState(
                npc_id=state.id,
                current_location=state.current_location,
                current_action=state.current_action,
                mood=state.mood,
                goal=state.goal,
            )
            if existing is None:
                self.runtime_repo.upsert_runtime_state(next_runtime, now)
                continue

            changes = {}
            for field in ("current_location", "current_action", "mood", "goal"):
                old_value = getattr(existing, field)
                new_value = getattr(next_runtime, field)
                if old_value != new_value:
                    changes[field] = {"from": old_value, "to": new_value}

            if changes:
                self.runtime_repo.upsert_runtime_state(next_runtime, now)
                self.event_repo.append_event(
                    event_type="npc_state_changed",
                    location=state.current_location,
                    payload={"npc_id": state.id, "changes": changes},
                    created_at=now,
                )
