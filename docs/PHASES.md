# Implementation status

## Implemented in this branch
- Phase 1: FastAPI foundation and configuration.
- Phase 2: Local CUAD/ContractNLI JSON normalization utility. Dataset files are not downloaded or committed.
- Phase 3: PDF/DOCX extraction, optional PDF OCR, clause segmentation, page provenance where available.
- Phase 4 baseline: transparent phrase-based risk indicators and API response schema.

## Still to implement
- Supervised clause classification training/evaluation and Legal-BERT comparison.
- FAISS/BM25 hybrid retrieval and cross-encoder reranking.
- LLM-backed evidence-grounded RAG, citations, and abstention.
- PostgreSQL persistence, authentication, React frontend, and production deployment hardening.
- Evaluation datasets, ablations, MLflow, Docker, and CI.

The current rules are explainable heuristics, not a trained legal model or legal advice. DOCX page numbers are not reliable and therefore returned as null. OCR requires the Tesseract executable installed on the host.
