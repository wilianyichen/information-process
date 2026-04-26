from __future__ import annotations

import shutil
import tarfile
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
SOURCE_DIR = ROOT / "deploy" / "linux" / "rootless"
SKILLS_DIR = ROOT / "skills"


def main() -> int:
    version = _load_version()
    wheel_path = _find_wheel(version)
    bundle_name = f"infoproc-linux-user-{version}"
    staging_dir = DIST_DIR / bundle_name
    archive_path = DIST_DIR / f"{bundle_name}.tar.gz"

    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    try:
        _copy_file(SOURCE_DIR / "README.md", staging_dir / "README.md")
        if (SOURCE_DIR / "README-EN.md").exists():
            _copy_file(SOURCE_DIR / "README-EN.md", staging_dir / "README-EN.md")
        _copy_file(SOURCE_DIR / "install.sh", staging_dir / "install.sh")
        _copy_tree(SOURCE_DIR / "bin", staging_dir / "bin")
        _copy_tree(SOURCE_DIR / "lib", staging_dir / "lib")
        _copy_tree(SOURCE_DIR / "templates", staging_dir / "templates")
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                _copy_tree(skill_dir, staging_dir / "codex-skill" / skill_dir.name)

        wheels_dir = staging_dir / "wheels"
        wheels_dir.mkdir(parents=True, exist_ok=True)
        _copy_file(wheel_path, wheels_dir / wheel_path.name)

        if archive_path.exists():
            archive_path.unlink()
        with tarfile.open(archive_path, "w:gz") as handle:
            handle.add(staging_dir, arcname=bundle_name)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

    print(archive_path)
    return 0


def _load_version() -> str:
    pyproject_path = ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return data["project"]["version"]


def _find_wheel(version: str) -> Path:
    candidates = sorted(DIST_DIR.glob(f"infoproc-{version}-*.whl"))
    if not candidates:
        raise FileNotFoundError(
            f"No wheel found for infoproc {version}. Run `python -m build` before building the rootless bundle."
        )
    return candidates[-1]


def _copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, dirs_exist_ok=True)


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


if __name__ == "__main__":
    raise SystemExit(main())
