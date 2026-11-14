from pydantic import BaseModel, Field


class ClauseResult(BaseModel):
    clause_id: str
    text: str
    page: int | None = None
    category: str = "other"
    risk_level: str = "low"
    risk_flags: list[str] = Field(default_factory=list)
    explanation: str = ""


class DocumentAnalysis(BaseModel):
    filename: str
    document_id: int | None = None
    pages: int
    word_count: int
    clauses: list[ClauseResult]
    summary: dict[str, int]
    disclaimer: str = "Automated decision support only. Obtain qualified legal review."
