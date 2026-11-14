"""Create ClauseIQ tables using the configured DATABASE_URL."""
from backend.app.core.config import get_settings
from backend.app.database.base import Base
from backend.app.models import DocumentRecord, ClauseRecord  # noqa: F401
from sqlalchemy import create_engine

if __name__ == "__main__":
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    print("ClauseIQ database tables are ready.")
