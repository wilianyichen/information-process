from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from infoproc.config import load_config, write_default_config


def _base_env(**overrides: str) -> dict[str, str]:
    env = dict(os.environ)
    for key in (
        "INFOPROC_CONFIG",
        "INFOPROC_BASE_URL",
        "INFOPROC_MODEL",
        "INFOPROC_API_KEY",
        "INFOPROC_TIMEOUT_SECONDS",
        "INFOPROC_TEMPERATURE",
        "INFOPROC_MAX_TOKENS",
        "INFOPROC_STATE_DIR",
        "INFOPROC_LOG_LEVEL",
        "INFOPROC_STORAGE_ROOT",
        "INFOPROC_RUNS_DIR_NAME",
        "INFOPROC_SCHEDULER_MODE",
        "INFOPROC_DOCUMENT_WORKERS",
        "INFOPROC_TRANSCRIBE_WORKERS",
        "INFOPROC_LLM_WORKERS",
        "INFOPROC_EXECUTION_STRATEGY",
        "INFOPROC_DISTILL_BATCH_SIZE",
        "INFOPROC_TRANSCRIPTION_DEVICE",
        "INFOPROC_FAST_MODEL",
        "INFOPROC_BALANCED_MODEL",
        "INFOPROC_QUALITY_MODEL",
        "INFOPROC_MODEL_CACHE_DIR",
        "INFOPROC_HF_HOME",
        "INFOPROC_PDF_ENGINE",
        "INFOPROC_OFFICE_CONVERTER",
    ):
        env.pop(key, None)
    env.update(overrides)
    return env


class ConfigTests(unittest.TestCase):
    def test_load_config_from_infoproc_config_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "server.toml"
            config_path.write_text(
                """
[api]
base_url = "https://example.invalid/v1"

[runtime]
state_dir = "/var/lib/infoproc/state"

[storage]
root_dir = "/var/lib/infoproc/output"
                """.strip(),
                encoding="utf-8",
            )

            with patch.dict(os.environ, _base_env(INFOPROC_CONFIG=str(config_path)), clear=True):
                config = load_config(None)

            self.assertEqual(config.config_path, config_path.resolve())
            self.assertEqual(config.api.base_url, "https://example.invalid/v1")
            self.assertEqual(config.runtime.state_dir, Path("/var/lib/infoproc/state"))
            self.assertEqual(config.storage.root_dir, Path("/var/lib/infoproc/output"))

    def test_env_overrides_apply_to_new_runtime_settings(self) -> None:
        with patch.dict(
            os.environ,
            _base_env(
                INFOPROC_BASE_URL="https://api.example.com/v1",
                INFOPROC_MODEL="gpt-test",
                INFOPROC_API_KEY="secret",
                INFOPROC_TIMEOUT_SECONDS="45",
                INFOPROC_TEMPERATURE="0.2",
                INFOPROC_MAX_TOKENS="2048",
                INFOPROC_STATE_DIR="/srv/infoproc/state",
                INFOPROC_LOG_LEVEL="DEBUG",
                INFOPROC_STORAGE_ROOT="/srv/infoproc/storage",
                INFOPROC_RUNS_DIR_NAME="custom-runs",
                INFOPROC_SCHEDULER_MODE="serial",
                INFOPROC_DOCUMENT_WORKERS="4",
                INFOPROC_TRANSCRIBE_WORKERS="2",
                INFOPROC_LLM_WORKERS="6",
                INFOPROC_TRANSCRIPTION_DEVICE="cpu",
                INFOPROC_FAST_MODEL="tiny",
                INFOPROC_BALANCED_MODEL="small",
                INFOPROC_QUALITY_MODEL="large-v3",
                INFOPROC_MODEL_CACHE_DIR="/srv/infoproc/models",
                INFOPROC_HF_HOME="/srv/infoproc/hf_home",
                INFOPROC_PDF_ENGINE="pdftotext",
                INFOPROC_OFFICE_CONVERTER="libreoffice",
            ),
            clear=True,
        ):
            config = load_config(None)

        self.assertEqual(config.api.base_url, "https://api.example.com/v1")
        self.assertEqual(config.api.model, "gpt-test")
        self.assertEqual(config.api.api_key, "secret")
        self.assertEqual(config.runtime.state_dir, Path("/srv/infoproc/state"))
        self.assertEqual(config.runtime.log_level, "DEBUG")
        self.assertEqual(config.storage.root_dir, Path("/srv/infoproc/storage"))
        self.assertEqual(config.storage.runs_dir_name, "custom-runs")
        self.assertEqual(config.scheduler.mode, "serial")
        self.assertEqual(config.scheduler.document_workers, 4)
        self.assertEqual(config.scheduler.transcribe_workers, 2)
        self.assertEqual(config.scheduler.llm_workers, 6)
        self.assertEqual(config.transcription.device, "cpu")
        self.assertEqual(config.transcription.fast_model, "tiny")
        self.assertEqual(config.transcription.balanced_model, "small")
        self.assertEqual(config.transcription.model_cache_dir, Path("/srv/infoproc/models"))
        self.assertEqual(config.diarization.hf_home, Path("/srv/infoproc/hf_home"))
        self.assertEqual(config.document.pdf_engine, "pdftotext")
        self.assertEqual(config.document.office_converter, "libreoffice")

    def test_expanduser_applies_to_config_and_env_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home_dir = Path(tmp) / "home-user"
            home_dir.mkdir(parents=True, exist_ok=True)
            config_path = Path(tmp) / "tilde.toml"
            config_path.write_text(
                """
[storage]
root_dir = "~/wuxiaoran/storage"

[transcription]
model_cache_dir = "~/wuxiaoran/models"
                """.strip(),
                encoding="utf-8",
            )

            env = _base_env(
                INFOPROC_CONFIG=str(config_path),
                INFOPROC_HF_HOME="~/wuxiaoran/hf_home",
                HOME=str(home_dir),
                USERPROFILE=str(home_dir),
            )
            with patch.dict(os.environ, env, clear=True):
                config = load_config(None)

            self.assertEqual(config.storage.root_dir, home_dir / "wuxiaoran" / "storage")
            self.assertEqual(config.transcription.model_cache_dir, home_dir / "wuxiaoran" / "models")
            self.assertEqual(config.diarization.hf_home, home_dir / "wuxiaoran" / "hf_home")

    def test_write_default_config_uses_storage_root_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            storage_root = Path(tmp) / "storage-root"

            written = write_default_config(config_path, storage_root)
            config = load_config(written)

            self.assertEqual(written, config_path.resolve())
            self.assertEqual(config.storage.root_dir, storage_root.resolve())
            self.assertEqual(config.runtime.state_dir, (storage_root / ".state").resolve())
            self.assertEqual(config.transcription.model_cache_dir, (storage_root / "models").resolve())


if __name__ == "__main__":
    unittest.main()
