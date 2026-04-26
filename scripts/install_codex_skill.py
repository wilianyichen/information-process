from __future__ import annotations

import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "skills"


def main() -> int:
    code_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
    target_root = code_home / "skills"

    target_root.mkdir(parents=True, exist_ok=True)
    installed = []
    for source_dir in sorted(SOURCE_ROOT.iterdir()):
        if not source_dir.is_dir() or not (source_dir / "SKILL.md").exists():
            continue
        target_dir = target_root / source_dir.name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
        installed.append(target_dir)

    if not installed:
        raise FileNotFoundError(f"No skill sources found under: {SOURCE_ROOT}")

    for target_dir in installed:
        print(target_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
