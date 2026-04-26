from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from infoproc.aggregate import generate_final_summaries


class AggregateTests(unittest.TestCase):
    def test_generate_final_summaries_writes_combined_distill_rank_and_clean_files(self) -> None:
        root = Path(__file__).resolve().parents[1] / ".test-temp" / f"aggregate-{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        try:
            distill_path = root / "05_final" / "distill__md" / "nested" / "meeting.md"
            rank_path = root / "05_final" / "rank__md" / "nested" / "meeting.md"
            clean_path = root / "04_text_clean" / "clean_text__txt" / "nested" / "meeting.txt"
            distill_path.parent.mkdir(parents=True, exist_ok=True)
            rank_path.parent.mkdir(parents=True, exist_ok=True)
            clean_path.parent.mkdir(parents=True, exist_ok=True)
            distill_path.write_text("# 蒸馏标题\n\n蒸馏内容\n", encoding="utf-8")
            rank_path.write_text("# 降秩标题\n\n降秩内容\n", encoding="utf-8")
            clean_path.write_text("clean内容\n第二行\n", encoding="utf-8")

            outputs = generate_final_summaries(root)

            self.assertTrue(outputs.summary_dir.exists())
            distill_rank_text = outputs.distill_rank_summary.read_text(encoding="utf-8")
            clean_text = outputs.clean_summary.read_text(encoding="utf-8")
            self.assertIn("nested/meeting.md", distill_rank_text)
            self.assertIn("### 蒸馏", distill_rank_text)
            self.assertIn("#### 蒸馏标题", distill_rank_text)
            self.assertIn("### 降秩", distill_rank_text)
            self.assertIn("#### 降秩标题", distill_rank_text)
            self.assertIn("nested/meeting.txt", clean_text)
            self.assertIn("```text", clean_text)
            self.assertIn("clean内容", clean_text)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_generate_final_summaries_writes_placeholder_text_when_inputs_missing(self) -> None:
        root = Path(__file__).resolve().parents[1] / ".test-temp" / f"aggregate-empty-{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        try:
            outputs = generate_final_summaries(root)
            distill_rank_text = outputs.distill_rank_summary.read_text(encoding="utf-8")
            clean_text = outputs.clean_summary.read_text(encoding="utf-8")
            self.assertIn("当前运行没有可汇总的蒸馏或降秩文件", distill_rank_text)
            self.assertIn("当前运行没有可汇总的 clean 文本文件", clean_text)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
