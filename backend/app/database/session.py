from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import get_settings

@lru_cache
def get_engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True)

def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)

def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
