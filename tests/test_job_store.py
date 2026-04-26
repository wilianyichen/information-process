from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from infoproc.config import AppConfig
from infoproc.execution import choose_batch_execution_plan, sort_inputs_for_processing
from infoproc.models import DiscoveredInput, EnvironmentSnapshot, InputKind


def _discovered(name: str, kind: InputKind, **estimates) -> DiscoveredInput:
    return DiscoveredInput(
        input_path=Path(name),
        relative_path=Path(name),
        kind=kind,
        source_node="plain_text__txt",
        probe_data={},
        estimates=estimates,
    )


class ExecutionPlanTests(unittest.TestCase):
    def test_choose_batch_execution_plan_prefers_single_gpu_transcription_lane(self) -> None:
        config = AppConfig()
        config.scheduler.document_workers = 4
        config.scheduler.transcribe_workers = 3
        config.scheduler.llm_workers = 5
        environment = EnvironmentSnapshot(
            cpu_count=8,
            available_memory_bytes=16 * 1024**3,
            has_cuda=True,
            ffmpeg_available=True,
            ffprobe_available=True,
            office_converter=None,
            pdftotext=None,
        )
        inputs = [
            _discovered("video.mp4", InputKind.VIDEO, duration_seconds=120.0),
            _discovered("notes.txt", InputKind.TEXT, characters=1000),
        ]

        plan = choose_batch_execution_plan(config, environment, inputs)

        self.assertEqual(plan.transcribe_workers, 1)
        self.assertGreaterEqual(plan.document_workers, 1)
        self.assertGreaterEqual(plan.llm_workers, 1)
        self.assertTrue(plan.stream_llm)

    def test_sort_inputs_for_processing_puts_large_media_before_docs_and_text(self) -> None:
        items = [
            _discovered("short.txt", InputKind.TEXT, characters=10, lines=1),
            _discovered("slides.pptx", InputKind.PRESENTATION, characters=200, slide_count=4),
            _discovered("long.mp4", InputKind.VIDEO, duration_seconds=300.0),
            _discovered("short.mp4", InputKind.VIDEO, duration_seconds=30.0),
        ]

        ordered = sort_inputs_for_processing(items)

        self.assertEqual([item.relative_key for item in ordered[:2]], ["long.mp4", "short.mp4"])
        self.assertEqual(ordered[2].relative_key, "slides.pptx")


if __name__ == "__main__":
    unittest.main()
