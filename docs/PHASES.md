# ClauseIQ implementation status

## Implemented
1. Foundation: FastAPI, settings, routes, tests and CI.
2. Data preparation: CUAD/ContractNLI JSON normalization; raw datasets remain local.
3. Ingestion: PDF/DOCX extraction, optional OCR, clause segmentation and PDF page provenance.
4. ML/risk: explainable phrase indicators, TF-IDF + LinearSVC training, optional Legal-BERT fine-tuning and lazy inference.
5. Retrieval: BM25 + TF-IDF, optional sentence-transformer dense embeddings with FAISS, optional cross-encoder reranking.
6. RAG: evidence-first retrieval, optional OpenAI-compatible generation constrained to supplied passages, clause citation validation, extractive fallback and abstention.
7. Application: React/Vite dashboard, FastAPI, optional PostgreSQL persistence and Alembic migration.
8. Evaluation/deployment: classifier and retrieval evaluation, optional MLflow logging, Docker/Compose, Vercel configs and CI.

## Research workflow
- Install optional dependencies: `python -m pip install -r requirements-ml.txt`.
- Normalize source files: `python scripts/prepare_datasets.py --cuad datasets/raw/cuad.json --contractnli datasets/raw/contractnli.json`.
- Train classical baseline: `python scripts/train_clause_classifier.py`.
- Fine-tune Legal-BERT: `python scripts/train_legalbert.py --epochs 2`.
- Enable Legal-BERT inference: `CLAUSEIQ_CLASSIFIER_BACKEND=legalbert`.
- Enable dense retrieval: `CLAUSEIQ_DENSE_MODEL=sentence-transformers/all-MiniLM-L6-v2`.
- Enable reranking: `CLAUSEIQ_CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2`.
- Configure grounded generation with `CLAUSEIQ_LLM_BASE_URL`, `CLAUSEIQ_LLM_MODEL`, and optional `CLAUSEIQ_LLM_API_KEY`.
- Retrieval evaluation JSONL rows require `query`, `documents` (passages), and `relevant_indices` (relevant passage positions). Run `python scripts/evaluate_retrieval.py --input path/to/queries.jsonl`.

## Remaining before production/legal use
- Run experiments on licensed datasets and publish measured metrics; this repository does not claim model scores.
- Verify dataset versions, licenses, label mapping, and train/validation/test split methodology.
- Restrict CORS to the frontend domain; add authentication, authorization, rate limits, malware scanning, secure object storage, retention/deletion controls, audit logs and tenant isolation.
- Evaluate generated answers against expert-labeled questions; citations alone do not prove correctness.
- Run OCR/transformer workloads on a persistent worker, not constrained serverless functions.

## Limitations
Risk flags are heuristic review prompts, not legal conclusions. Models are not trained until the user downloads licensed data and runs the documented scripts. DOCX page numbers are unavailable via python-docx. Vercel serverless payload/runtime limits make Docker/persistent hosting preferable for larger contracts and optional ML inference.
