import os

# Ensure tests never touch the developer's real SQLite file - point the
# app at an isolated test database before anything imports app.config.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./storage/test.db")
