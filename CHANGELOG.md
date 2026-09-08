# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added — Sprint 4: Resume/JD Matching Engine

- **Matching module** (`core/matching/`), pure application logic with no
  LLM involved:
  - `normalizer.py` — a controlled, hand-maintained alias table
    (`CANONICAL_ALIASES`) for formatting variants (e.g. "REST API" /
    "REST APIs" / "RESTful API" all normalize to the same value);
    deliberately not a fuzzy/statistical stemmer, so nothing can be
    merged that wasn't explicitly declared safe.
  - `matcher.py` — per-requirement classification into `exact` /
    `normalized` / `related` / `partial` / `missing` / `unknown`, plus
    freetext-category matching (responsibilities/experience/education/
    domain/keywords/soft-skills) via whole-word token overlap, plus
    `analyze_requirements()` full-analysis orchestration. `partial`
    matching is token-set-based (not substring-based) specifically so
    "java" can never accidentally match inside "javascript".
  - `scorer.py` — configurable weighted scoring
    (`MATCH_WEIGHT_REQUIRED_SKILLS`, etc., default 50/25/10/5/5/5 per
    the spec), the documented "empty category scores 1.0, not 0" rule,
    and the mapping of 9 JD `requirement_type` values onto the 6
    weighted categories (`technology`→required_skills,
    `domain`/`soft_skill`→keywords).
- **Database**: `Analysis` (overall + 6 category scores, a
  `weights_snapshot` JSON capturing the exact weights/breakdown used, so
  a past analysis stays reproducible even if defaults change later) and
  `SkillMatch` (one row per JD requirement evaluated, including
  `missing` ones, with `resume_skill_id` for skill-table matches or
  `matched_resume_label`/`matched_resume_text` for freetext-category
  matches). Alembic migration `add analysis and skill match tables`.
- **Analysis service** (`services/analysis_service.py`): converts a
  verified `Resume`/`JobDescription` pair into the plain,
  ORM-independent shapes `core/matching` operates on, runs the engine,
  and persists the result. **Enforces the critical rule structurally**:
  both inputs must already be `verified` (`409` otherwise) - the service
  has no code path that adds, infers, or "fills in" a resume skill to
  produce a match.
- **API** (`api/v1/analyses.py`): `POST /analyses`, `GET
  /analyses/{id}`, `GET /analyses/{id}/matches` (includes
  `extra_resume_skills` - verified resume skills matching no
  requirement, informational only, never scored).
- **Frontend**: `/analysis` rebuilt as a verified-resume ×
  verified-job-description picker that runs an analysis and navigates
  to it; new `/analysis/:id` shows the overall score, a weighted
  category breakdown (`OverallScoreCard`, `ScoreBar`), and matched /
  partial / missing / extra-skill groupings (`MatchList`).
- **Testing**: 44 new pure-logic unit tests for `core/matching/`
  (`test_matching_engine.py`) including a dedicated
  `TestMandatoryFalsePositiveGuards` class proving Java/JavaScript,
  AWS/Azure, Selenium/Playwright, and React/Angular never merge in
  either direction, plus 20 new analysis API integration tests
  (`test_analysis_api.py`) that reproduce the acceptance criteria
  scenario byte-for-byte (resume: Python/Selenium/Playwright/SQL, JD:
  Python/Selenium/Playwright/Cypress/AWS → matched
  Python/Selenium/Playwright, missing Cypress/AWS, score 80.0,
  reproducible). 164 backend tests total. 3 new frontend tests for the
  analysis picker flow (14 frontend tests total).
- **Documentation**: new `docs/matching-engine.md` (complete scoring
  algorithm with a worked example matching the acceptance criteria
  exactly); updated `docs/api.md`, `docs/database.md`,
  `docs/architecture.md`, `docs/testing.md`, `README.md`.

### Explicitly not included in this sprint

AI-assisted tailoring, claim validation, and DOCX resume generation
remain out of scope and are planned for later sprints.

## [Unreleased - Sprint 3]

### Added — Sprint 3: Job Description Processing

- **AI provider abstraction** (`core/ai/`): `AIProvider` (`base.py`) is a
  minimal, vendor-agnostic interface (`generate(prompt, system) -> str`)
  with two exception types (`AIProviderUnavailableError`,
  `AIProviderResponseError`); `OllamaProvider` implements it against a
  local Ollama instance; `factory.py` resolves the configured provider
  from settings. `JDService` depends only on the interface and never
  imports `OllamaProvider` directly.
- **JD requirement extraction** (`core/ai/jd_extraction.py`): builds the
  extraction prompt, calls any injected `AIProvider`, and validates the
  response against a strict Pydantic contract (`core/ai/schemas.py`) -
  9 `requirement_type` categories × 3 `importance` levels. A response
  missing the `requirements` key entirely is treated as malformed
  (caught during manual testing - the field has no default, unlike an
  explicit empty list, which is legitimately valid).
- **Database**: `JobDescription` and `JDRequirement` models with
  `requirement_type`, `name`, `normalized_name`, `importance`,
  `description`, `source_text`, `verified`. Alembic migration `add job
  description domain tables`.
- **Deterministic normalization** (`utils/text_normalization.py`):
  lowercase/trim/collapse-whitespace, applied to every requirement name
  by `JDService` - never delegated to the AI.
- **JD service** (`services/jd_service.py`): save and extract are
  **separate steps** (`create()` vs. `extract_requirements_for()`),
  matching the spec's explicit six-step flow. Implements the
  `created → extracted/needs_review → verified` state machine; AI
  failures (unavailable or malformed response) never fail the HTTP
  request - they're recorded as `needs_review` with an explanation, and
  the job description remains fully editable.
- **API** (`api/v1/job_descriptions.py`):
  - `POST /job-descriptions` — save (title/company optional, description required)
  - `GET /job-descriptions` — list
  - `GET /job-descriptions/{id}` — full JD with requirements
  - `POST /job-descriptions/{id}/extract` — run AI extraction
  - `PUT /job-descriptions/{id}` — corrections (rejected once verified)
  - `POST /job-descriptions/{id}/verify` — mark verified (idempotent)
- **Frontend**: `/jobs` (list), `/jobs/new` (paste-and-save), `/jobs/:id`
  (description edit, extract button, grouped requirements editor, "Mark
  Requirements as Verified"). New components: `JDStatusBadge`,
  `RequirementsEditor`. `api/jobDescriptions.ts` and
  `types/jobDescription.ts` added. Nav link and router updated from the
  old `/job-descriptions` placeholder to `/jobs`.
- **Testing**: 44 new backend tests (96 total) covering extraction logic
  against a fake `AIProvider` (valid responses, markdown-fence
  stripping, malformed JSON, wrong schema, invalid enum values,
  provider-unavailable propagation, normalization), and the full JD API
  (creation, empty-description rejection, extraction with a mocked
  provider, required-vs-preferred importance, malformed AI output,
  AI-unavailable handling - confirmed to return `200`/`needs_review`
  rather than a 500 - corrections, verification, persistence). Also 4
  new frontend tests for the job-creation flow. AI-unavailable behavior
  was additionally confirmed manually against a live server with no
  Ollama process running (a naturally-occurring case in this
  environment, not just a mock).
- **Documentation**: new `docs/ai-architecture.md`; updated
  `docs/api.md`, `docs/database.md`, `docs/architecture.md`,
  `docs/testing.md`, `README.md`.

### Explicitly not included in this sprint

Resume ↔ JD matching, match analysis, AI-assisted tailoring, claim
validation, and DOCX resume generation remain out of scope and are
planned for later sprints.

## [Unreleased - Sprint 2]

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
