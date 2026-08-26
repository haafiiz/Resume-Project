"""
SQLAlchemy engine, session factory, and declarative base.

This module intentionally does NOT define any application tables yet.
Sprint 1 only establishes the connection machinery; the schema is added
in later sprints as models are introduced.
"""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# Ensure the storage directory exists for file-based SQLite databases.
if settings.database_url.startswith("sqlite:///./"):
    db_path = settings.database_url.replace("sqlite:///./", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models in the application."""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables registered on Base's metadata.

    In Sprint 1 there are no models yet, so this is effectively a no-op,
    but it verifies the engine/connection is functional and gives later
    sprints a single place to call when new models are added.
    """
    Base.metadata.create_all(bind=engine)
