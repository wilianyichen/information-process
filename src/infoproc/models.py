from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_run_name(input_path: Path) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}__{input_path.stem or input_path.name}"


class DistillMode(str, Enum):
    BOTH = "both"
    DISTILL = "distill"
    RANK = "rank"


class ProcessingStage(str, Enum):
    FULL = "full"
    PROBE = "probe"
    NORMALIZE = "normalize"
    TRANSCRIBE = "transcribe"
    CLEAN = "clean"
    DISTILL = "distill"
    RANK = "rank"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class InputKind(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"
    TEXT = "text"
    DOCUMENT = "document"
    PRESENTATION = "presentation"
    IMAGE = "image"
    WEB = "web"


@dataclass(slots=True)
class RunRequest:
    input_path: Path
    storage_root: Path
    profile: str = "balanced"
    diarize: bool = False
    distill_mode: DistillMode = DistillMode.BOTH
    stage: ProcessingStage = ProcessingStage.FULL
    pattern: str = "*"
    recursive: bool = False
    run_name: str | None = None
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def resolved_run_name(self) -> str:
        return self.run_name or default_run_name(self.input_path)


@dataclass(slots=True)
class EnvironmentSnapshot:
    cpu_count: int
    available_memory_bytes: int | None
    has_cuda: bool
    ffmpeg_available: bool
    ffprobe_available: bool
    office_converter: str | None
    pdftotext: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_count": self.cpu_count,
            "available_memory_bytes": self.available_memory_bytes,
            "has_cuda": self.has_cuda,
            "ffmpeg_available": self.ffmpeg_available,
            "ffprobe_available": self.ffprobe_available,
            "office_converter": self.office_converter,
            "pdftotext": self.pdftotext,
        }


@dataclass(slots=True)
class SchedulerPlan:
    mode: str
    document_workers: int
    transcribe_workers: int
    llm_workers: int
    stream_llm: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "document_workers": self.document_workers,
            "transcribe_workers": self.transcribe_workers,
            "llm_workers": self.llm_workers,
            "stream_llm": self.stream_llm,
            "reason": self.reason,
        }


@dataclass(slots=True)
class DiscoveredInput:
    input_path: Path
    relative_path: Path
    kind: InputKind
    source_node: str
    probe_data: dict[str, Any]
    estimates: dict[str, Any]

    @property
    def relative_key(self) -> str:
        return self.relative_path.as_posix()


@dataclass(slots=True)
class ProcessedFile:
    input_path: Path
    relative_path: Path
    status: str
    error: str | None = None
    artifacts: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RunResult:
    run_dir: Path
    run_manifest_path: Path
    files: list[ProcessedFile]


@dataclass(slots=True)
class RunLayout:
    run_dir: Path

    SOURCE_LAYER: str = "00_source"
    PROBE_LAYER: str = "01_probe"
    NORMALIZED_LAYER: str = "02_normalized"
    RAW_TEXT_LAYER: str = "03_text_raw"
    CLEAN_TEXT_LAYER: str = "04_text_clean"
    FINAL_LAYER: str = "05_final"
    MANIFEST_LAYER: str = "_manifests"
    LOG_LAYER: str = "_logs"

    @property
    def manifests_dir(self) -> Path:
        return self.run_dir / self.MANIFEST_LAYER

    @property
    def logs_dir(self) -> Path:
        return self.run_dir / self.LOG_LAYER

    @property
    def files_log_dir(self) -> Path:
        return self.logs_dir / "files"

    @property
    def run_manifest(self) -> Path:
        return self.manifests_dir / "run_manifest.json"

    @property
    def file_index(self) -> Path:
        return self.manifests_dir / "file_index.json"

    @property
    def scheduler_plan(self) -> Path:
        return self.manifests_dir / "scheduler_plan.json"

    @property
    def environment_snapshot(self) -> Path:
        return self.manifests_dir / "environment_snapshot.json"

    @property
    def run_log(self) -> Path:
        return self.logs_dir / "run.log"

    @property
    def summary_dir(self) -> Path:
        return self.run_dir / self.FINAL_LAYER / "_summaries"

    @property
    def distill_rank_summary(self) -> Path:
        return self.summary_dir / "蒸馏与降秩汇总.md"

    @property
    def clean_summary(self) -> Path:
        return self.summary_dir / "clean汇总.md"

    def ensure_dirs(self) -> None:
        for path in (
            self.run_dir,
            self.manifests_dir,
            self.logs_dir,
            self.files_log_dir,
            self.summary_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def source_path(self, node_name: str, relative_path: Path) -> Path:
        return self.run_dir / self.SOURCE_LAYER / node_name / relative_path

    def probe_path(self, relative_path: Path) -> Path:
        return self.run_dir / self.PROBE_LAYER / "metadata__json" / relative_path.with_suffix(".json")

    def normalized_path(self, node_name: str, relative_path: Path, suffix: str) -> Path:
        return self.run_dir / self.NORMALIZED_LAYER / node_name / relative_path.with_suffix(suffix)

    def raw_text_path(self, node_name: str, relative_path: Path, suffix: str) -> Path:
        return self.run_dir / self.RAW_TEXT_LAYER / node_name / relative_path.with_suffix(suffix)

    def clean_text_path(self, relative_path: Path) -> Path:
        return self.run_dir / self.CLEAN_TEXT_LAYER / "clean_text__txt" / relative_path.with_suffix(".txt")

    def final_path(self, node_name: str, relative_path: Path) -> Path:
        return self.run_dir / self.FINAL_LAYER / node_name / relative_path.with_suffix(".md")

    def file_log_path(self, relative_path: Path) -> Path:
        return self.files_log_dir / Path(*relative_path.parts[:-1], relative_path.name + ".log")

    def relative_output_path(self, path: Path) -> str:
        return path.relative_to(self.run_dir).as_posix()


def default_run_manifest(layout: RunLayout, request: RunRequest) -> dict[str, Any]:
    return {
        "run_id": request.job_id,
        "status": JobStatus.QUEUED.value,
        "input": {
            "path": str(request.input_path),
            "profile": request.profile,
            "diarize": request.diarize,
            "distill_mode": request.distill_mode.value,
            "stage": request.stage.value,
            "pattern": request.pattern,
            "recursive": request.recursive,
            "run_name": request.resolved_run_name(),
        },
        "run_dir": str(layout.run_dir),
        "files": {},
        "errors": [],
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
