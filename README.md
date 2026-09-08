# Resume Tailoring Platform

A **truth-constrained** resume tailoring and job-description matching
platform. It takes a candidate's existing resume and a job description
and produces a tailored resume optimized for that JD — without ever
inventing skills, experience, titles, metrics, or anything else the
candidate hasn't actually verified.

## Why "truth-constrained"?

Most AI resume tools will happily rewrite a resume to match a job
description, quietly fabricating whatever the JD asks for along the way.
This platform is built around the opposite principle:

- The user's **verified resume profile** is the only source of truth
  about the candidate.
- The **job description** describes what the employer wants — it is
  never treated as evidence the candidate possesses those skills.
- If something can't be verified against the resume, it gets **flagged
  for review**, never invented.
- The LLM never writes the final resume directly. AI output is always
  structured and passes through a deterministic **validation engine**
  before anything is generated.

See [docs/architecture.md](./docs/architecture.md) for the full design.

## Project status

This repository currently implements:

- **Sprint 1 — Project Foundation**: working, tested frontend/backend
  skeleton with health-check connectivity, database wiring, and full
  developer documentation.
- **Sprint 2 — Resume Upload and Processing**: upload a PDF or DOCX
  resume, deterministic (no-LLM) parsing into structured
  skills/experience/education/projects/certifications, a review UI to
  correct extracted data, and an explicit verification step. See
  [docs/resume-processing.md](./docs/resume-processing.md).
- **Sprint 3 — Job Description Processing**: paste a job description,
  save it, run AI-based (Ollama) requirement extraction into 9
  structured categories with required/preferred/nice-to-have importance,
  review and correct the results, and verify. See
  [docs/ai-architecture.md](./docs/ai-architecture.md).
- **Sprint 4 — Resume/JD Matching Engine**: deterministic (no-LLM)
  matching of a verified resume against a verified job description,
  with a transparent exact/normalized/related/partial/missing/unknown
  classification for every requirement, a configurable weighted score,
  and full explanations. See
  [docs/matching-engine.md](./docs/matching-engine.md).

AI-assisted tailoring, claim validation, and DOCX generation are **not
yet implemented** — see [CHANGELOG.md](./CHANGELOG.md) for progress.

## Technology stack

**Frontend:** React, TypeScript, Vite, Tailwind CSS, React Router
**Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic
**Database:** SQLite (V1)
**Document parsing:** python-docx (DOCX), pypdf (PDF) — deterministic
extraction, no LLM involved (see [docs/resume-processing.md](./docs/resume-processing.md))
**AI:** Ollama (local LLM), accessed through an `AIProvider` abstraction
(see [docs/ai-architecture.md](./docs/ai-architecture.md)) so other
providers can be added later without touching the rest of the app
**Testing:** Pytest (backend), Vitest + React Testing Library (frontend)

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- (Later sprints only) a locally running [Ollama](https://ollama.com) instance

## Quick start

```bash
# 1. Environment variables
cp .env.example backend/.env

# 2. Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://localhost:8000  (docs at /docs, health at /api/v1/health)

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

Open http://localhost:5173 — the Dashboard page shows a live
"Backend API: connected" indicator once the frontend successfully
reaches the backend's health endpoint. Go to **Resumes → Upload resume**
to try the resume upload/parsing/review/verify flow (PDF and DOCX
supported), **Job Descriptions → Add job description** to try the
paste/save/extract/review/verify flow for job postings (requires a
running [Ollama](https://ollama.com) instance for extraction to
actually find requirements — without one, extraction still completes
gracefully and flags the job description for manual review), or
**Analysis** to compare a verified resume against a verified job
description and see a transparent, reproducible match score.

Full walkthrough: [docs/setup.md](./docs/setup.md).

## Running tests

```bash
# Backend
cd backend && source .venv/bin/activate && pytest

# Frontend
cd frontend && npm test
```

See [docs/testing.md](./docs/testing.md) for what's covered and how to
add new tests.

## Repository structure

```
resume-tailor/
├── frontend/          React + TypeScript + Vite + Tailwind app
├── backend/            FastAPI + SQLAlchemy + Alembic API
│   └── storage/           uploads/ (resume files) + app.db (SQLite) - gitignored
├── tests/backend/       Backend pytest suite (+ helpers/ fixture builders)
├── docs/                 Architecture, setup, development, resume processing,
│                          database, API reference, testing, contributing
├── storage/               Shared file storage (reserved for future use)
├── .env.example            Documented environment variables
└── .gitignore
```

## Documentation

- [docs/architecture.md](./docs/architecture.md) — system design, data flow, AI abstraction
- [docs/setup.md](./docs/setup.md) — first-time setup, step by step
- [docs/development.md](./docs/development.md) — day-to-day workflow, conventions, env vars
- [docs/resume-processing.md](./docs/resume-processing.md) — upload, parsing, and verification flow
- [docs/ai-architecture.md](./docs/ai-architecture.md) — AIProvider abstraction and JD extraction
- [docs/matching-engine.md](./docs/matching-engine.md) — deterministic matching algorithm and scoring
- [docs/database.md](./docs/database.md) — schema and relationships
- [docs/api.md](./docs/api.md) — REST API reference
- [docs/testing.md](./docs/testing.md) — running and writing tests
- [docs/contributing.md](./docs/contributing.md) — contribution workflow and rules

## License

Not yet specified.
