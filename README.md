# ClauseIQ

**Evidence-first AI contract intelligence and review workspace.**

ClauseIQ is a research prototype that extracts contract text, segments clauses, surfaces explainable review indicators, retrieves supporting passages, and optionally generates answers constrained to retrieved evidence.

## Features
- PDF and DOCX extraction with optional Tesseract OCR for scanned PDFs.
- Clause segmentation with PDF page provenance.
- Explainable phrase-based risk review indicators.
- Trainable TF-IDF + LinearSVC baseline and optional Legal-BERT fine-tuning/inference.
- BM25 + TF-IDF retrieval, optional FAISS dense embeddings and cross-encoder reranking.
- Evidence-first Q&A with clause citation validation, extractive fallback and abstention.
- React/Vite dashboard, FastAPI API and optional PostgreSQL persistence.
- Alembic migration, Docker Compose, evaluation scripts and GitHub Actions CI.

## Quick start (Python 3.13)
```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```
API docs: `http://127.0.0.1:8000/docs`.

In a second terminal:
```powershell
cd frontend
npm install
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

## Optional ML/research stack
```powershell
python -m pip install -r requirements-ml.txt
```
Download CUAD and ContractNLI from their original sources, follow their terms, and place source files under `datasets/raw/`. Then normalize:
```powershell
python scripts/prepare_datasets.py --cuad datasets/raw/cuad.json --contractnli datasets/raw/contractnli.json
python scripts/train_clause_classifier.py
python scripts/train_legalbert.py --epochs 2
```
Enable optional model components with environment variables documented in `.env.example`. Research workflow and limitations are in `docs/PHASES.md`.

## Database
Configure `DATABASE_URL`, then apply migrations:
```powershell
alembic upgrade head
```
The analyze endpoint persists only when explicitly called with `?persist=true`.

## Docker
```powershell
docker compose up --build
```
The compose file starts PostgreSQL and the API. Apply database migrations in the API container before using persistence.

## Deployment
See `docs/DEPLOYMENT.md` for separate Vercel frontend/API setup and Docker hosting guidance.

## Important limitations
- The repository does not include external datasets, trained weights, private contracts or measured benchmark scores.
- Risk flags are heuristic review prompts, not legal conclusions.
- Legal-BERT and dense retrieval require optional dependencies, downloaded model weights and actual training/evaluation.
- Grounded LLM generation is optional and requires an OpenAI-compatible endpoint configured via environment variables.
- DOCX pagination is not reliably available through python-docx.
- Vercel serverless is suitable only for small demo documents; large uploads, OCR and model inference should use persistent container/worker hosting.
- Authentication, tenant isolation, malware scanning, production rate limiting and formal privacy controls must be added before handling confidential customer contracts.

## Disclaimer
ClauseIQ is an educational/research decision-support prototype, not legal advice. Outputs require review by qualified counsel.
