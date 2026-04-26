from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from infoproc.services.prompts import load_prompt


class PromptTests(unittest.TestCase):
    def test_distill_prompt_contains_framework(self) -> None:
        prompt = load_prompt("distill.md")
        self.assertIn("【道】", prompt)
        self.assertIn("【器】", prompt)

    def test_rank_prompt_mentions_ljg_rank(self) -> None:
        prompt = load_prompt("rank.md")
        self.assertIn("ljg-rank", prompt)


if __name__ == "__main__":
    unittest.main()
