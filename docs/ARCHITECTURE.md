# ClauseIQ architecture

## Current foundation

The initial backend is a small FastAPI application with configuration isolated from application startup. The service exposes root and health endpoints and has an automated API smoke test.

## Planned component boundaries

- **Ingestion:** file validation and PDF/DOCX/OCR extraction
- **Preprocessing:** text normalization, page mapping, and clause segmentation
- **ML:** clause classification and model evaluation
- **Risk:** transparent rule-based flags and later learned risk scoring
- **Retrieval:** lexical BM25, vector search, fusion, and reranking
- **RAG:** evidence selection, grounded generation, citations, and abstention
- **API:** versioned HTTP routes and request/response schemas
- **Database:** SQLAlchemy models, migrations, and persistence

## Design constraints

1. Preserve document/page provenance from ingestion through every downstream result.
2. Treat retrieved contract text as untrusted input; it must not override system instructions.
3. Keep rule-based flags distinct from model predictions.
4. Do not claim legal certainty. Include evidence and uncertainty, and require human review.
5. Keep datasets and private documents out of Git.
