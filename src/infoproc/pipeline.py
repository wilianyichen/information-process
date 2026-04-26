from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
from pathlib import Path
import threading
from typing import Callable, Iterable

from infoproc.adapters import DocumentInputAdapter, MediaInputAdapter, TextInputAdapter
from infoproc.aggregate import generate_final_summaries
from infoproc.config import AppConfig
from infoproc.execution import build_environment_snapshot, choose_batch_execution_plan, sort_inputs_for_processing
from infoproc.models import (
    DiscoveredInput,
    DistillMode,
    InputKind,
    JobStatus,
    ProcessedFile,
    ProcessingStage,
    RunLayout,
    RunRequest,
    RunResult,
    SchedulerPlan,
    default_run_manifest,
    utc_now,
)
from infoproc.services import DocumentExtractionService, DistillService, RankService, TranscriptionService, clean_text
from infoproc.utils import (
    append_log,
    file_signature,
    fingerprint_from_mapping,
    link_or_copy,
    read_json,
    sha256_text,
    write_json,
    write_text,
)


class JobCanceledError(RuntimeError):
    pass


@dataclass(slots=True)
class Pipeline:
    config: AppConfig
    log_callback: Callable[[str], None] | None = None
    adapters: tuple = field(init=False)
    transcription: TranscriptionService = field(init=False)
    documents: DocumentExtractionService = field(init=False)
    distill: DistillService = field(init=False)
    rank: RankService = field(init=False)
    _manifest_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _manifest: dict = field(default_factory=dict, init=False)
    _layout: RunLayout | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.adapters = (MediaInputAdapter(), TextInputAdapter(), DocumentInputAdapter())
        self.transcription = TranscriptionService(self.config)
        self.documents = DocumentExtractionService(self.config)
        self.distill = DistillService(self.config.api)
        self.rank = RankService(self.config.api)

    def process(self, request: RunRequest, should_cancel: Callable[[], bool] | None = None) -> RunResult:
        should_cancel = should_cancel or (lambda: False)
        discovered_paths = list(discover_inputs(request.input_path, request.pattern, request.recursive))
        if not discovered_paths:
            raise FileNotFoundError(f"No supported inputs found under {request.input_path} matching {request.pattern}")

        run_dir = request.storage_root / self.config.storage.runs_dir_name / request.resolved_run_name()
        layout = RunLayout(run_dir)
        layout.ensure_dirs()
        self._layout = layout
        self._manifest = read_json(layout.run_manifest, default_run_manifest(layout, request))
        self._manifest["status"] = JobStatus.RUNNING.value
        self._manifest["updated_at"] = utc_now()
        self._sync_manifest()

        environment = build_environment_snapshot(self.config)
        write_json(layout.environment_snapshot, environment.to_dict())

        discovered = self._discover_inputs(request, discovered_paths)
        discovered = sort_inputs_for_processing(discovered)
        write_json(layout.file_index, [_discovered_to_dict(item) for item in discovered])

        plan = choose_batch_execution_plan(self.config, environment, discovered)
        write_json(layout.scheduler_plan, plan.to_dict())
        self._log(None, f"[plan] {plan.reason}")

        for item in discovered:
            self._ensure_file_entry(item)

        prep_executor = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, plan.document_workers))
        media_executor = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, plan.transcribe_workers))
        llm_executor = (
            concurrent.futures.ThreadPoolExecutor(max_workers=max(1, plan.llm_workers))
            if _should_run_final_stage(request)
            else None
        )

        prep_futures: list[tuple[DiscoveredInput, concurrent.futures.Future[str | None]]] = []
        llm_futures: list[concurrent.futures.Future[None]] = []
        try:
            for item in discovered:
                self._check_cancel(should_cancel)
                executor = media_executor if item.kind in (InputKind.AUDIO, InputKind.VIDEO) else prep_executor
                prep_futures.append(
                    (
                        item,
                        executor.submit(self._prepare_until_clean, request, item, should_cancel),
                    )
                )

            for item, future in prep_futures:
                clean_content = future.result()
                if clean_content is None or not _should_run_final_stage(request):
                    continue
                if llm_executor is None:
                    self._run_final_outputs(request, item, clean_content, should_cancel)
                else:
                    llm_futures.append(
                        llm_executor.submit(self._run_final_outputs, request, item, clean_content, should_cancel)
                    )

            for future in concurrent.futures.as_completed(llm_futures):
                future.result()
        finally:
            prep_executor.shutdown(wait=True)
            media_executor.shutdown(wait=True)
            if llm_executor is not None:
                llm_executor.shutdown(wait=True)

        outputs = generate_final_summaries(layout.run_dir)
        self._log(None, f"[aggregate] wrote {outputs.distill_rank_summary}")
        self._log(None, f"[aggregate] wrote {outputs.clean_summary}")

        files = self._finalize_run(discovered)
        return RunResult(run_dir=layout.run_dir, run_manifest_path=layout.run_manifest, files=files)

    def process_batch(self, request: RunRequest, should_cancel: Callable[[], bool] | None = None) -> list[ProcessedFile]:
        return self.process(request, should_cancel).files

    def process_file(
        self,
        request: RunRequest,
        input_path: Path,
        relative_parent: Path | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> ProcessedFile:
        del input_path, relative_parent
        result = self.process(request, should_cancel)
        return result.files[0]

    def _discover_inputs(self, request: RunRequest, inputs: list[Path]) -> list[DiscoveredInput]:
        discovered: list[DiscoveredInput] = []
        for input_path in inputs:
            adapter = self._resolve_adapter(input_path)
            relative_path = input_path.relative_to(request.input_path) if request.input_path.is_dir() else Path(input_path.name)
            probe_data = adapter.probe(input_path)
            kind = _detected_input_kind(probe_data.get("detected_kind"), input_path)
            source_node = _source_node_name(input_path, kind)
            estimates = _estimate_resources(kind, probe_data, input_path)
            discovered.append(
                DiscoveredInput(
                    input_path=input_path,
                    relative_path=relative_path,
                    kind=kind,
                    source_node=source_node,
                    probe_data=probe_data,
                    estimates=estimates,
                )
            )
        return discovered

    def _prepare_until_clean(
        self,
        request: RunRequest,
        item: DiscoveredInput,
        should_cancel: Callable[[], bool],
    ) -> str | None:
        try:
            self._check_cancel(should_cancel)
            self._run_source_stage(item)
            self._run_probe_stage(item)
            if request.stage == ProcessingStage.PROBE:
                self._set_file_status(item, JobStatus.COMPLETED.value)
                return None
            if item.kind in (InputKind.AUDIO, InputKind.VIDEO):
                clean_content = self._prepare_media_file(request, item, should_cancel)
            elif item.kind in (InputKind.DOCUMENT, InputKind.PRESENTATION):
                clean_content = self._prepare_document_file(request, item, should_cancel)
            else:
                clean_content = self._prepare_text_file(request, item)

            if request.stage in (
                ProcessingStage.NORMALIZE,
                ProcessingStage.TRANSCRIBE,
                ProcessingStage.CLEAN,
            ):
                self._set_file_status(item, JobStatus.COMPLETED.value)
                return None

            self._set_file_status(item, JobStatus.RUNNING.value)
            return clean_content
        except JobCanceledError as exc:
            self._fail_file(item, JobStatus.CANCELED.value, str(exc))
            return None
        except Exception as exc:
            self._fail_file(item, JobStatus.FAILED.value, str(exc))
            return None

    def _prepare_text_file(self, request: RunRequest, item: DiscoveredInput) -> str | None:
        layout = self._require_layout()
        raw_text_path = layout.raw_text_path("plain_text__txt", item.relative_path, ".txt")
        raw_text = self._run_raw_text_stage(
            item,
            raw_text_path,
            read_source=lambda: item.input_path.read_text(encoding="utf-8"),
            fingerprint=fingerprint_from_mapping({"stage": "raw_text", "source": file_signature(item.input_path)}),
        )
        if request.stage == ProcessingStage.NORMALIZE:
            self._mark_stage_skipped(item, "normalize", "text input does not require normalization")
            return None
        if request.stage == ProcessingStage.TRANSCRIBE:
            return None
        return self._run_clean_stage(item, raw_text, raw_text_path)

    def _prepare_document_file(
        self,
        request: RunRequest,
        item: DiscoveredInput,
        should_cancel: Callable[[], bool],
    ) -> str | None:
        layout = self._require_layout()
        self._check_cancel(should_cancel)
        extraction_source = item.input_path
        if item.input_path.suffix.lower() in {".doc", ".ppt"}:
            normalized_node = "presentation__pptx" if item.kind == InputKind.PRESENTATION else "document__docx"
            normalized_suffix = ".pptx" if item.kind == InputKind.PRESENTATION else ".docx"
            normalized_path = layout.normalized_path(normalized_node, item.relative_path, normalized_suffix)
            normalize_fingerprint = fingerprint_from_mapping(
                {
                    "stage": "normalize",
                    "source": file_signature(item.input_path),
                    "office_converter": self.config.document.office_converter,
                }
            )
            cached = self._stage_payload(item, "normalize")
            if cached.get("fingerprint") == normalize_fingerprint and normalized_path.exists():
                self._log(item.relative_path, "[cache] normalize")
            else:
                payload = self.documents.convert_legacy_office(item.input_path, normalized_path)
                self._record_stage(
                    item,
                    "normalize",
                    {
                        "status": "completed",
                        "fingerprint": normalize_fingerprint,
                        "artifact": layout.relative_output_path(normalized_path),
                        "details": payload,
                        "updated_at": utc_now(),
                    },
                    artifacts={"normalized_document": normalized_path},
                )
                self._log(item.relative_path, "[run] normalize")
            extraction_source = normalized_path
        else:
            self._mark_stage_skipped(item, "normalize", "document format does not require legacy conversion")

        if request.stage == ProcessingStage.NORMALIZE:
            return None

        self._check_cancel(should_cancel)
        raw_text_path = layout.raw_text_path("plain_text__txt", item.relative_path, ".txt")
        extract_fingerprint = fingerprint_from_mapping(
            {
                "stage": "extract_text",
                "source": file_signature(extraction_source),
                "pdf_engine": self.config.document.pdf_engine,
            }
        )
        cached = self._stage_payload(item, "extract_text")
        if cached.get("fingerprint") == extract_fingerprint and raw_text_path.exists():
            self._log(item.relative_path, "[cache] extract_text")
            raw_text = raw_text_path.read_text(encoding="utf-8")
        else:
            payload, raw_text = self.documents.extract_text(extraction_source)
            write_text(raw_text_path, raw_text)
            self._record_stage(
                item,
                "extract_text",
                {
                    "status": "completed",
                    "fingerprint": extract_fingerprint,
                    "artifact": layout.relative_output_path(raw_text_path),
                    "details": payload,
                    "updated_at": utc_now(),
                },
                artifacts={"raw_text": raw_text_path},
            )
            self._log(item.relative_path, "[run] extract_text")

        if request.stage == ProcessingStage.TRANSCRIBE:
            return None
        return self._run_clean_stage(item, raw_text, raw_text_path)

    def _prepare_media_file(
        self,
        request: RunRequest,
        item: DiscoveredInput,
        should_cancel: Callable[[], bool],
    ) -> str | None:
        layout = self._require_layout()
        self._check_cancel(should_cancel)
        normalized_path = layout.normalized_path("audio__wav", item.relative_path, ".wav")
        normalize_fingerprint = fingerprint_from_mapping(
            {
                "stage": "normalize",
                "source": file_signature(item.input_path),
                "kind": item.kind.value,
            }
        )
        cached = self._stage_payload(item, "normalize")
        if cached.get("fingerprint") == normalize_fingerprint and normalized_path.exists():
            self._log(item.relative_path, "[cache] normalize")
        else:
            adapter = self._resolve_adapter(item.input_path)
            payload = adapter.normalize(item.input_path, normalized_path)
            self._record_stage(
                item,
                "normalize",
                {
                    "status": "completed",
                    "fingerprint": normalize_fingerprint,
                    "artifact": layout.relative_output_path(normalized_path),
                    "details": payload,
                    "updated_at": utc_now(),
                },
                artifacts={"normalized_audio": normalized_path},
            )
            self._log(item.relative_path, "[run] normalize")

        if request.stage == ProcessingStage.NORMALIZE:
            return None

        self._check_cancel(should_cancel)
        raw_json_path = layout.raw_text_path("transcript__json", item.relative_path, ".json")
        raw_text_path = layout.raw_text_path("plain_text__txt", item.relative_path, ".txt")
        transcribe_fingerprint = fingerprint_from_mapping(
            {
                "stage": "transcribe",
                "source": file_signature(normalized_path),
                "profile": request.profile,
                "diarize": request.diarize,
            }
        )
        cached = self._stage_payload(item, "transcribe")
        if (
            cached.get("fingerprint") == transcribe_fingerprint
            and raw_json_path.exists()
            and raw_text_path.exists()
        ):
            self._log(item.relative_path, "[cache] transcribe")
            raw_text = raw_text_path.read_text(encoding="utf-8")
        else:
            raw_payload, raw_text = self.transcription.transcribe(normalized_path, request.profile, request.diarize)
            self.transcription.write_outputs(raw_payload, raw_text, raw_json_path, raw_text_path)
            self._record_stage(
                item,
                "transcribe",
                {
                    "status": "completed",
                    "fingerprint": transcribe_fingerprint,
                    "artifacts": [
                        layout.relative_output_path(raw_json_path),
                        layout.relative_output_path(raw_text_path),
                    ],
                    "updated_at": utc_now(),
                },
                artifacts={"transcript_json": raw_json_path, "raw_text": raw_text_path},
            )
            self._log(item.relative_path, "[run] transcribe")

        if request.stage == ProcessingStage.TRANSCRIBE:
            return None
        return self._run_clean_stage(item, raw_text, raw_text_path)

    def _run_final_outputs(
        self,
        request: RunRequest,
        item: DiscoveredInput,
        clean_content: str,
        should_cancel: Callable[[], bool],
    ) -> None:
        try:
            layout = self._require_layout()
            requested_modes = _requested_distill_modes(request)
            content_fp = sha256_text(clean_content)
            if DistillMode.DISTILL in requested_modes:
                self._check_cancel(should_cancel)
                distill_path = layout.final_path("distill__md", item.relative_path)
                distill_path.parent.mkdir(parents=True, exist_ok=True)
                fingerprint = fingerprint_from_mapping(
                    {
                        "stage": "distill",
                        "content_sha": content_fp,
                        "base_url": self.config.api.base_url,
                        "model": self.config.api.model,
                    }
                )
                cached = self._stage_payload(item, "distill")
                if cached.get("fingerprint") == fingerprint and distill_path.exists():
                    self._log(item.relative_path, "[cache] distill")
                else:
                    self.distill.write(clean_content, item.relative_path.stem, distill_path)
                    self._record_stage(
                        item,
                        "distill",
                        {
                            "status": "completed",
                            "fingerprint": fingerprint,
                            "artifact": layout.relative_output_path(distill_path),
                            "updated_at": utc_now(),
                        },
                        artifacts={"distill_markdown": distill_path},
                    )
                    self._log(item.relative_path, "[run] distill")

            if DistillMode.RANK in requested_modes:
                self._check_cancel(should_cancel)
                rank_path = layout.final_path("rank__md", item.relative_path)
                rank_path.parent.mkdir(parents=True, exist_ok=True)
                fingerprint = fingerprint_from_mapping(
                    {
                        "stage": "rank",
                        "content_sha": content_fp,
                        "base_url": self.config.api.base_url,
                        "model": self.config.api.model,
                    }
                )
                cached = self._stage_payload(item, "rank")
                if cached.get("fingerprint") == fingerprint and rank_path.exists():
                    self._log(item.relative_path, "[cache] rank")
                else:
                    self.rank.write(clean_content, item.relative_path.stem, rank_path)
                    self._record_stage(
                        item,
                        "rank",
                        {
                            "status": "completed",
                            "fingerprint": fingerprint,
                            "artifact": layout.relative_output_path(rank_path),
                            "updated_at": utc_now(),
                        },
                        artifacts={"rank_markdown": rank_path},
                    )
                    self._log(item.relative_path, "[run] rank")
            self._set_file_status(item, JobStatus.COMPLETED.value)
        except JobCanceledError as exc:
            self._fail_file(item, JobStatus.CANCELED.value, str(exc))
        except Exception as exc:
            self._fail_file(item, JobStatus.FAILED.value, str(exc))

    def _run_source_stage(self, item: DiscoveredInput) -> None:
        layout = self._require_layout()
        source_path = layout.source_path(item.source_node, item.relative_path)
        fingerprint = fingerprint_from_mapping(
            {
                "stage": "source",
                "source": file_signature(item.input_path),
                "node": item.source_node,
            }
        )
        cached = self._stage_payload(item, "source")
        if cached.get("fingerprint") == fingerprint and source_path.exists():
            self._log(item.relative_path, "[cache] source")
            return
        strategy = link_or_copy(item.input_path, source_path)
        self._record_stage(
            item,
            "source",
            {
                "status": "completed",
                "fingerprint": fingerprint,
                "artifact": layout.relative_output_path(source_path),
                "details": {"strategy": strategy},
                "updated_at": utc_now(),
            },
            artifacts={"source": source_path},
        )
        self._log(item.relative_path, "[run] source")

    def _run_probe_stage(self, item: DiscoveredInput) -> None:
        layout = self._require_layout()
        probe_path = layout.probe_path(item.relative_path)
        fingerprint = fingerprint_from_mapping({"stage": "probe", "source": file_signature(item.input_path)})
        cached = self._stage_payload(item, "probe")
        if cached.get("fingerprint") == fingerprint and probe_path.exists():
            self._log(item.relative_path, "[cache] probe")
            return
        write_json(probe_path, item.probe_data)
        self._record_stage(
            item,
            "probe",
            {
                "status": "completed",
                "fingerprint": fingerprint,
                "artifact": layout.relative_output_path(probe_path),
                "updated_at": utc_now(),
            },
            artifacts={"probe": probe_path},
        )
        self._log(item.relative_path, "[run] probe")

    def _run_raw_text_stage(
        self,
        item: DiscoveredInput,
        output_path: Path,
        read_source: Callable[[], str],
        fingerprint: str,
    ) -> str:
        cached = self._stage_payload(item, "raw_text")
        if cached.get("fingerprint") == fingerprint and output_path.exists():
            self._log(item.relative_path, "[cache] raw_text")
            return output_path.read_text(encoding="utf-8")
        raw_text = read_source()
        write_text(output_path, raw_text)
        self._record_stage(
            item,
            "raw_text",
            {
                "status": "completed",
                "fingerprint": fingerprint,
                "artifact": self._require_layout().relative_output_path(output_path),
                "updated_at": utc_now(),
            },
            artifacts={"raw_text": output_path},
        )
        self._log(item.relative_path, "[run] raw_text")
        return raw_text

    def _run_clean_stage(self, item: DiscoveredInput, raw_text: str, raw_text_path: Path) -> str:
        layout = self._require_layout()
        clean_path = layout.clean_text_path(item.relative_path)
        fingerprint = fingerprint_from_mapping(
            {
                "stage": "clean",
                "raw_text_sha": sha256_text(raw_text),
                "raw_text_path": layout.relative_output_path(raw_text_path),
            }
        )
        cached = self._stage_payload(item, "clean")
        if cached.get("fingerprint") == fingerprint and clean_path.exists():
            self._log(item.relative_path, "[cache] clean")
            return clean_path.read_text(encoding="utf-8")
        cleaned = clean_text(raw_text)
        write_text(clean_path, cleaned)
        self._record_stage(
            item,
            "clean",
            {
                "status": "completed",
                "fingerprint": fingerprint,
                "artifact": layout.relative_output_path(clean_path),
                "updated_at": utc_now(),
            },
            artifacts={"clean_text": clean_path},
        )
        self._log(item.relative_path, "[run] clean")
        return cleaned

    def _resolve_adapter(self, path: Path):
        for adapter in self.adapters:
            if adapter.supports(path):
                return adapter
        raise ValueError(f"Unsupported input format: {path.suffix or path.name}")

    def _ensure_file_entry(self, item: DiscoveredInput) -> None:
        with self._manifest_lock:
            file_entry = self._manifest.setdefault("files", {}).setdefault(
                item.relative_key,
                {
                    "input_path": str(item.input_path),
                    "relative_path": item.relative_key,
                    "kind": item.kind.value,
                    "source_node": item.source_node,
                    "probe": item.probe_data,
                    "estimates": item.estimates,
                    "artifacts": {},
                    "stages": {},
                    "errors": [],
                    "status": JobStatus.QUEUED.value,
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                },
            )
            file_entry["probe"] = item.probe_data
            file_entry["estimates"] = item.estimates
            file_entry["updated_at"] = utc_now()
            self._manifest["updated_at"] = utc_now()
            self._sync_manifest_unlocked()

    def _record_stage(
        self,
        item: DiscoveredInput,
        stage_name: str,
        payload: dict,
        artifacts: dict[str, Path] | None = None,
    ) -> None:
        with self._manifest_lock:
            file_entry = self._manifest["files"][item.relative_key]
            file_entry.setdefault("stages", {})[stage_name] = payload
            if artifacts:
                for key, path in artifacts.items():
                    file_entry.setdefault("artifacts", {})[key] = self._require_layout().relative_output_path(path)
            file_entry["updated_at"] = utc_now()
            self._manifest["updated_at"] = utc_now()
            self._sync_manifest_unlocked()

    def _set_file_status(self, item: DiscoveredInput, status: str) -> None:
        with self._manifest_lock:
            file_entry = self._manifest["files"][item.relative_key]
            file_entry["status"] = status
            file_entry["updated_at"] = utc_now()
            self._manifest["updated_at"] = utc_now()
            self._sync_manifest_unlocked()
        self._log(item.relative_path, f"[status] {status}")

    def _fail_file(self, item: DiscoveredInput, status: str, error_text: str) -> None:
        with self._manifest_lock:
            file_entry = self._manifest["files"][item.relative_key]
            file_entry["status"] = status
            file_entry.setdefault("errors", []).append(error_text)
            file_entry["updated_at"] = utc_now()
            self._manifest.setdefault("errors", []).append(f"{item.relative_key}: {error_text}")
            self._manifest["updated_at"] = utc_now()
            self._sync_manifest_unlocked()
        self._log(item.relative_path, f"[error] {error_text}")

    def _mark_stage_skipped(self, item: DiscoveredInput, stage_name: str, reason: str) -> None:
        self._record_stage(
            item,
            stage_name,
            {"status": "skipped", "reason": reason, "updated_at": utc_now()},
        )
        self._log(item.relative_path, f"[skip] {stage_name}: {reason}")

    def _stage_payload(self, item: DiscoveredInput, stage_name: str) -> dict:
        with self._manifest_lock:
            return dict(self._manifest["files"].get(item.relative_key, {}).get("stages", {}).get(stage_name, {}))

    def _finalize_run(self, discovered: list[DiscoveredInput]) -> list[ProcessedFile]:
        with self._manifest_lock:
            statuses = {entry.get("status", JobStatus.FAILED.value) for entry in self._manifest.get("files", {}).values()}
            if statuses == {JobStatus.COMPLETED.value}:
                self._manifest["status"] = JobStatus.COMPLETED.value
            elif JobStatus.FAILED.value in statuses:
                self._manifest["status"] = JobStatus.FAILED.value
            elif JobStatus.CANCELED.value in statuses:
                self._manifest["status"] = JobStatus.CANCELED.value
            else:
                self._manifest["status"] = JobStatus.COMPLETED.value
            self._manifest["updated_at"] = utc_now()
            self._sync_manifest_unlocked()

            files: list[ProcessedFile] = []
            for item in discovered:
                entry = self._manifest["files"][item.relative_key]
                files.append(
                    ProcessedFile(
                        input_path=item.input_path,
                        relative_path=item.relative_path,
                        status=entry.get("status", JobStatus.FAILED.value),
                        error="; ".join(entry.get("errors", [])) or None,
                        artifacts={
                            key: str(self._require_layout().run_dir / Path(value))
                            for key, value in entry.get("artifacts", {}).items()
                        },
                    )
                )
        return files

    def _log(self, relative_path: Path | None, message: str) -> None:
        layout = self._require_layout()
        append_log(layout.run_log, message)
        if relative_path is not None:
            append_log(layout.file_log_path(relative_path), message)
        if self.log_callback:
            self.log_callback(message)

    def _check_cancel(self, should_cancel: Callable[[], bool]) -> None:
        if should_cancel():
            raise JobCanceledError("Cancellation requested.")

    def _require_layout(self) -> RunLayout:
        if self._layout is None:
            raise RuntimeError("Run layout has not been initialized.")
        return self._layout

    def _sync_manifest(self) -> None:
        with self._manifest_lock:
            self._sync_manifest_unlocked()

    def _sync_manifest_unlocked(self) -> None:
        write_json(self._require_layout().run_manifest, self._manifest)


def discover_inputs(root: Path, pattern: str = "*", recursive: bool = False) -> Iterable[Path]:
    if root.is_file():
        yield root
        return

    adapters = (MediaInputAdapter(), TextInputAdapter(), DocumentInputAdapter())
    iterator = root.rglob(pattern) if recursive else root.glob(pattern)
    for path in iterator:
        if not path.is_file():
            continue
        if any(adapter.supports(path) for adapter in adapters):
            yield path


def _requested_distill_modes(request: RunRequest) -> tuple[DistillMode, ...]:
    if request.stage == ProcessingStage.DISTILL:
        return (DistillMode.DISTILL,)
    if request.stage == ProcessingStage.RANK:
        return (DistillMode.RANK,)
    if request.distill_mode == DistillMode.BOTH:
        return (DistillMode.DISTILL, DistillMode.RANK)
    return (request.distill_mode,)


def _should_run_final_stage(request: RunRequest) -> bool:
    return request.stage in (ProcessingStage.FULL, ProcessingStage.DISTILL, ProcessingStage.RANK)


def _detected_input_kind(detected_kind: str | None, input_path: Path) -> InputKind:
    if detected_kind in {item.value for item in InputKind}:
        return InputKind(detected_kind)
    suffix = input_path.suffix.lower()
    if suffix in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".wmv", ".m4v"}:
        return InputKind.VIDEO
    if suffix in {".pdf", ".doc", ".docx"}:
        return InputKind.DOCUMENT
    if suffix in {".ppt", ".pptx"}:
        return InputKind.PRESENTATION
    return InputKind.TEXT


