from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DISTILL_RANK_SUMMARY_NAME = "蒸馏与降秩汇总.md"
CLEAN_SUMMARY_NAME = "clean汇总.md"


@dataclass(slots=True)
class AggregateOutputs:
    summary_dir: Path
    distill_rank_summary: Path
    clean_summary: Path


def generate_final_summaries(run_dir: Path) -> AggregateOutputs:
    summary_dir = run_dir / "05_final" / "_summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)

    distill_root = run_dir / "05_final" / "distill__md"
    rank_root = run_dir / "05_final" / "rank__md"
    clean_root = run_dir / "04_text_clean" / "clean_text__txt"

    distill_rank_summary = summary_dir / DISTILL_RANK_SUMMARY_NAME
    clean_summary = summary_dir / CLEAN_SUMMARY_NAME

    distill_rank_summary.write_text(
        _build_distill_rank_summary(distill_root, rank_root),
        encoding="utf-8",
    )
    clean_summary.write_text(
        _build_clean_summary(clean_root),
        encoding="utf-8",
    )

    return AggregateOutputs(
        summary_dir=summary_dir,
        distill_rank_summary=distill_rank_summary,
        clean_summary=clean_summary,
    )


def _build_distill_rank_summary(distill_root: Path, rank_root: Path) -> str:
    entries: dict[str, dict[str, Path]] = {}
    for path in _sorted_files(distill_root, "*.md"):
        entries.setdefault(path.relative_to(distill_root).as_posix(), {})["distill"] = path
    for path in _sorted_files(rank_root, "*.md"):
        entries.setdefault(path.relative_to(rank_root).as_posix(), {})["rank"] = path

    sections: list[str] = []
    for relative_name in sorted(entries):
        payload = entries[relative_name]
        sections.append(f"## {relative_name}\n\n")
        if "distill" in payload:
            sections.append("### 蒸馏\n\n")
            sections.append(_offset_markdown_headings(payload["distill"].read_text(encoding="utf-8"), 3))
            sections.append("\n")
        if "rank" in payload:
            sections.append("### 降秩\n\n")
            sections.append(_offset_markdown_headings(payload["rank"].read_text(encoding="utf-8"), 3))
            sections.append("\n")

    if not sections:
        sections.append("当前运行没有可汇总的蒸馏或降秩文件。\n")
    return _build_summary("蒸馏与降秩汇总", sections)


def _build_clean_summary(clean_root: Path) -> str:
    sections: list[str] = []
    for text_path in _sorted_files(clean_root, "*.txt"):
        relative_name = text_path.relative_to(clean_root).as_posix()
        sections.append(f"## {relative_name}\n\n")
        sections.append("```text\n")
        sections.append(text_path.read_text(encoding="utf-8").rstrip())
        sections.append("\n```\n\n")

    if not sections:
        sections.append("当前运行没有可汇总的 clean 文本文件。\n")
    return _build_summary("clean汇总", sections)


def _sorted_files(root: Path, pattern: str) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob(pattern), key=lambda item: item.relative_to(root).as_posix())


def _build_summary(title: str, sections: list[str]) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = "".join(section if section.endswith("\n") else section + "\n" for section in sections)
    return f"# {title}\n\n生成时间：{timestamp}\n\n{body}".rstrip() + "\n"


def _offset_markdown_headings(content: str, level_offset: int) -> str:
    adjusted_lines: list[str] = []
    for line in content.splitlines():
        if line.startswith("#"):
            hash_count = len(line) - len(line.lstrip("#"))
            adjusted_lines.append("#" * (hash_count + level_offset) + line[hash_count:])
        else:
            adjusted_lines.append(line)
    return "\n".join(adjusted_lines).rstrip() + "\n"
