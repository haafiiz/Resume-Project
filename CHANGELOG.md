# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added — Sprint 2: Resume Upload and Processing

- **Database**: `Resume`, `ResumeSection`, `Skill`, `Experience`,
  `Project`, `Education`, `Certification` models with `source`
  (`resume`/`user`) and `verified` metadata on every extracted item.
  Alembic migration `add resume domain tables`.
- **File storage**: `utils/file_storage.py` — UUID-based, collision-free
  filenames under `storage/uploads/`; original filesystem paths are
  never exposed via the API.
- **Upload validation**: `utils/upload_validation.py` — filename safety,
  extension allowlist, file-signature (magic byte) verification (not
  just declared `Content-Type`), size limits, empty-file rejection.
- **Deterministic parsing** (`core/parsing/`): `docx_parser.py` and
  `pdf_parser.py` extract plain text; `resume_parser.py` performs
  section detection and structured extraction (contact info, skills,
  experience, education, projects, certifications) using regex/heuristic
  matching — no LLM involved anywhere in this pipeline, consistent with
  the project's truth-constrained principle.
- **Resume service** (`services/resume_service.py`): orchestrates
  upload → validate → store → parse → persist, corrections, and
  verification, implementing the `uploaded → parsed/needs_review →
  verified` state machine. Corrections are rejected (`409`) once a
  resume is verified.
- **API** (`api/v1/resumes.py`):
  - `POST /resumes` — upload (multipart)
  - `GET /resumes` — list
  - `GET /resumes/{id}/profile` — full structured profile
  - `PUT /resumes/{id}` — corrections (rejected once verified)
  - `POST /resumes/{id}/verify` — mark verified (idempotent)
- **Frontend**: `/resumes` (list), `/resumes/new` (upload), `/resumes/:id`
  (profile view, section editors, and "Mark Resume as Verified"). New
  components: `UploadForm`, `StatusBadge`, `SkillsEditor`,
  `ExperienceEditor`, `ProjectEditor`, `EducationEditor`,
  `CertificationEditor`. `api/resumes.ts` and `types/resume.ts` added;
  `api/client.ts` refactored with a shared request helper and `ApiError`.
- **Testing**: 52 backend tests (DOCX/PDF parsing, structured extraction,
  upload validation, resume CRUD/update/verification) and a new frontend
  test suite for the upload flow. Test-only DOCX/PDF fixture builders
  added (`tests/backend/helpers/pdf_docx_builders.py`) rather than
  checked-in binary files.
- **Documentation**: new `docs/resume-processing.md`, `docs/database.md`,
  `docs/api.md`; updated `docs/setup.md`, `docs/architecture.md`,
  `docs/testing.md`, `README.md`.

### Explicitly not included in this sprint

Job description parsing, matching engine, AI provider implementation,
tailoring engine, validation engine, DOCX resume generation, and
authentication remain out of scope and are planned for later sprints.

## [Unreleased - Sprint 1]

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
