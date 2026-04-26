from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from infoproc.adapters.base import InputAdapter
from infoproc.models import InputKind
from infoproc.utils import run_command, which_or_raise


MEDIA_EXTENSIONS = {
    ".mp3": InputKind.AUDIO,
    ".wav": InputKind.AUDIO,
    ".m4a": InputKind.AUDIO,
    ".flac": InputKind.AUDIO,
    ".aac": InputKind.AUDIO,
    ".ogg": InputKind.AUDIO,
    ".wma": InputKind.AUDIO,
    ".mp4": InputKind.VIDEO,
    ".mov": InputKind.VIDEO,
    ".mkv": InputKind.VIDEO,
    ".avi": InputKind.VIDEO,
    ".webm": InputKind.VIDEO,
    ".wmv": InputKind.VIDEO,
    ".m4v": InputKind.VIDEO,
}


class MediaInputAdapter(InputAdapter):
    kind = InputKind.AUDIO

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in MEDIA_EXTENSIONS

    def probe(self, path: Path) -> dict[str, Any]:
        which_or_raise("ffprobe")
        result = run_command(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
        payload = json.loads(result.stdout or "{}")
        detected_kind = MEDIA_EXTENSIONS[path.suffix.lower()]
        format_info = payload.get("format", {})
        streams = payload.get("streams", [])
        payload["detected_kind"] = detected_kind.value
        payload["input_path"] = str(path)
        payload["extension"] = path.suffix.lower()
        payload["duration_seconds"] = _safe_float(format_info.get("duration"))
        payload["bit_rate"] = _safe_int(format_info.get("bit_rate"))
        payload["stream_count"] = len(streams)
        payload["is_video"] = detected_kind == InputKind.VIDEO
        return payload

    def normalize(self, path: Path, output_audio_path: Path) -> dict[str, Any]:
        which_or_raise("ffmpeg")
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        result = run_command(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(path),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-vn",
                str(output_audio_path),
            ],
            timeout=1800,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg normalization failed: {result.stderr.strip()}")
        return {
            "normalized_audio": str(output_audio_path),
            "sample_rate": 16000,
            "channels": 1,
        }


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