def _source_node_name(input_path: Path, kind: InputKind) -> str:
    extension = input_path.suffix.lower().lstrip(".") or "bin"
    if kind == InputKind.VIDEO:
        return f"video__{extension}"
    if kind == InputKind.AUDIO:
        return f"audio__{extension}"
    if kind == InputKind.PRESENTATION:
        return f"presentation__{extension}"
    if kind == InputKind.DOCUMENT:
        return f"document__{extension}"
    if input_path.suffix.lower() == ".md":
        return "markdown__md"
    return "plain_text__txt"


def _estimate_resources(kind: InputKind, probe_data: dict, input_path: Path) -> dict[str, int | float | str | None]:
    estimates: dict[str, int | float | str | None] = {
        "size_bytes": input_path.stat().st_size,
        "duration_seconds": None,
        "characters": probe_data.get("characters"),
        "lines": probe_data.get("lines"),
        "page_count": probe_data.get("page_count"),
        "slide_count": probe_data.get("slide_count"),
        "bit_rate": probe_data.get("bit_rate"),
        "kind": kind.value,
    }
    if kind in (InputKind.AUDIO, InputKind.VIDEO):
        estimates["duration_seconds"] = probe_data.get("duration_seconds")
    return estimates


def _discovered_to_dict(item: DiscoveredInput) -> dict[str, object]:
    return {
        "input_path": str(item.input_path),
        "relative_path": item.relative_key,
        "kind": item.kind.value,
        "source_node": item.source_node,
        "probe": item.probe_data,
        "estimates": item.estimates,
    }
