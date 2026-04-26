from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from infoproc.cli import build_parser


class CLITests(unittest.TestCase):
    def test_init_parser_supports_storage_root_and_force(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "--config",
                "config.toml",
                "init",
                "--storage-root",
                "~/infoproc-storage",
                "--model-cache-dir",
                "~/models",
                "--force",
            ]
        )

        self.assertEqual(args.command, "init")
        self.assertEqual(args.storage_root, "~/infoproc-storage")
        self.assertEqual(args.model_cache_dir, "~/models")
        self.assertTrue(args.force)

    def test_process_parser_does_not_require_output(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "process",
                "--input",
                "input-dir",
                "--recursive",
                "--run-name",
                "demo-run",
            ]
        )

        self.assertEqual(args.command, "process")
        self.assertEqual(args.input, "input-dir")
        self.assertTrue(args.recursive)
        self.assertEqual(args.run_name, "demo-run")

    def test_batch_alias_keeps_compatibility_output(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "batch",
                "--input",
                "input-dir",
                "--output",
                "legacy-output",
                "--pattern",
                "*.txt",
            ]
        )

        self.assertEqual(args.command, "batch")
        self.assertEqual(args.output, "legacy-output")
        self.assertEqual(args.pattern, "*.txt")


if __name__ == "__main__":
    unittest.main()
