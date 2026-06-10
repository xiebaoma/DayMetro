# DayMetro Backend Architecture (Decoupled)

## Layering

- API layer: `server/main.py`
- Application services: `server/npc_agent/services/`
- Domain models: `server/npc_agent/domain/models.py`
- Ports/contracts: `server/npc_agent/ports/repositories.py`
- Adapters:
  - Persistence: `server/adapters/persistence/sqlite_repositories.py`
  - Content: `server/adapters/content/`
  - DayMetro rules: `server/adapters/daymetro/`
  - LLM: `server/adapters/llm/deepseek_client.py` (DeepSeek only)

## Responsibility Split

- `main.py` only handles HTTP validation, error mapping, and service orchestration.
- `InteractionService` owns dialogue use-cases (options, choice effects, relation/mood/memory/event updates).
- `PerceptionService` owns bounded world-awareness (seen/heard/experienced/told), preventing omniscient NPC behavior.
- `NpcStateService` separates:
  - `compute_npc_states(game_time)` (pure computation)
  - `sync_runtime_state(states)` (state persistence + change event emission)
- `WorldService` provides read-model snapshots for `/world/state`.
- `EventService` handles event log writes and save-state updates.
- `EventService` + `PerceptionService` propagate local events to same-location NPCs, and cross-location knowledge only when explicitly shared.

## DayMetro-Specific vs Generic

- Generic core:
  - `npc_agent/domain`, `npc_agent/ports`, `npc_agent/services`
- DayMetro-specific adapters:
  - Dialogue effects/options: `adapters/daymetro/dialogue_effects.py`
  - Time points/labels: `adapters/daymetro/time_points.py`
  - Response serializer shape: `adapters/daymetro/serializers.py`

This keeps the core reusable for non-game NPC Agent scenarios.

## Runtime Wiring

- `server/npc_agent/services/factory.py` builds repository adapters and service instances from a single SQLite connection.
- Each route opens one DB connection, builds services, executes use-cases, then commits when needed.

## Compatibility Notes

- Existing API routes and response fields are preserved.
- Added inspection route: `/npc/perception` (for querying each NPC's local knowledge snapshot).
- Legacy modules (`server/memory.py`, `server/scheduler.py`, `server/npc_agent.py`) remain as compatibility wrappers over the new layered implementation.
