from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActionPlan:
    actions: list[dict[str, Any]]


@dataclass(frozen=True)
class ActionResult:
    actions: list[dict[str, Any]]
    executed: bool = False
    effects: dict[str, Any] = field(default_factory=dict)
