from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from infoproc.models import InputKind


class InputAdapter(ABC):
    kind: InputKind

    @abstractmethod
    def supports(self, path: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def probe(self, path: Path) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, path: Path, output_audio_path: Path) -> dict[str, Any]:
        raise NotImplementedError
