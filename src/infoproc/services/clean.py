from __future__ import annotations

import re


FILLER_WORDS = ("嗯", "啊", "呃", "然后", "就是", "这个", "那个")


def clean_text(content: str) -> str:
    lines = [_normalize_line(line) for line in content.splitlines()]
    lines = [line for line in lines if line]
    deduped: list[str] = []
    for line in lines:
        if deduped and (_dedupe_key(deduped[-1]) == _dedupe_key(line)):
            continue
        deduped.append(line)
    return "\n".join(deduped).strip() + ("\n" if deduped else "")


def _normalize_line(line: str) -> str:
    compact = re.sub(r"\s+", " ", line).strip()
    compact = _collapse_duplicate_phrases(compact)
    for filler in FILLER_WORDS:
        compact = re.sub(rf"(^|\s){re.escape(filler)}(\s{re.escape(filler)})+", rf"\1{filler}", compact)
    return compact.strip(" ,，")


def _collapse_duplicate_phrases(line: str) -> str:
    words = line.split(" ")
    collapsed: list[str] = []
    for word in words:
        if collapsed and collapsed[-1] == word:
            continue
        collapsed.append(word)
    return " ".join(collapsed)


def _dedupe_key(line: str) -> str:
    words = [word for word in line.split(" ") if word and word not in FILLER_WORDS]
    return " ".join(words)
