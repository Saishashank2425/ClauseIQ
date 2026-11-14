"""Transparent keyword/phrase risk heuristics; not legal conclusions."""
from __future__ import annotations

RULES: dict[str, tuple[str, list[str]]] = {
    "unlimited_liability": ("high", ["unlimited liability", "without limitation of liability", "infinite liability"]),
    "broad_indemnity": ("high", ["indemnify and hold harmless", "defend, indemnify", "any and all claims"]),
    "unilateral_termination": ("medium", ["terminate at any time", "sole discretion to terminate", "without cause"]),
    "automatic_renewal": ("medium", ["automatically renew", "automatic renewal", "successive renewal term"]),
    "broad_ip_assignment": ("high", ["all intellectual property", "work made for hire", "assigns all right, title and interest"]),
    "confidentiality": ("low", ["confidential information", "non-disclosure", "keep confidential"]),
    "personal_data": ("medium", ["personal data", "personal information", "data controller", "processes personal data"]),
    "late_payment": ("low", ["late fee", "interest at", "overdue amount"]),
    "non_compete": ("high", ["non-compete", "not compete", "competitive business"]),
    "limitation_of_liability": ("medium", ["limitation of liability", "aggregate liability", "consequential damages"]),
}


def assess_clause(text: str) -> tuple[str, list[str], str]:
    normalized = " ".join(text.lower().split())
    flags: list[str] = []
    levels: list[str] = []
    for name, (level, phrases) in RULES.items():
        if any(phrase in normalized for phrase in phrases):
            flags.append(name)
            levels.append(level)
    rank = {"low": 0, "medium": 1, "high": 2}
    risk = max(levels, key=lambda x: rank[x]) if levels else "low"
    explanation = ("Matched review indicators: " + ", ".join(flags)) if flags else "No configured phrase indicator matched; this does not establish that the clause is safe."
    return risk, flags, explanation
