# Architecture

## Purpose

The Resume Tailoring Platform is a **truth-constrained** resume tailoring
and job-description matching tool. The user's verified resume profile is
the only source of truth for factual claims about the candidate. The job
description describes what an employer wants — it is never treated as
evidence that the candidate has a given skill. The system is designed so
that no component can silently invent skills, experience, or metrics on
the user's behalf.

This document describes the architecture established in **Sprint 1**
(project foundation). Later sprints will extend it with parsing,
matching, AI-assisted tailoring, and validation — this document will be
updated as each of those lands.

## High-level shape

The project is a **modular monolith**:

```
React UI  →  REST API  →  FastAPI  →  Services  →  Core business logic  →  Repositories  →  SQLite
```

- The frontend never talks to the database or AI provider directly — only
  to the backend's REST API.
- API routes are thin: they validate input/output via Pydantic schemas
  and delegate to services.
- Business logic lives in `services/` and `core/`, not in route handlers.
- Data access goes through `repositories/`, which are the only layer
  allowed to speak SQLAlchemy directly to the database.

## Planned end-to-end data flow

This is the target flow the foundation is built to support.
**Implemented:** resume upload/parse/review/verify (Sprint 2), JD
save/extract/review/verify (Sprint 3), and deterministic resume↔JD
matching (Sprint 4) - everything through "Match Analysis" below.
Tailoring and validation remain unimplemented.

```
Resume            →  Parse  →  Structured Resume  →  User Review  →  Verified Resume Profile          [implemented, Sprint 2]
Job Description    →  Parse  →  Structured JD Requirements                                              [implemented, Sprint 3]

Verified Resume Profile + JD Requirements
    →  Matching Engine                                                                                  [implemented, Sprint 4]
    →  Match Analysis                                                                                    [implemented, Sprint 4]
    →  Tailoring Engine
    →  Structured AI Output
    →  Validation Engine
    →  Resume Generator
    →  DOCX
```

The key architectural rule behind this flow: **the LLM never generates
the final resume directly**. AI output is always structured, and always
passes through a deterministic claim-validation step before a DOCX is
generated. This is what keeps the system truth-constrained even though
it uses an LLM.

## AI abstraction

The rest of the application must never depend on a specific AI vendor.
All AI calls go through an `AIProvider` interface:

```
AIProvider
├── OllamaProvider       (implemented, Sprint 3)
├── OpenAIProvider       (future)
└── GeminiProvider       (future)
```

