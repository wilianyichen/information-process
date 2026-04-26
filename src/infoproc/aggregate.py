from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DISTILL_SUMMARY_NAME = "蒸馏汇总.md"
RANK_SUMMARY_NAME = "降秩汇总.md"


@dataclass(slots=True)
class AggregateOutputs:
    summary_dir: Path
    distill_summary: Path | None
    rank_summary: Path | None


def generate_final_summaries(run_dir: Path) -> AggregateOutputs:
    summary_dir = run_dir / "05_final" / "_summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)

    distill_sections = _collect_sections(run_dir / "05_final" / "distill__md")
    rank_sections = _collect_sections(run_dir / "05_final" / "rank__md")

    distill_summary = None
    if distill_sections:
        distill_summary = summary_dir / DISTILL_SUMMARY_NAME
        distill_summary.write_text(_build_summary("蒸馏汇总", distill_sections), encoding="utf-8")

    rank_summary = None
    if rank_sections:
        rank_summary = summary_dir / RANK_SUMMARY_NAME
        rank_summary.write_text(_build_summary("降秩汇总", rank_sections), encoding="utf-8")

    return AggregateOutputs(
        summary_dir=summary_dir,
        distill_summary=distill_summary,
        rank_summary=rank_summary,
    )


def _collect_sections(root: Path) -> list[str]:
    if not root.exists():
        return []
    sections: list[str] = []
    for markdown_path in sorted(root.rglob("*.md"), key=lambda item: item.relative_to(root).as_posix()):
        relative_name = markdown_path.relative_to(root).as_posix()
        sections.append(f"## {relative_name}\n")
        sections.append(_offset_markdown_headings(markdown_path.read_text(encoding="utf-8"), 2))
        sections.append("\n")
    return sections


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
