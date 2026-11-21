from __future__ import annotations

import re


def segment_text(text: str, target: int = 280, minimum: int = 120) -> list[tuple[int, str]]:
    """Return (chapter, segment) pairs without crossing Markdown headings."""
    chapters: list[list[str]] = [[]]
    for line in text.replace("\r\n", "\n").split("\n"):
        if re.match(r"^#{1,6}\s+", line.strip()) and chapters[-1]:
            chapters.append([])
        chapters[-1].append(line.strip())
    result: list[tuple[int, str]] = []
    for chapter_no, lines in enumerate(chapters, 1):
        sentences = re.split(r"(?<=[.!?])\s+", " ".join(x for x in lines if x).strip())
        buffer = ""
        for sentence in sentences:
            if not sentence:
                continue
            if buffer and len(buffer) + len(sentence) + 1 > target and len(buffer) >= minimum:
                result.append((chapter_no, buffer))
                buffer = sentence
            else:
                buffer = f"{buffer} {sentence}".strip()
        if buffer:
            result.append((chapter_no, buffer))
    return result
