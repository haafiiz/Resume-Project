# Development Guide

This document covers day-to-day development workflow, conventions, and
configuration details. For first-time setup, see
[docs/setup.md](./setup.md).

## Running both servers during development

Two terminals, both from the repository root:

```bash
# Terminal 1 — backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm run dev
```

- Backend: http://localhost:8000 (docs at `/docs`, health at `/api/v1/health`)
- Frontend: http://localhost:5173

`--reload` (backend) and Vite's dev server (frontend) both hot-reload on
file changes.

## Environment variables

All configuration is read from environment variables via
`backend/app/config.py` (backed by `pydantic-settings`), which will load
a `backend/.env` file if present. See the root `.env.example` for the
full list with descriptions. Key ones for day-to-day dev:

| Variable | Purpose | Default |
|---|---|---|
| `APP_ENV` | `development` \| `test` \| `production` | `development` |
| `DEBUG` | FastAPI debug mode | `true` |
| `CORS_ORIGINS` | Comma-separated allowed origins | Vite dev server origins |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./storage/app.db` |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Reserved for later AI sprint | — |
| `MAX_UPLOAD_SIZE_MB` / `ALLOWED_UPLOAD_EXTENSIONS` | Reserved for later upload sprint | — |

The frontend reads `VITE_API_BASE_URL` from `frontend/.env` (see
`frontend/.env.example`); it defaults to
`http://localhost:8000/api/v1` if unset.

**Never commit a real `.env` file.** Only `.env.example` files are
tracked in git (enforced by `.gitignore`).

## Project conventions

These carry forward from the project's global rules and apply to every
sprint, not just this one:

1. **Implement incrementally** — don't build ahead of the current
   sprint's scope.
2. **Don't rewrite unrelated code** while working on a feature.
3. **Don't add dependencies** that aren't needed for the task at hand.
4. **Separation of concerns**: API routes are thin; business logic lives
   in `services/` and `core/`; database access is confined to
   `repositories/`.
5. **Pydantic models** are the API contract (`schemas/`) — request and
   response shapes should always be explicit, typed models, not raw
   dicts.
6. **SQLAlchemy** is the only way the app talks to the database, and only
   from `repositories/`.
7. **Tests accompany every major feature** — see
   [docs/testing.md](./testing.md).
8. **Docs are updated whenever architecture changes** — if you add a
   module, route, or table, reflect it in the relevant `docs/*.md` file
   in the same change.
9. **No secrets in code** — environment variables only.
10. **Prefer local/free tools** for V1 (SQLite, local Ollama) — don't
    introduce paid services unless explicitly requested.

## Backend structure quick reference

```
backend/app/
├── main.py            FastAPI app, CORS, lifespan (calls init_db())
├── config.py           Settings — add new env-backed config here
├── database.py         Engine/session/Base — add table imports to
│                        alembic/env.py's target_metadata once models exist
├── api/v1/              Route modules — keep handlers thin
├── models/               SQLAlchemy models (one module per domain concept)
├── schemas/              Pydantic request/response models
├── services/              Use-case orchestration, calls into core/ + repositories/
├── core/                  Domain logic: matching/, ai/, parsing/, generation/
├── repositories/          Data access — the only layer using SQLAlchemy sessions directly
└── utils/                 Shared helpers with no business logic of their own
```

When adding a new route:

1. Define the request/response `schemas/` first.
2. Add the route handler in `api/v1/<name>.py`, register it in
   `api/v1/router.py`.
3. Put orchestration logic in `services/`, not in the route handler.
4. Put any non-trivial business rules in `core/<domain>/`.
5. If it needs persistence, add a `models/` entry and a
   `repositories/<name>_repository.py`, then generate an Alembic
   migration (see below).

## Database migrations

Schema is managed with Alembic, configured in `backend/alembic/` and
`backend/alembic.ini`. The database URL is **not** hardcoded in
`alembic.ini` — `alembic/env.py` loads it from the same `Settings` object
the app uses, so migrations and the running app can never point at
different databases.

Once models exist (Sprint 1 has none yet — `app/models/` is empty), the
workflow will be:

```bash
cd backend
alembic revision --autogenerate -m "add resumes table"
alembic upgrade head
```

## Frontend structure quick reference

```
frontend/src/
├── main.tsx             Entry point, mounts <App />
├── App.tsx               Wires up the router
├── routes/router.tsx      Route table (add new pages/routes here)
├── layout/
│   ├── AppLayout.tsx       Header + nav + <Outlet />
│   └── Navigation.tsx      Top nav links
├── pages/                  One file per top-level page
├── api/client.ts            Fetch wrapper — add new API functions here
└── test/setup.ts             Vitest/RTL global setup
```

Styling uses Tailwind CSS v4 (CSS-first config via `@import "tailwindcss"`
in `src/index.css` — there is no `tailwind.config.js` to edit for basic
utility usage). Keep to utility classes; avoid introducing a separate
component styling system.

## Linting

The frontend ships with `oxlint`:

```bash
cd frontend
npm run lint
```
