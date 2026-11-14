"""Synthetic demo agreement used to exercise the retrieval and Q&A pipeline."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.rag.answer import answer_question
from backend.app.schemas.analysis import ClauseResult, DocumentAnalysis

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

DEMO_CLAUSES = [
    ClauseResult(clause_id="C0001", page=2, category="liability", risk_level="high",
        risk_flags=["uncapped_liability", "indemnification"],
        explanation="Broad indemnification language with no stated monetary cap.",
        text="9. INDEMNIFICATION. The Supplier shall indemnify, defend and hold harmless the Customer and its affiliates, directors, officers and employees from and against all claims, losses, damages, liabilities, costs and expenses (including reasonable legal fees) arising out of or relating to any breach of this Agreement, negligence, wilful misconduct, or infringement of third-party rights by Supplier. The obligations in this section are not subject to any limitation of liability set out elsewhere in this Agreement."),
    ClauseResult(clause_id="C0002", page=3, category="termination", risk_level="medium",
        risk_flags=["termination_for_convenience"],
        explanation="Either party may terminate for convenience on 30 days' notice.",
        text="10. TERMINATION. Either party may terminate this Agreement for convenience by providing thirty (30) days' prior written notice to the other party. Either party may terminate immediately if the other party commits a material breach and fails to cure that breach within fifteen (15) days after receiving written notice."),
    ClauseResult(clause_id="C0003", page=3, category="renewal", risk_level="medium",
        risk_flags=["automatic_renewal"],
        explanation="The agreement renews automatically unless notice is given 60 days before expiry.",
        text="11. TERM AND RENEWAL. This Agreement begins on the Effective Date and continues for an initial term of twelve (12) months. It will automatically renew for successive twelve (12) month periods unless either party gives written notice of non-renewal at least sixty (60) days before the end of the then-current term."),
    ClauseResult(clause_id="C0004", page=4, category="confidentiality", risk_level="low",
        risk_flags=["confidentiality"],
        explanation="Confidentiality obligations continue for five years after termination.",
        text="12. CONFIDENTIALITY. Each party shall protect the other party's Confidential Information using at least reasonable care and shall use it only to perform this Agreement. These obligations survive expiration or termination for five (5) years, except for information qualifying as a trade secret, which remains protected for so long as it remains a trade secret."),
    ClauseResult(clause_id="C0005", page=5, category="governing_law", risk_level="low",
        risk_flags=["governing_law"],
        explanation="The agreement selects New York law and exclusive New York County courts.",
        text="15. GOVERNING LAW AND VENUE. This Agreement is governed by the laws of the State of New York, without regard to conflict-of-law principles. The parties submit to the exclusive jurisdiction of the state and federal courts located in New York County, New York.")
]

def _analysis() -> DocumentAnalysis:
    return DocumentAnalysis(
        filename="Northstar_SaaS_Services_Agreement_DEMO.docx",
        pages=5,
        word_count=sum(len(clause.text.split()) for clause in DEMO_CLAUSES),
        clauses=DEMO_CLAUSES,
        summary={"high": 1, "medium": 2, "low": 2},
        disclaimer="Synthetic sample agreement for product demonstration only. Not legal advice."
    )

@router.get("")
def get_demo():
    return _analysis()

class DemoQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=1500)

@router.post("/ask")
def ask_demo(body: DemoQuestion):
    result = answer_question(body.question, DEMO_CLAUSES, top_k=3)
    result["document"] = "Northstar SaaS Services Agreement (synthetic demo)"
    return result
