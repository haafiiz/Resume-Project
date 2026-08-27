import os

# Ensure tests never touch the developer's real SQLite file - point the
# app at an isolated test database before anything imports app.config.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./storage/test.db")

# Likewise, keep uploaded test fixtures out of the developer's real
# storage/uploads/ directory.
os.environ.setdefault("UPLOAD_DIR", "./storage/test_uploads")

import shutil  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import Base, engine  # noqa: E402
import app.models  # noqa: E402,F401  (registers all models on Base.metadata)


@pytest.fixture(autouse=True)
def _reset_database_and_uploads():
    """Give every test function a clean database and upload directory,
    so resume records/files from one test never leak into another."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    yield
