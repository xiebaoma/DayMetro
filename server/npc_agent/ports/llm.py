from __future__ import annotations

from typing import Protocol


class LLMClientPort(Protocol):
    def generate(self, prompt: str) -> str | None: ...
