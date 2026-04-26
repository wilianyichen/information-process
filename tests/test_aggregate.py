from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from infoproc.aggregate import generate_final_summaries


class AggregateTests(unittest.TestCase):
    def test_generate_final_summaries_writes_separate_distill_and_rank_files(self) -> None:
        root = Path(__file__).resolve().parents[1] / ".test-temp" / f"aggregate-{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        try:
            distill_path = root / "05_final" / "distill__md" / "nested" / "meeting.md"
            rank_path = root / "05_final" / "rank__md" / "nested" / "meeting.md"
            distill_path.parent.mkdir(parents=True, exist_ok=True)
            rank_path.parent.mkdir(parents=True, exist_ok=True)
            distill_path.write_text("# 蒸馏标题\n\n蒸馏内容\n", encoding="utf-8")
            rank_path.write_text("# 降秩标题\n\n降秩内容\n", encoding="utf-8")

            outputs = generate_final_summaries(root)

            self.assertIsNotNone(outputs.distill_summary)
            self.assertIsNotNone(outputs.rank_summary)
            self.assertTrue(outputs.summary_dir.exists())
            distill_text = outputs.distill_summary.read_text(encoding="utf-8")  # type: ignore[union-attr]
            rank_text = outputs.rank_summary.read_text(encoding="utf-8")  # type: ignore[union-attr]
            self.assertIn("nested/meeting.md", distill_text)
            self.assertIn("### 蒸馏标题", distill_text)
            self.assertIn("nested/meeting.md", rank_text)
            self.assertIn("### 降秩标题", rank_text)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
