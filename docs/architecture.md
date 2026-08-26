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

This is the target flow the foundation is built to support. None of the
parsing/matching/AI/validation stages exist yet as of Sprint 1.

```
Resume            →  Parse  →  Structured Resume  →  User Review  →  Verified Resume Profile
Job Description    →  Parse  →  Structured JD Requirements

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

## AI abstraction (established now, implemented later)

The rest of the application must never depend on a specific AI vendor.
All AI calls will go through an `AIProvider` interface:

```
AIProvider
├── OllamaProvider       (local, used for V1)
├── OpenAIProvider       (future)
└── GeminiProvider       (future)
```

Sprint 1 only reserves configuration for this (`OLLAMA_BASE_URL`,
`OLLAMA_MODEL` in `.env.example`) and the `core/ai/` package location.
No provider code exists yet.

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
│   │       └── router.py
│   ├── models/             SQLAlchemy ORM models (empty in Sprint 1)
│   ├── schemas/             Pydantic request/response contracts
│   ├── services/            Orchestration / use-case logic
│   ├── core/                 Core business logic, organized by domain:
│   │   ├── matching/         (future) resume ↔ JD matching engine
│   │   ├── ai/                (future) AIProvider abstraction + providers
│   │   ├── parsing/           (future) resume/JD parsing
│   │   └── generation/        (future) DOCX generation
│   ├── repositories/        Data-access layer (only layer touching the DB directly)
│   └── utils/                 Shared helpers
├── alembic/                 Migrations (configured, no schema yet)
└── tests/                    (backend tests actually live in /tests/backend, see below)
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
│   ├── pages/                  One placeholder page per top-level section:
│   │   ├── Dashboard.tsx        (also shows live backend connectivity)
│   │   ├── Resumes.tsx
│   │   ├── JobDescriptions.tsx
│   │   └── Analysis.tsx
│   ├── api/client.ts            Minimal fetch wrapper, reads VITE_API_BASE_URL
│   └── test/setup.ts             Vitest + jest-dom setup
```

## Testing layout

```
tests/
└── backend/          pytest suite (health endpoint, database init)
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

## What Sprint 1 deliberately does NOT include

- No resume or JD parsing
- No AI provider implementation
- No matching, tailoring, or validation engines
- No application database schema/tables (only the connection machinery)
- No authentication

These are all planned in later sprints and are called out as "future" in
the module layout above so the codebase's intended shape is visible even
before the code exists.
