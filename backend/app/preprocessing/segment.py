"""Conservative clause segmentation with stable page provenance."""
from __future__ import annotations
import re
from dataclasses import dataclass
from backend.app.ingestion.extract import ExtractedPage

HEADING = re.compile(r"(?im)^\s*((?:\d+(?:\.\d+)*[.)]?|[A-Z](?:\.|\))|ARTICLE\s+[IVXLC]+|SECTION\s+\d+(?:\.\d+)*)\s+.{2,120}$")

@dataclass
class Clause:
    clause_id: str
    text: str
    page: int | None

def segment_pages(pages: list[ExtractedPage], max_chars: int = 5000) -> list[Clause]:
    clauses = []
    for page in pages:
        text = page.text.strip()
        if not text:
            continue
        matches = list(HEADING.finditer(text))
        if matches:
            starts = [m.start() for m in matches] + [len(text)]
            parts = [text[starts[i]:starts[i + 1]].strip() for i in range(len(starts) - 1)]
            parts = [part for part in parts if len(part) >= 35]
        else:
            parts = [part.strip() for part in re.split(r"\n\s*\n", text) if len(part.strip()) >= 80]
            if not parts:
                parts = [text]
        for part in parts:
            for offset in range(0, len(part), max_chars):
                clauses.append(Clause(f"C{len(clauses) + 1:04d}", part[offset:offset + max_chars], page.page))
    return clauses
