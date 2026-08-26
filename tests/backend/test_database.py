from sqlalchemy import text

from app.database import Base, SessionLocal, engine, init_db


def test_init_db_creates_metadata_without_error():
    # Sprint 1 has no models registered yet, so this simply verifies the
    # engine/session machinery is wired correctly end-to-end.
    init_db()
    assert Base.metadata is not None


def test_database_session_can_execute_query():
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        db.close()


def test_engine_connects_successfully():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar()
        assert result == 1
