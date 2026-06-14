from __future__ import annotations

from server.logging_service import get_logger
from server.npc_agent.domain.events import WorldEvent
from server.npc_agent.ports.memory import EventMemoryMapperPort
from server.npc_agent.ports.repositories import RelationRepository, SaveStateRepository
from server.npc_agent.services.event_service import EventService
from server.npc_agent.services.memory_system import MemorySystem
from server.npc_agent.services.npc_state_service import NpcStateService
from server.npc_agent.services.perception_service import PerceptionService

logger = get_logger("daymetro.event_pipeline")


class EventPipeline:
    def __init__(
        self,
        *,
        event_service: EventService,
        save_repo: SaveStateRepository,
        perception_service: PerceptionService,
        memory_system: MemorySystem,
        relation_repo: RelationRepository,
        npc_state_service: NpcStateService,
        event_memory_mapper: EventMemoryMapperPort | None = None,
    ):
        self.event_service = event_service
        self.save_repo = save_repo
        self.perception_service = perception_service
        self.memory_system = memory_system
        self.relation_repo = relation_repo
        self.npc_state_service = npc_state_service
        self.event_memory_mapper = event_memory_mapper

    def record_event(
        self,
        *,
        event_type: str,
        location: str,
        payload: dict,
        game_time: str | None,
    ) -> dict:
        result = self.event_service.log_event(event_type, location, payload, game_time)
        event = WorldEvent(
            id=result["event_id"],
            event_type=event_type,
            location=location,
            payload=payload,
            created_at=result["created_at"],
            game_time=game_time,
        )
        self.after_event_logged(event)
        if event_type == "tick":
            self.sync_npc_runtime()
        return result

    def after_event_logged(self, event: WorldEvent) -> None:
        if event.game_time:
            self.save_repo.update_save_state(event.game_time, event.location, event.created_at)
            self.perception_service.distribute_event_perception(
                event_id=event.id or 0,
                event_type=event.event_type,
                location=event.location,
                payload=event.payload,
                game_time=event.game_time,
                observed_at=event.created_at,
            )
        self._write_mapped_memory(event)

    def sync_npc_runtime(self) -> None:
        save_state = self.save_repo.get_save_state()
        if save_state is None:
            return
        states = self.npc_state_service.compute_npc_states(save_state["game_time"])
        self.npc_state_service.sync_runtime_state(states)

    def _write_mapped_memory(self, event: WorldEvent) -> None:
        if self.event_memory_mapper is None:
            return
        npc_id = event.payload.get("npc_id") or event.payload.get("target_npc_id")
        if not npc_id:
            return
        memory = self.event_memory_mapper.map_event(event.event_type, event.location, event.payload)
        if memory is None:
            return

        self.memory_system.remember_event(
            npc_id=str(npc_id),
            content=memory.content,
            memory_type=memory.memory_type,
            importance=memory.importance,
            related_event_id=event.id or 0,
            tags=memory.tags,
            metadata={"event_type": event.event_type, "location": event.location},
        )
        self.relation_repo.apply_delta(str(npc_id), **memory.relation_delta)
        logger.info(
            "memory_generated_from_event event_id=%s npc_id=%s memory_type=%s",
            event.id,
            npc_id,
            memory.memory_type,
        )
