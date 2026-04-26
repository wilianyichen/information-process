from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib


DEFAULT_CONFIG_PATHS = (
    Path("config.toml"),
    Path.home() / ".config" / "infoproc" / "config.toml",
    Path("/etc/infoproc/config.toml"),
)


@dataclass(slots=True)
class APISettings:
    base_url: str = ""
    model: str = "astron-code-latest"
    api_key: str | None = None
    api_key_env: str = "INFOPROC_API_KEY"
    timeout_seconds: int = 120
    temperature: float = 0.7
    max_tokens: int = 4096

    def resolved_api_key(self) -> str | None:
        return self.api_key or os.getenv(self.api_key_env)


@dataclass(slots=True)
class RuntimeSettings:
    state_dir: Path = Path(".infoproc")
    log_level: str = "INFO"


@dataclass(slots=True)
class StorageSettings:
    root_dir: Path = Path("outputs")
    runs_dir_name: str = "runs"


@dataclass(slots=True)
class SchedulerSettings:
    mode: str = "auto"
    document_workers: int = 2
    transcribe_workers: int = 1
    llm_workers: int = 2


@dataclass(slots=True)
class TranscriptionSettings:
    device: str = "auto"
    fast_model: str = "small"
    balanced_model: str = "medium"
    quality_model: str = "large-v3"
    model_cache_dir: Path = Path(".infoproc/models")

    def model_for_profile(self, profile: str) -> str:
        mapping = {
            "fast": self.fast_model,
            "balanced": self.balanced_model,
            "quality": self.quality_model,
        }
        if profile not in mapping:
            raise ValueError(f"Unsupported profile: {profile}")
        return mapping[profile]


@dataclass(slots=True)
class DiarizationSettings:
    hf_token_env: str = "HF_TOKEN"
    hf_home: Path = Path(".infoproc/hf_home")

    def resolved_token(self) -> str | None:
        return os.getenv(self.hf_token_env)


@dataclass(slots=True)
class DocumentSettings:
    pdf_engine: str = "pypdf"
    office_converter: str = "soffice"


