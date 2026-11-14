"""Conservative clause segmentation with stable page provenance."""
from __future__ import annotations
import re
from dataclasses import dataclass
from backend.app.ingestion.extract import ExtractedPage

HEADING = re.compile(r"(?im)^\\s*((?:\\d+(?:\\.\\d+)*[.)]?|[A-Z](?:\\.|\\))|ARTICLE\\s+[IVXLC]+|SECTION\\s+\\d+(?:\\.\\d+)*)\\s+.{2,120}$")

@dataclass
class Clause:
    clause_id: str
    text: str
    page: int | None


def segment_pages(pages: list[ExtractedPage], max_chars: int = 5000) -> list[Clause]:
    clauses: list[Clause] = []
    for page in pages:
        text = page.text.strip()
        if not text:
            continue
        matches = list(HEADING.finditer(text))
        if matches:
            starts = [m.start() for m in matches] + [len(text)]
            parts = [text[starts[i]:starts[i + 1]].strip() for i in range(len(starts) - 1)]
            parts = [p for p in parts if len(p) >= 35]
        else:
            parts = [p.strip() for p in re.split(r"\\n\\s*\\n", text) if len(p.strip()) >= 80]
            if not parts:
                parts = [text]
        for part in parts:
            # Keep model inputs bounded without silently dropping the remainder.
            chunks = [part[i:i + max_chars] for i in range(0, len(part), max_chars)]
            for chunk in chunks:
                clauses.append(Clause(f"C{len(clauses) + 1:04d}", chunk, page.page))
    return clauses
