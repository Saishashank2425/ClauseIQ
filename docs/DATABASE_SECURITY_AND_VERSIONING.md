# ClauseIQ database, authorization and versioning

## Database setup

ClauseIQ uses PostgreSQL 16+ with the pgvector extension. Install the runtime
requirements and configure `DATABASE_URL` before running migrations.

```powershell
python -m pip install -r requirements.txt
alembic upgrade head
```

For local development, Docker Compose uses the pgvector-enabled PostgreSQL image:

```powershell
docker compose up -d db
alembic upgrade head
```

The migration installs the `vector` extension and creates a 384-dimensional
vector column on clauses. Embedding generation is optional and is enabled by
setting `CLAUSEIQ_DENSE_MODEL=sentence-transformers/all-MiniLM-L6-v2` and
installing `requirements-ml.txt`. Without that optional model, documents remain
persistable and lexical workflows continue, but vector search has no vectors to rank.

## Authorization invariant

All persisted-document reads must use the query builders in
`backend/app/retrieval/authorized.py`. The subject identifier comes from a
server-verified Google ID token. It is never accepted from a request body.

The SQL statement applies these filters before clause rows are returned:

1. Current document version only.
2. Document owner, or active tenant membership plus a direct user grant,
   role grant, or tenant owner/admin role.
3. Requested document ID, if one was supplied.

Do not fetch all clauses and filter them in Python. The saved-document list,
clause endpoint, and saved-document Q&A endpoint all use the same SQL policy.
An inaccessible document returns 404 to avoid disclosing its existence.

A user's first persisted upload creates a private personal workspace with the
verified Google subject as tenant and owner. Team sharing requires an active
`tenant_memberships` row and an explicit `document_permissions` grant.
Role and permission changes must be performed by a trusted administrative
workflow; never trust role claims supplied by the browser.

## Document versioning

A changed upload with the same filename in the same personal tenant creates a
new version in the same version group. The preceding version is marked
`is_current = false`, and the new row records `supersedes_document_id`.
Identical content in the same tenant is deduplicated by SHA-256. Retrieval
queries exclude superseded versions by default.

Existing pre-migration records are assigned to a quarantined `legacy` owner
scope. They are not visible to newly authenticated users through the
authorization query.

## Important operational notes

- Set a real PostgreSQL connection URL before enabling `persist=true`.
- Back up the database before applying migrations to an existing environment.
- The vector index is an HNSW cosine index; embeddings must be 384-dimensional.
- The current first-login workflow creates a private personal tenant. A complete
  team administration/invitation UI is a separate follow-on task.
- This migration does not make the public demo endpoint multi-tenant. Demo
  fixtures are synthetic and must never contain private customer contracts.
