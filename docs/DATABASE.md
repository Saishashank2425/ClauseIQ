# Database setup

Configure `DATABASE_URL` in `.env`:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
```

Apply versioned schema migrations:

```powershell
alembic upgrade head
```

The `POST /api/v1/analyze?persist=true` option stores a SHA-256 deduplicated document record and its extracted clauses. Persistence is opt-in. Do not enable it until PostgreSQL is provisioned, access-controlled and backed up. The initial Alembic revision creates `documents` and `clauses`.

The current prototype does not implement user accounts or tenant isolation. Do not store confidential third-party contracts in a publicly accessible demo.
