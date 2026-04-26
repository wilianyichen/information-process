from __future__ import annotations

import os
import shutil

from infoproc.config import AppConfig
from infoproc.models import DiscoveredInput, EnvironmentSnapshot, SchedulerPlan
from infoproc.utils import get_available_memory_bytes


def build_environment_snapshot(config: AppConfig) -> EnvironmentSnapshot:
    office_converter = _resolve_office_converter(config.document.office_converter)
    return EnvironmentSnapshot(
        cpu_count=os.cpu_count() or 4,
        available_memory_bytes=get_available_memory_bytes(),
        has_cuda=_has_cuda_runtime(config),
        ffmpeg_available=shutil.which("ffmpeg") is not None,
        ffprobe_available=shutil.which("ffprobe") is not None,
        office_converter=office_converter,
        pdftotext=shutil.which("pdftotext"),
    )


def choose_batch_execution_plan(
    config: AppConfig,
    environment: EnvironmentSnapshot,
    inputs: list[DiscoveredInput],
) -> SchedulerPlan:
    if config.scheduler.mode == "serial":
        return SchedulerPlan(
            mode="serial",
            document_workers=1,
            transcribe_workers=1,
            llm_workers=1,
            stream_llm=False,
            reason="scheduler.mode=serial",
        )

    cpu_count = max(1, environment.cpu_count)
    media_count = sum(1 for item in inputs if item.kind.value in {"audio", "video"})
    has_docs = any(item.kind.value in {"document", "presentation", "text"} for item in inputs)
    low_memory = environment.available_memory_bytes is not None and environment.available_memory_bytes < 4 * 1024**3

    transcribe_workers = 1 if environment.has_cuda else min(max(1, cpu_count // 2), config.scheduler.transcribe_workers)
    document_workers = min(max(1, cpu_count - transcribe_workers), max(1, config.scheduler.document_workers))
    llm_workers = min(max(1, cpu_count // 2), max(1, config.scheduler.llm_workers))

    if media_count == 0:
        transcribe_workers = 1
    if not has_docs:
        document_workers = 1
    if low_memory:
        document_workers = 1
        llm_workers = 1

    reason_parts = []
    if environment.has_cuda:
        reason_parts.append("CUDA detected, keep transcription nearly serialized")
    else:
        reason_parts.append("CPU-only or forced CPU transcription")
    if low_memory:
        reason_parts.append("available memory is low, reduce document/LLM parallelism")
    if has_docs:
        reason_parts.append("documents/text can overlap with media transcription")
    return SchedulerPlan(
        mode="auto",
        document_workers=max(1, document_workers),
        transcribe_workers=max(1, transcribe_workers),
        llm_workers=max(1, llm_workers),
        stream_llm=True,
        reason="; ".join(reason_parts),
    )


def sort_inputs_for_processing(inputs: list[DiscoveredInput]) -> list[DiscoveredInput]:
    def sort_key(item: DiscoveredInput) -> tuple[int, float, int, str]:
        if item.kind.value in {"audio", "video"}:
            return (0, -(item.estimates.get("duration_seconds") or 0.0), 0, item.relative_key)
        if item.kind.value in {"document", "presentation"}:
            return (1, float(item.estimates.get("characters") or 0), int(item.estimates.get("page_count") or item.estimates.get("slide_count") or 0), item.relative_key)
        return (2, float(item.estimates.get("characters") or 0), int(item.estimates.get("lines") or 0), item.relative_key)

    return sorted(inputs, key=sort_key)


def _has_cuda_runtime(config: AppConfig) -> bool:
    if config.transcription.device == "cpu":
        return False
    return shutil.which("nvidia-smi") is not None


def _resolve_office_converter(configured: str) -> str | None:
    if os.path.exists(configured):
        return configured
    return shutil.which(configured) or shutil.which("libreoffice")
