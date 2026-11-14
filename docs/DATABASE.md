# Database setup

Set `DATABASE_URL` in `.env` to a PostgreSQL SQLAlchemy URL, for example:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
```

Install requirements, then run:

```powershell
python -m scripts.init_db
```

The API's `POST /api/v1/analyze?persist=true` option stores a SHA-256 deduplicated document record and its extracted clauses. Do not enable persistence until the database is provisioned and access-controlled. This initial schema uses SQLAlchemy `create_all`; production deployments should move to versioned Alembic migrations.
