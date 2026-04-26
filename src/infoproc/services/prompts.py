from __future__ import annotations

from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=8)
def load_prompt(name: str) -> str:
    return resources.files("infoproc.prompts").joinpath(name).read_text(encoding="utf-8")
