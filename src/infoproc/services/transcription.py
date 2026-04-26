from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from infoproc.config import AppConfig


def _choose_device(preferred: str) -> str:
    if preferred != "auto":
        return preferred
    return "cuda" if shutil.which("nvidia-smi") else "cpu"


@dataclass(slots=True)
class TranscriptionService:
    config: AppConfig
    _faster_whisper_models: dict[tuple[str, str, str, str], Any] = field(default_factory=dict, init=False)
    _whisperx_models: dict[tuple[str, str, str, str], Any] = field(default_factory=dict, init=False)
    _align_models: dict[tuple[str, str], tuple[Any, Any]] = field(default_factory=dict, init=False)
    _diarize_models: dict[tuple[str, str], Any] = field(default_factory=dict, init=False)

    def transcribe(self, audio_path: Path, profile: str, diarize: bool) -> tuple[dict[str, Any], str]:
        if diarize:
            return self._transcribe_with_whisperx(audio_path, profile)
        return self._transcribe_with_faster_whisper(audio_path, profile)

    def prefetch_profile_model(self, profile: str) -> dict[str, Any]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is required to pre-download transcription models. Install it in the active Python environment."
            ) from exc

        del WhisperModel  # Imported only to validate dependency presence.
        device = _choose_device(self.config.transcription.device)
        compute_type = "float16" if device == "cuda" else "int8"
        model_name = self.config.transcription.model_for_profile(profile)
        download_root = str(self.config.transcription.model_cache_dir.expanduser())
        Path(download_root).mkdir(parents=True, exist_ok=True)
        self._load_faster_whisper_model(model_name, device, compute_type, download_root)
        return {
            "profile": profile,
            "model": model_name,
            "device": device,
            "compute_type": compute_type,
            "model_cache_dir": download_root,
        }

    def _transcribe_with_faster_whisper(self, audio_path: Path, profile: str) -> tuple[dict[str, Any], str]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is required for transcription. Install it in the active Python environment."
            ) from exc

        device = _choose_device(self.config.transcription.device)
        compute_type = "float16" if device == "cuda" else "int8"
        model_name = self.config.transcription.model_for_profile(profile)
        download_root = str(self.config.transcription.model_cache_dir)
        Path(download_root).mkdir(parents=True, exist_ok=True)
        model = self._load_faster_whisper_model(model_name, device, compute_type, download_root)
        segments, info = model.transcribe(str(audio_path), vad_filter=True)

        payload_segments = []
        lines: list[str] = []
        for segment in segments:
            item = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            }
            payload_segments.append(item)
            lines.append(item["text"])
        payload = {
            "engine": "faster-whisper",
            "model": model_name,
            "device": device,
            "language": getattr(info, "language", None),
            "duration": getattr(info, "duration", None),
            "segments": payload_segments,
        }
        return payload, "\n".join(lines).strip() + ("\n" if lines else "")

    def _load_faster_whisper_model(
        self,
        model_name: str,
        device: str,
        compute_type: str,
        download_root: str,
    ):
        from faster_whisper import WhisperModel

        key = (model_name, device, compute_type, download_root)
        cached = self._faster_whisper_models.get(key)
        if cached is not None:
            return cached

        try:
            model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                download_root=download_root,
                local_files_only=True,
            )
        except Exception as local_exc:
            try:
                model = WhisperModel(
                    model_name,
                    device=device,
                    compute_type=compute_type,
                    download_root=download_root,
                )
            except Exception as remote_exc:
                raise RuntimeError(
                    f"Failed to load local model cache for {model_name}, and remote download was unavailable: {remote_exc}"
                ) from local_exc
        self._faster_whisper_models[key] = model
        return model

    def _transcribe_with_whisperx(self, audio_path: Path, profile: str) -> tuple[dict[str, Any], str]:
        try:
            import torch
            import whisperx
            from whisperx.diarize import DiarizationPipeline
        except ImportError as exc:
            raise RuntimeError(
                "whisperx, torch, and diarization dependencies are required when --diarize is enabled."
            ) from exc

        hf_token = self.config.diarization.resolved_token()
        if not hf_token:
            raise RuntimeError(
                f"Diarization requested, but {self.config.diarization.hf_token_env} is not set."
            )
        self.config.diarization.hf_home.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(self.config.diarization.hf_home))

        device = _choose_device(self.config.transcription.device)
        compute_type = "float16" if device == "cuda" else "int8"
        model_name = self.config.transcription.model_for_profile(profile)
        audio = whisperx.load_audio(str(audio_path))
        model = self._load_whisperx_model(whisperx, model_name, device, compute_type)
        result = model.transcribe(audio, batch_size=16)

        align_model, metadata = self._load_align_model(whisperx, result["language"], device)
        aligned = whisperx.align(
            result["segments"],
            align_model,
            metadata,
            audio,
            device,
            return_char_alignments=False,
        )

        diarize_model = self._load_diarize_model(DiarizationPipeline, hf_token, device)
        diarize_segments = diarize_model(audio)
        assigned = whisperx.assign_word_speakers(diarize_segments, aligned)

        lines: list[str] = []
        for segment in assigned["segments"]:
            speaker = segment.get("speaker", "SPEAKER_00")
            text = segment["text"].strip()
            lines.append(f"{speaker}: {text}")

        payload = {
            "engine": "whisperx",
            "model": model_name,
            "device": device,
            "language": assigned.get("language"),
            "segments": assigned["segments"],
        }
        return payload, "\n".join(lines).strip() + ("\n" if lines else "")

    def _load_whisperx_model(self, whisperx_module: Any, model_name: str, device: str, compute_type: str):
        key = (model_name, device, compute_type, str(self.config.transcription.model_cache_dir))
        cached = self._whisperx_models.get(key)
        if cached is not None:
            return cached
        model = whisperx_module.load_model(
            model_name,
            device=device,
            compute_type=compute_type,
            download_root=str(self.config.transcription.model_cache_dir),
        )
        self._whisperx_models[key] = model
        return model

    def _load_align_model(self, whisperx_module: Any, language_code: str, device: str) -> tuple[Any, Any]:
        key = (language_code, device)
        cached = self._align_models.get(key)
        if cached is not None:
            return cached
        cached = whisperx_module.load_align_model(language_code=language_code, device=device)
        self._align_models[key] = cached
        return cached

    def _load_diarize_model(self, diarization_cls: Any, hf_token: str, device: str) -> Any:
        key = (hf_token, device)
        cached = self._diarize_models.get(key)
        if cached is not None:
            return cached
        cached = diarization_cls(
            model_name="pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
            device=device,
        )
        self._diarize_models[key] = cached
        return cached

    @staticmethod
    def write_outputs(raw_payload: dict[str, Any], full_text: str, raw_path: Path, full_text_path: Path) -> None:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        full_text_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        full_text_path.write_text(full_text, encoding="utf-8")
