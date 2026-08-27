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
**Implemented as of Sprint 2:** resume upload, parsing, structured
storage, and user review/verification (the first line below). Job
description parsing, matching, tailoring, and validation remain
unimplemented.

```
Resume            →  Parse  →  Structured Resume  →  User Review  →  Verified Resume Profile   [implemented, Sprint 2]
Job Description    →  Parse  →  Structured JD Requirements                                       [not yet implemented]

Verified Resume Profile + JD Requirements
    →  Matching Engine
    →  Match Analysis
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

## AI abstraction (reserved, not yet implemented)

The rest of the application must never depend on a specific AI vendor.
All AI calls will go through an `AIProvider` interface:

```
AIProvider
├── OllamaProvider       (local, used for V1)
├── OpenAIProvider       (future)
└── GeminiProvider       (future)
```

As of Sprint 2, resume parsing is fully implemented and deliberately
**does not** use an LLM at all - see
[docs/resume-processing.md](./resume-processing.md#why-parsing-is-deterministic-not-llm-based)
for why. The `AIProvider` abstraction remains reserved configuration
(`OLLAMA_BASE_URL`, `OLLAMA_MODEL`) and the `core/ai/` package location
for a later sprint (matching/tailoring), where an LLM's structured
output will still pass through deterministic validation before ever
reaching a generated document.

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
│   │       ├── resumes.py    upload, list, profile, update, verify
│   │       └── router.py
│   ├── models/              SQLAlchemy ORM models
│   │   └── resume.py          Resume, ResumeSection, Skill, Experience,
│   │                            Project, Education, Certification
│   ├── schemas/               Pydantic request/response contracts
│   │   └── resume.py
│   ├── services/                Orchestration / use-case logic
│   │   └── resume_service.py      upload→parse→persist, update, verify
│   ├── core/                       Core business logic, organized by domain:
│   │   ├── matching/                 (future) resume ↔ JD matching engine
│   │   ├── ai/                        (future) AIProvider abstraction + providers
│   │   ├── parsing/                    resume/JD parsing — resume side implemented:
│   │   │   ├── docx_parser.py            DOCX bytes -> text
│   │   │   ├── pdf_parser.py               PDF bytes -> text
│   │   │   └── resume_parser.py              text -> structured sections/fields
│   │   └── generation/                  (future) DOCX generation
│   ├── repositories/                 Data-access layer (only layer touching the DB directly)
│   │   └── resume_repository.py
│   └── utils/                          Shared helpers
│       ├── file_storage.py               safe on-disk storage under storage/uploads/
│       └── upload_validation.py            filename/extension/signature/size checks
├── alembic/                          Migrations (resume domain tables added in Sprint 2)
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
│   │   ├── JobDescriptions.tsx          Placeholder
│   │   └── Analysis.tsx                   Placeholder
│   ├── components/resume/       Section editors used by ResumeDetail:
│   │   ├── UploadForm.tsx          drag-and-drop / click-to-browse
│   │   ├── StatusBadge.tsx
│   │   ├── SkillsEditor.tsx
│   │   ├── ExperienceEditor.tsx
│   │   ├── ProjectEditor.tsx
│   │   ├── EducationEditor.tsx
│   │   ├── CertificationEditor.tsx
│   │   └── editorStyles.ts           shared Tailwind class constants
│   ├── types/resume.ts           TypeScript types mirroring backend schemas
│   ├── api/
│   │   ├── client.ts               Shared fetch wrapper + ApiError
│   │   └── resumes.ts                Resume-specific endpoint calls
│   └── test/setup.ts             Vitest + jest-dom setup
```

## Testing layout

```
tests/
└── backend/          pytest suite: health, database, DOCX/PDF parsing,
                        structured resume parsing, upload validation,
                        resume CRUD/update/verification
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

## What's still not implemented (as of Sprint 2)

- No JD parsing
- No AI provider implementation
- No matching, tailoring, or validation engines
- No DOCX resume generation
- No authentication

These are planned in later sprints.