Resume parsing (Sprint 2) deliberately **does not** use an LLM at all -
see [docs/resume-processing.md](./resume-processing.md#why-parsing-is-deterministic-not-llm-based)
for why. Job description requirement extraction (Sprint 3) is the first
feature to actually call an LLM, and does so entirely through the
generic `AIProvider` interface (`app/core/ai/base.py`) - `JDService`
never imports `OllamaProvider` directly. See
[docs/ai-architecture.md](./ai-architecture.md) for the full design:
the provider interface, prompt construction, structured-output
validation, and how AI failures (unavailable / malformed response) are
handled without ever failing the request outright.

## Backend layout

```
backend/
├── app/
│   ├── main.py            FastAPI app instance, CORS, router mounting
│   ├── config.py          Settings (env-var based, pydantic-settings)
│   ├── database.py        SQLAlchemy engine/session/Base + init_db()
│   ├── api/                REST routes (thin — delegate to services)
│   │   └── v1/
│   │       ├── health.py
│   │       ├── resumes.py            upload, list, profile, update, verify
│   │       ├── job_descriptions.py     create, list, get, extract, update, verify
│   │       ├── analyses.py               create, get, get matches
│   │       └── router.py
│   ├── models/              SQLAlchemy ORM models
│   │   ├── resume.py          Resume, ResumeSection, Skill, Experience,
│   │   │                        Project, Education, Certification
│   │   ├── job_description.py   JobDescription, JDRequirement
│   │   └── analysis.py            Analysis, SkillMatch
│   ├── schemas/               Pydantic request/response contracts
│   │   ├── resume.py
│   │   ├── job_description.py
│   │   └── analysis.py
│   ├── services/                Orchestration / use-case logic
│   │   ├── resume_service.py      upload→parse→persist, update, verify
│   │   ├── jd_service.py            save→extract→persist, update, verify
│   │   └── analysis_service.py        verify inputs→match→score→persist
│   ├── core/                       Core business logic, organized by domain:
│   │   ├── matching/                 deterministic resume↔JD matching:
│   │   │   ├── normalizer.py           controlled alias table (never fuzzy)
│   │   │   ├── matcher.py                per-requirement classification +
│   │   │   │                              full-analysis orchestration
│   │   │   └── scorer.py                   weighted category scoring
│   │   ├── ai/                        AIProvider abstraction + JD extraction:
│   │   │   ├── base.py                  AIProvider ABC + exception types
│   │   │   ├── ollama_provider.py         Ollama HTTP client
│   │   │   ├── factory.py                   settings -> AIProvider instance
│   │   │   ├── schemas.py                     structured AI-output contract
│   │   │   └── jd_extraction.py                 prompt + response validation
│   │   ├── parsing/                    resume parsing (deterministic, no LLM):
│   │   │   ├── docx_parser.py            DOCX bytes -> text
│   │   │   ├── pdf_parser.py               PDF bytes -> text
│   │   │   └── resume_parser.py              text -> structured sections/fields
│   │   └── generation/                  (future) DOCX generation
│   ├── repositories/                 Data-access layer (only layer touching the DB directly)
│   │   ├── resume_repository.py
│   │   ├── jd_repository.py
│   │   └── analysis_repository.py
│   └── utils/                          Shared helpers
│       ├── file_storage.py               safe on-disk storage under storage/uploads/
│       ├── upload_validation.py            filename/extension/signature/size checks
│       └── text_normalization.py             deterministic name normalization
├── alembic/                          Migrations (resume tables in Sprint 2, JD tables
│                                       in Sprint 3, analysis tables in Sprint 4)
└── tests/                             (backend tests actually live in /tests/backend, see below)
```

## Frontend layout

```
frontend/
├── src/
│   ├── main.tsx              Entry point
│   ├── App.tsx                Mounts the router
│   ├── routes/router.tsx      Route table
│   ├── layout/
│   │   ├── AppLayout.tsx       Header + nav + <Outlet />
│   │   └── Navigation.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx        Shows live backend connectivity
│   │   ├── Resumes.tsx            List of uploaded resumes
│   │   ├── ResumeNew.tsx            Upload flow (/resumes/new)
│   │   ├── ResumeDetail.tsx           Profile view/edit/verify (/resumes/:id)
│   │   ├── Jobs.tsx                     List of job descriptions (/jobs)
│   │   ├── JobNew.tsx                     Paste-and-save flow (/jobs/new)
│   │   ├── JobDetail.tsx                    Extract/review/edit/verify (/jobs/:id)
│   │   ├── Analysis.tsx                       Verified resume+JD picker (/analysis)
│   │   └── AnalysisDetail.tsx                   Score + matches view (/analysis/:id)
│   ├── components/
│   │   ├── resume/               Section editors used by ResumeDetail:
│   │   │   ├── UploadForm.tsx      drag-and-drop / click-to-browse
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── SkillsEditor.tsx
│   │   │   ├── ExperienceEditor.tsx
│   │   │   ├── ProjectEditor.tsx
│   │   │   ├── EducationEditor.tsx
│   │   │   ├── CertificationEditor.tsx
│   │   │   └── editorStyles.ts       shared Tailwind class constants (reused by job/, analysis/)
│   │   ├── job/                  Used by JobDetail:
│   │   │   ├── JDStatusBadge.tsx
│   │   │   └── RequirementsEditor.tsx  grouped-by-type add/remove/edit list
│   │   └── analysis/             Used by AnalysisDetail:
│   │       ├── OverallScoreCard.tsx  big score + category breakdown
│   │       ├── ScoreBar.tsx            one category's weighted score bar
│   │       └── MatchList.tsx             matched/partial/missing/extra-skills groups
│   ├── types/
│   │   ├── resume.ts             TypeScript types mirroring backend resume schemas
│   │   ├── jobDescription.ts       TypeScript types mirroring backend JD schemas
│   │   └── analysis.ts               TypeScript types mirroring backend analysis schemas
│   ├── api/
│   │   ├── client.ts               Shared fetch wrapper + ApiError
│   │   ├── resumes.ts                Resume-specific endpoint calls
│   │   ├── jobDescriptions.ts          JD-specific endpoint calls
│   │   └── analyses.ts                   Analysis-specific endpoint calls
│   └── test/setup.ts             Vitest + jest-dom setup
```

## Testing layout

```
tests/
└── backend/          pytest suite: health, database, DOCX/PDF parsing,
                        structured resume parsing, upload validation,
                        resume CRUD/update/verification, JD extraction
                        logic (fake AIProvider), JD CRUD/extraction API,
                        malformed-AI-output and AI-unavailable handling,
                        matching engine (normalizer/matcher/scorer unit
                        tests incl. mandatory false-positive pairs), and
                        analysis API (creation, verification guard,
                        acceptance-criteria scenario, reproducibility)
    └── helpers/         test-only fixture builders (DOCX/PDF file bytes)
```

Frontend tests are colocated with source (`frontend/src/*.test.tsx`) since
that is the idiomatic Vitest/React Testing Library convention and keeps
component tests next to the component they exercise. Backend tests live
in the shared top-level `tests/` directory per the project's repository
structure convention.

## Configuration & CORS

All configuration is environment-variable based (`app/config.py`, backed
by `pydantic-settings`). Nothing is hardcoded, and no real secrets are
committed — only `.env.example` is tracked in git.

CORS is also environment-driven (`CORS_ORIGINS`), defaulting to the Vite
dev server's origin in development. Production deployments are expected
to set a locked-down `CORS_ORIGINS` value via the environment.

## What's still not implemented (as of Sprint 4)

- No AI-assisted tailoring
- No claim validation engine
- No DOCX resume generation
- No authentication

These are planned in later sprints.
