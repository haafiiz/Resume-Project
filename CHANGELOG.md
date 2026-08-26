# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added — Sprint 1: Project Foundation

- Repository structure: `frontend/`, `backend/`, `tests/`, `docs/`, `storage/`.
- **Backend**: FastAPI application skeleton (`app/main.py`) with
  `api/`, `models/`, `schemas/`, `services/`, `core/`, `repositories/`,
  `utils/` packages established per the architecture.
  - `GET /api/v1/health` returning `{"status": "ok"}`.
  - Environment-variable based configuration (`app/config.py`, via
    `pydantic-settings`) covering app environment, CORS origins,
    database URL, Ollama URL/model (reserved), and upload limits
    (reserved).
  - SQLAlchemy engine/session/`Base` (`app/database.py`) and `init_db()`.
    No application tables yet — schema starts in a later sprint.
  - Alembic configured (`backend/alembic/`), wired to read the database
    URL from application settings rather than a hardcoded value.
  - CORS configured from `CORS_ORIGINS`, environment-based.
- **Frontend**: React + TypeScript + Vite + Tailwind CSS v4 app shell.
  - Routing via `react-router-dom`: Dashboard (`/`), Resumes
    (`/resumes`), Job Descriptions (`/job-descriptions`), Analysis
    (`/analysis`) — all placeholder pages.
  - `AppLayout` + `Navigation` components for shared header/nav chrome.
  - `api/client.ts` — minimal fetch wrapper reading `VITE_API_BASE_URL`.
  - Dashboard page calls the backend health endpoint and displays a live
    connectivity indicator.
- **Testing**:
  - Backend: `tests/backend/test_health.py`,
    `tests/backend/test_database.py` (pytest + FastAPI `TestClient`).
  - Frontend: `frontend/src/App.test.tsx` (Vitest + React Testing
    Library), mocking the API client so it doesn't depend on a running
    backend.
- **Documentation**: `README.md`, this `CHANGELOG.md`,
  `docs/architecture.md`, `docs/setup.md`, `docs/development.md`,
  `docs/testing.md`, `docs/contributing.md`.
- `.gitignore` and `.env.example` (root, documenting all env vars) plus
  `frontend/.env.example`.

### Explicitly not included in this sprint

Resume parsing, JD parsing, matching engine, AI provider implementation,
tailoring engine, validation engine, DOCX generation, and authentication
are all out of scope for Sprint 1 and will be introduced in later
sprints.
