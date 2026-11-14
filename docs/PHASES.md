# Implementation status

## Implemented in this branch
- Phase 1: FastAPI foundation, configuration, health routes, and CI.
- Phase 2: local CUAD/ContractNLI normalization utility. Dataset files are not downloaded or committed.
- Phase 3: PDF/DOCX extraction, optional PDF OCR, clause segmentation, page provenance where available.
- Phase 4 baseline: explainable phrase-based risk flags and optional TF-IDF + LinearSVC clause-category training/inference.
- Phase 5 baseline: BM25 + TF-IDF hybrid retrieval; optional cross-encoder reranking can be enabled with `CLAUSEIQ_CROSS_ENCODER_MODEL` when `sentence-transformers` and model weights are installed.
- Phase 6 baseline: evidence-returning extractive Q&A with relevance threshold and abstention. This is not an LLM answer generator.
- Phase 7 baseline: FastAPI endpoints, React/Vite dashboard, optional SQLAlchemy/PostgreSQL persistence, Vercel serverless entry point.
- Phase 8 baseline: backend/frontend GitHub Actions CI and deployment documentation.

## Remaining research and production work
- Validate dataset normalization against the exact CUAD and ContractNLI releases used; build deterministic train/validation/test splits and dataset cards.
- Train, tune, and evaluate the classifier; compare TF-IDF against Legal-BERT with macro-F1, per-class metrics, calibration, and error analysis.
- Add neural dense embeddings (e.g. sentence-transformers + FAISS), measure retrieval recall@k/MRR, and evaluate cross-encoder reranking.
- Add an LLM-backed answer generator that is constrained to retrieved evidence, emits page/section citations, and abstains when evidence is insufficient.
- Add Alembic migrations, user/document access control, secure object storage, audit logging, rate limiting, and retention/deletion controls.
- Add full integration/evaluation suites, ablations, MLflow tracking, Docker deployment, and production observability.

## Important limitations
- Risk flags are transparent heuristics, not legal conclusions or a trained risk model.
- The optional classifier is a classical baseline and needs actual training/evaluation before it is useful.
- DOCX page numbers are not reliable and are returned as null.
- OCR requires the Tesseract executable installed on the host.
- The Q&A endpoint returns source passages rather than generating a legal interpretation.
- Database persistence is opt-in with `persist=true`; initialize PostgreSQL first with `python -m scripts.init_db`.
- Vercel serverless is suitable for a lightweight demo API, not large OCR jobs, transformer inference, or long-running processing.