@dataclass(slots=True)
class AppConfig:
    api: APISettings = field(default_factory=APISettings)
    runtime: RuntimeSettings = field(default_factory=RuntimeSettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    scheduler: SchedulerSettings = field(default_factory=SchedulerSettings)
    transcription: TranscriptionSettings = field(default_factory=TranscriptionSettings)
    diarization: DiarizationSettings = field(default_factory=DiarizationSettings)
    document: DocumentSettings = field(default_factory=DocumentSettings)
    config_path: Path | None = None

    def ensure_state_dir(self) -> Path:
        self.runtime.state_dir.mkdir(parents=True, exist_ok=True)
        return self.runtime.state_dir

    def ensure_storage_root(self) -> Path:
        self.storage.root_dir.mkdir(parents=True, exist_ok=True)
        return self.storage.root_dir


def _merge_dataclass(instance: Any, values: dict[str, Any]) -> Any:
    for key, value in values.items():
        if not hasattr(instance, key):
            continue
        current = getattr(instance, key)
        if isinstance(current, Path):
            setattr(instance, key, _expand_path(value))
        else:
            setattr(instance, key, value)
    return instance


def load_config(config_path: str | Path | None = None) -> AppConfig:
    config = AppConfig()
    path = _resolve_config_path(config_path)
    data: dict[str, Any] = {}
    if path is not None:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        _merge_dataclass(config.api, data.get("api", {}))
        runtime_values = data.get("runtime", {})
        _merge_dataclass(config.runtime, runtime_values)
        _merge_dataclass(config.storage, data.get("storage", {}))
        _merge_dataclass(config.scheduler, data.get("scheduler", {}))
        _merge_dataclass(config.transcription, data.get("transcription", {}))
        _merge_dataclass(config.diarization, data.get("diarization", {}))
        _merge_dataclass(config.document, data.get("document", {}))
        _apply_legacy_runtime_values(config, runtime_values)
        config.config_path = path
    _apply_env_overrides(config)
    return config


def write_default_config(
    config_path: str | Path,
    storage_root: str | Path,
    state_dir: str | Path | None = None,
    model_cache_dir: str | Path | None = None,
    force: bool = False,
) -> Path:
    path = Path(config_path).expanduser()
    if path.exists() and not force:
        raise FileExistsError(f"Config file already exists: {path}")
    storage_path = Path(storage_root).expanduser()
    resolved_state_dir = Path(state_dir).expanduser() if state_dir else storage_path / ".state"
    resolved_model_cache = Path(model_cache_dir).expanduser() if model_cache_dir else storage_path / "models"
    content = render_default_config(storage_path, resolved_state_dir, resolved_model_cache)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path.resolve()


def render_default_config(storage_root: Path, state_dir: Path, model_cache_dir: Path) -> str:
    return "\n".join(
        [
            "[api]",
            'base_url = "https://your-openai-compatible-endpoint/v1"',
            'model = "astron-code-latest"',
            'api_key_env = "INFOPROC_API_KEY"',
            "timeout_seconds = 120",
            "temperature = 0.7",
            "max_tokens = 4096",
            "",
            "[runtime]",
            f'state_dir = "{_path_for_toml(state_dir)}"',
            'log_level = "INFO"',
            "",
            "[storage]",
            f'root_dir = "{_path_for_toml(storage_root)}"',
            'runs_dir_name = "runs"',
            "",
            "[scheduler]",
            'mode = "auto"',
            "document_workers = 2",
            "transcribe_workers = 1",
            "llm_workers = 2",
            "",
            "[transcription]",
            'device = "auto"',
            'fast_model = "small"',
            'balanced_model = "medium"',
            'quality_model = "large-v3"',
            f'model_cache_dir = "{_path_for_toml(model_cache_dir)}"',
            "",
            "[diarization]",
            'hf_token_env = "HF_TOKEN"',
            f'hf_home = "{_path_for_toml(storage_root / "hf_home")}"',
            "",
            "[document]",
            'pdf_engine = "pypdf"',
            'office_converter = "soffice"',
            "",
        ]
    )


def _resolve_config_path(config_path: str | Path | None) -> Path | None:
    if config_path:
        path = Path(config_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        return path
    env_config_path = os.getenv("INFOPROC_CONFIG")
    if env_config_path:
        path = Path(env_config_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        return path
    for candidate in DEFAULT_CONFIG_PATHS:
        if candidate.exists():
            return candidate.resolve()
    return None


def _apply_legacy_runtime_values(config: AppConfig, runtime_values: dict[str, Any]) -> None:
    if "execution_strategy" in runtime_values and "mode" not in runtime_values:
        config.scheduler.mode = runtime_values["execution_strategy"]
    if "transcribe_workers" in runtime_values and "document_workers" not in runtime_values:
        config.scheduler.document_workers = max(1, int(runtime_values["transcribe_workers"]))
    if "transcribe_workers" in runtime_values and "transcribe_workers" not in runtime_values:
        config.scheduler.transcribe_workers = max(1, int(runtime_values["transcribe_workers"]))
    if "distill_batch_size" in runtime_values and "llm_workers" not in runtime_values:
        config.scheduler.llm_workers = max(1, int(runtime_values["distill_batch_size"]))


def _apply_env_overrides(config: AppConfig) -> None:
    _apply_env_str("INFOPROC_BASE_URL", lambda value: setattr(config.api, "base_url", value))
    _apply_env_str("INFOPROC_MODEL", lambda value: setattr(config.api, "model", value))
    _apply_env_str("INFOPROC_API_KEY", lambda value: setattr(config.api, "api_key", value))
    _apply_env_int("INFOPROC_TIMEOUT_SECONDS", lambda value: setattr(config.api, "timeout_seconds", value))
    _apply_env_float("INFOPROC_TEMPERATURE", lambda value: setattr(config.api, "temperature", value))
    _apply_env_int("INFOPROC_MAX_TOKENS", lambda value: setattr(config.api, "max_tokens", value))

    _apply_env_path("INFOPROC_STATE_DIR", lambda value: setattr(config.runtime, "state_dir", value))
    _apply_env_str("INFOPROC_LOG_LEVEL", lambda value: setattr(config.runtime, "log_level", value))

    _apply_env_path("INFOPROC_STORAGE_ROOT", lambda value: setattr(config.storage, "root_dir", value))
    _apply_env_str("INFOPROC_RUNS_DIR_NAME", lambda value: setattr(config.storage, "runs_dir_name", value))

    _apply_env_str("INFOPROC_SCHEDULER_MODE", lambda value: setattr(config.scheduler, "mode", value))
    _apply_env_int(
        "INFOPROC_DOCUMENT_WORKERS",
        lambda value: setattr(config.scheduler, "document_workers", value),
    )
    _apply_env_int(
        "INFOPROC_TRANSCRIBE_WORKERS",
        lambda value: setattr(config.scheduler, "transcribe_workers", value),
    )
    _apply_env_int(
        "INFOPROC_LLM_WORKERS",
        lambda value: setattr(config.scheduler, "llm_workers", value),
    )

    if os.getenv("INFOPROC_SCHEDULER_MODE") in (None, ""):
        _apply_env_str("INFOPROC_EXECUTION_STRATEGY", lambda value: setattr(config.scheduler, "mode", value))
    if os.getenv("INFOPROC_LLM_WORKERS") in (None, ""):
        _apply_env_int(
            "INFOPROC_DISTILL_BATCH_SIZE",
            lambda value: setattr(config.scheduler, "llm_workers", value),
        )

    _apply_env_str(
        "INFOPROC_TRANSCRIPTION_DEVICE",
        lambda value: setattr(config.transcription, "device", value),
    )
    _apply_env_str(
        "INFOPROC_FAST_MODEL",
        lambda value: setattr(config.transcription, "fast_model", value),
    )
    _apply_env_str(
        "INFOPROC_BALANCED_MODEL",
        lambda value: setattr(config.transcription, "balanced_model", value),
    )
    _apply_env_str(
        "INFOPROC_QUALITY_MODEL",
        lambda value: setattr(config.transcription, "quality_model", value),
    )
    _apply_env_path(
        "INFOPROC_MODEL_CACHE_DIR",
        lambda value: setattr(config.transcription, "model_cache_dir", value),
    )

    _apply_env_path("INFOPROC_HF_HOME", lambda value: setattr(config.diarization, "hf_home", value))

    _apply_env_str("INFOPROC_PDF_ENGINE", lambda value: setattr(config.document, "pdf_engine", value))
    _apply_env_str(
        "INFOPROC_OFFICE_CONVERTER",
        lambda value: setattr(config.document, "office_converter", value),
    )


def _apply_env_str(name: str, setter) -> None:
    value = os.getenv(name)
    if value not in (None, ""):
        setter(value)


def _apply_env_int(name: str, setter) -> None:
    value = os.getenv(name)
    if value not in (None, ""):
        setter(int(value))


def _apply_env_float(name: str, setter) -> None:
    value = os.getenv(name)
    if value not in (None, ""):
        setter(float(value))


def _apply_env_path(name: str, setter) -> None:
    value = os.getenv(name)
    if value not in (None, ""):
        setter(_expand_path(value))


def _expand_path(value: str | os.PathLike[str]) -> Path:
    return Path(value).expanduser()


def _path_for_toml(path: Path) -> str:
    return path.expanduser().resolve().as_posix()
