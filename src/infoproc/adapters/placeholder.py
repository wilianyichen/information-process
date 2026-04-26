from __future__ import annotations

from pathlib import Path

from infoproc.adapters.base import InputAdapter
from infoproc.models import InputKind


class _PlaceholderAdapter(InputAdapter):
    kind = InputKind.IMAGE
    label = "placeholder"

    def supports(self, path: Path) -> bool:
        return False

    def probe(self, path: Path) -> dict[str, str]:
        raise NotImplementedError(f"{self.label} adapter is reserved for a later version.")

    def normalize(self, path: Path, output_audio_path: Path) -> dict[str, str]:
        raise NotImplementedError(f"{self.label} adapter is reserved for a later version.")


class ImageInputAdapter(_PlaceholderAdapter):
    kind = InputKind.IMAGE
    label = "image"


class WebInputAdapter(_PlaceholderAdapter):
    kind = InputKind.WEB
    label = "web"
