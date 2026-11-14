# ClauseIQ

**AI-powered legal contract intelligence and risk analysis.**

ClauseIQ is a research and engineering project for extracting contract content, identifying legal clauses, surfacing risk indicators, and answering questions with evidence-linked citations.

> Status: Phase 1 — foundation in progress. Features are implemented incrementally; the README will be updated as each phase is completed.

## Planned capabilities

- PDF, DOCX, and OCR-based document ingestion
- Clause segmentation and classification using CUAD-derived data
- Contractual entailment experiments using ContractNLI
- Rule-based risk indicators with explainable evidence
- Hybrid semantic and lexical retrieval (FAISS + BM25)
- Evidence-grounded RAG with page-level citations and abstention
- FastAPI backend, React dashboard, and PostgreSQL persistence
- Evaluation, experiment tracking, containerization, and CI

## Development roadmap

1. Environment and project foundation
2. CUAD and ContractNLI dataset preparation
3. Document processing and clause segmentation
4. ML classification and risk analysis
5. Hybrid retrieval and reranking
6. Evidence-grounded RAG
7. API, dashboard, and database integration
8. Evaluation, deployment, and demonstration

## Repository structure

```text
backend/
  app/
    api/
    core/
    database/
    ingestion/
    ml/
    models/
    preprocessing/
    rag/
    retrieval/
    risk/
  tests/
docs/
datasets/                 # Dataset files are not committed
```

## Quick start

Use Python 3.13 in a virtual environment.

```bash
python -m venv venv
# Windows
venv\\Scripts\\activate
# macOS/Linux
source venv/bin/activate

python -m pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

The API health endpoint will be available at `/health` and interactive API documentation at `/docs`.

## Data and licensing

CUAD and ContractNLI are external research datasets. Follow each dataset's original license, terms, and citation requirements. Dataset files, private contracts, credentials, and local environment files must not be committed.

## Security

Never commit API keys, passwords, private contracts, database dumps, or `.env` files. Use `.env.example` only for non-secret configuration templates.

## Disclaimer

ClauseIQ is an educational/research decision-support prototype, not a substitute for qualified legal advice. Model outputs and risk flags require human review.
