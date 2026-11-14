# ClauseIQ production RAG architecture

This is the implementation target and phased delivery checklist. A feature is not complete until tests and deployment verification pass.

## Request path
1. Verify the Google ID token server-side and resolve organisation and role from PostgreSQL. Never trust browser-supplied roles, tenant IDs, ACLs, or document IDs for authorization.
2. Build the authorization predicate first: organisation membership AND document ACL role membership AND owner/share rule AND current-version policy. Apply it in the SQL query that fetches candidate chunks. Never fetch all chunks and filter them in Python.
3. Retrieve candidates with PostgreSQL pgvector cosine distance and PostgreSQL full-text ranking. Combine rankings with reciprocal-rank fusion.
4. Rerank only authorized candidates with a cross-encoder. Reranking must never widen the authorized candidate set.
5. Apply document freshness/version rules. Prefer current versions; retrieve superseded versions only for explicit historical comparison. Newest upload is not automatically legally effective.
6. Pass only authorized, reranked excerpts and source metadata to the configured free-tier LLM.
7. Validate every clause/page citation against retrieved evidence. If support is insufficient, citations fail, or providers fail, abstain.
8. Persist operational metrics and trace IDs. Do not send raw contract text to observability services by default.

## Target components
- API: FastAPI.
- System of record: PostgreSQL.
- Vector index: pgvector extension in PostgreSQL, with tenant and ACL metadata on every chunk.
- Hybrid retrieval: PostgreSQL full-text search + pgvector similarity + reciprocal-rank fusion.
- Reranking: optional SentenceTransformers CrossEncoder.
- LLM: OpenAI-compatible adapter; Groq Free first, Gemini free tier fallback. Only configured keys are called. Free quotas and availability are not SLAs.
- Tracing: Langfuse cloud Hobby or self-hosted OSS. Trace metadata only by default.
- Evaluation: 50-question golden set, deterministic citation checks, optional RAGAS evaluation (faithfulness, context precision/recall, answer relevancy, factual correctness).
- Dashboard: incorrect/failed searches, latency percentiles, unsupported/abstained answers, token usage, estimated cost, provider/model and user feedback.

## Document freshness model
Each document needs document_family_id, version_number, effective_at, uploaded_at, is_current, supersedes_document_id, and status. Ingestion must not assume the latest upload is legally effective. Mark a version current only after explicit confirmation or a reliable effective-date/version extraction reviewed by a user. Keep historical versions for audit; default retrieval to current versions.

## Access-control model
Suggested roles: admin, legal, analyst, viewer. Store roles and organisation membership in PostgreSQL. Store per-document allowed roles and owner/explicit grants. Use SQL predicates before retrieval. Default-deny if identity, tenant, role, or ACL data is missing. Public synthetic demo data is separate from private tenant queries.

## Free-tier boundaries
- Groq Free has account/model-specific rate limits and no production uptime guarantee. Check current model IDs and quotas in the provider console.
- Gemini free API tier also has quotas and can be temporarily unavailable.
- Langfuse Cloud Hobby has a monthly usage allowance and short retention; self-hosted OSS is free software but still needs infrastructure.
- RAGAS LLM metrics consume evaluation-provider quota. Deterministic citation tests run locally without an LLM.
- pgvector runs inside PostgreSQL, but the database host still has storage and compute limits.

## Delivery phases
- [x] Phase A: configurable free-tier provider failover, strict citation validation, privacy-safe optional Langfuse span, 50-question synthetic golden set.
- [ ] Phase B: PostgreSQL user/organisation/role/document ACL schema; default-deny RBAC; SQL-side ACL filtering before chunk retrieval.
- [ ] Phase C: pgvector embeddings, hybrid lexical+dense SQL retrieval, reciprocal-rank fusion, reranker integration and freshness/version handling.
- [ ] Phase D: persisted query/feedback/provider metrics and admin dashboard.
- [ ] Phase E: run all 50 questions, RAGAS scoring and citation correctness; publish measured results, not assumed accuracy.

## Security and quality gates
- Never use browser role claims for authorization.
- Never return chunks from another tenant or a role-inaccessible document.
- Never send private excerpts to a provider unless the deployment's data-processing policy permits it.
- Keep provider keys server-side.
- Do not claim zero hallucinations. Measure faithfulness/citation precision, enforce abstention, and report residual risk.
- Treat version ordering as a legal/business decision; newest upload is not automatically the operative contract.
