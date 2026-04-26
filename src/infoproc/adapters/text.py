from __future__ import annotations

from pathlib import Path
from typing import Any

from infoproc.adapters.base import InputAdapter
from infoproc.models import InputKind


TEXT_EXTENSIONS = {".txt", ".md"}


class TextInputAdapter(InputAdapter):
    kind = InputKind.TEXT

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in TEXT_EXTENSIONS

    def probe(self, path: Path) -> dict[str, Any]:
        content = path.read_text(encoding="utf-8")
        return {
            "input_path": str(path),
            "detected_kind": self.kind.value,
            "node_kind": "markdown" if path.suffix.lower() == ".md" else "plain_text",
            "extension": path.suffix.lower(),
            "characters": len(content),
            "lines": len(content.splitlines()),
        }

    def normalize(self, path: Path, output_audio_path: Path) -> dict[str, Any]:
        return {
            "skipped": True,
            "reason": "text input does not require audio normalization",
        }
