from __future__ import annotations

import argparse
import json
from pathlib import Path

from infoproc.config import load_config, write_default_config
from infoproc.models import DistillMode, ProcessingStage, RunRequest
from infoproc.pipeline import Pipeline
from infoproc.services import TranscriptionService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="infoproc", description="Media-first information processing pipeline")
    parser.add_argument("--config", help="Path to config.toml", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Write a local config file with storage defaults")
    init_parser.add_argument("--storage-root", required=True, help="Root directory for infoproc outputs")
    init_parser.add_argument("--state-dir", default=None, help="Override runtime.state_dir in the generated config")
    init_parser.add_argument(
        "--model-cache-dir",
        default=None,
        help="Override transcription.model_cache_dir in the generated config",
    )
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing config file")

    process_parser = subparsers.add_parser("process", help="Process a file or directory into the configured conversion tree")
    _add_common_run_options(process_parser, require_output=False)

    run_parser = subparsers.add_parser("run", help=argparse.SUPPRESS)
    _add_common_run_options(run_parser, require_output=True)

    batch_parser = subparsers.add_parser("batch", help=argparse.SUPPRESS)
    _add_common_run_options(batch_parser, require_output=True)
    batch_parser.set_defaults(recursive_default=True)

    download_parser = subparsers.add_parser(
        "download-model",
        help="Pre-download a transcription model into the configured cache directory",
    )
    download_parser.add_argument("--profile", choices=["fast", "balanced", "quality"], default="quality")
    download_parser.add_argument(
        "--cache-dir",
        default=None,
        help="Override transcription.model_cache_dir for this command only",
    )

    return parser


def _add_common_run_options(parser: argparse.ArgumentParser, require_output: bool) -> None:
    parser.add_argument("--input", required=True, help="Input file or directory")
    if require_output:
        parser.add_argument("--output", required=True, help="Compatibility alias for storage root")
    parser.add_argument("--run-name", default=None, help="Reuse or override the run directory name")
    parser.add_argument("--pattern", default="*", help="Glob pattern used when discovering inputs")
    parser.add_argument("--recursive", action="store_true", help="Recurse into child directories")
    parser.add_argument("--profile", choices=["fast", "balanced", "quality"], default="balanced")
    parser.add_argument(
        "--distill",
        dest="distill_mode",
        choices=[item.value for item in DistillMode],
        default=DistillMode.BOTH.value,
    )
    parser.add_argument(
        "--stage",
        choices=[item.value for item in ProcessingStage],
        default=ProcessingStage.FULL.value,
        help="Run a specific pipeline stage or the full pipeline",
    )
    parser.add_argument("--diarize", action="store_true", help="Enable WhisperX diarization path")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        config_target = args.config or "config.toml"
        config_path = write_default_config(
            config_target,
            args.storage_root,
            state_dir=args.state_dir,
            model_cache_dir=args.model_cache_dir,
            force=args.force,
        )
        config = load_config(config_path)
        config.ensure_storage_root()
        config.ensure_state_dir()
        config.transcription.model_cache_dir.mkdir(parents=True, exist_ok=True)
        config.diarization.hf_home.mkdir(parents=True, exist_ok=True)
        print(
            json.dumps(
                {
                    "config_path": str(config_path),
                    "storage_root": str(config.storage.root_dir),
                    "state_dir": str(config.runtime.state_dir),
                    "model_cache_dir": str(config.transcription.model_cache_dir),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    config = load_config(args.config)

    if args.command == "download-model":
        if args.cache_dir:
            config.transcription.model_cache_dir = Path(args.cache_dir).expanduser()
        payload = TranscriptionService(config).prefetch_profile_model(args.profile)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    storage_root = Path(getattr(args, "output", config.storage.root_dir)).expanduser()
    request = RunRequest(
        input_path=Path(args.input),
        storage_root=storage_root,
        profile=args.profile,
        diarize=args.diarize,
        distill_mode=DistillMode(args.distill_mode),
        stage=ProcessingStage(args.stage),
        pattern=args.pattern,
        recursive=bool(getattr(args, "recursive", False) or getattr(args, "recursive_default", False)),
        run_name=args.run_name,
    )
    pipeline = Pipeline(config, log_callback=lambda msg: print(msg))
    result = pipeline.process(request)
    print(json.dumps(_run_result_to_dict(result), ensure_ascii=False, indent=2))
    return 0 if all(item.status == "completed" for item in result.files) else 1


def _run_result_to_dict(result) -> dict:
    return {
        "run_dir": str(result.run_dir),
        "run_manifest_path": str(result.run_manifest_path),
        "files": [
            {
                "input_path": str(item.input_path),
                "relative_path": item.relative_path.as_posix(),
                "status": item.status,
                "error": item.error,
                "artifacts": item.artifacts,
            }
            for item in result.files
        ],
    }
