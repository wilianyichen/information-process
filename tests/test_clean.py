from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from infoproc.services.clean import clean_text


class CleanTextTests(unittest.TestCase):
    def test_clean_text_deduplicates_lines_and_spaces(self) -> None:
        raw = "嗯  嗯  我们  我们 开始\n\n我们 我们 开始\n"
        cleaned = clean_text(raw)
        self.assertEqual(cleaned, "嗯 我们 开始\n")


if __name__ == "__main__":
    unittest.main()
