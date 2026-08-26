# Testing

## Backend

**Framework:** pytest, with FastAPI's `TestClient` for HTTP-level tests.

**Location:** `tests/backend/` (top-level, not nested under `backend/`),
configured via `backend/pytest.ini` (`testpaths = ../tests/backend`).

**Run:**

```bash
cd backend
source .venv/bin/activate
pytest            # or: pytest -v
```

**Isolation:** `tests/backend/conftest.py` points the app at a dedicated
`sqlite:///./storage/test.db` via the `DATABASE_URL` environment variable
before anything imports `app.config`, so test runs never touch the
developer's real `storage/app.db`.

**What's covered in Sprint 1:**

- `test_health.py` — `GET /api/v1/health` returns `{"status": "ok"}`,
  and the root `/` endpoint responds.
- `test_database.py` — the SQLAlchemy engine connects, a session can
  execute a query, and `init_db()` runs without error.

**Adding tests for a new feature:** create a new module in
`tests/backend/`, named `test_<feature>.py`. Use `TestClient(app)` for
route-level tests; for anything touching the database, prefer testing
through the `repositories/` or `services/` layer directly over
round-tripping through HTTP where possible, to keep tests fast and
focused.

## Frontend

**Framework:** Vitest + React Testing Library (`@testing-library/react`,
`@testing-library/jest-dom`, `@testing-library/user-event`), running in
a `jsdom` environment.

**Location:** colocated with source, e.g. `frontend/src/App.test.tsx`.
This is the standard Vitest/RTL convention and keeps a component's test
next to the component itself.

**Run:**

```bash
cd frontend
npm test            # runs `vitest run` (single pass, CI-friendly)
```

For a watch-mode loop while developing: `npx vitest`.

**What's covered in Sprint 1:**

- `App.test.tsx` — renders the full app shell (router + layout), asserts
  the navigation links for all four sections are present, asserts the
  Dashboard heading renders by default, and waits for the mocked backend
  health check to resolve to "connected". The real `api/client` module is
  mocked (`vi.mock("./api/client", ...)`) so this test never depends on a
  running backend.

**Adding tests for a new feature:** place `<Component>.test.tsx` next to
the component. Mock `api/client` functions rather than hitting a real
network in unit tests; reserve real backend calls for manual/integration
testing during development (see [docs/setup.md](./setup.md) for how to
run both servers together).

## Manually verifying the full stack

Beyond automated tests, the quickest end-to-end sanity check is:

1. Start the backend (`uvicorn app.main:app --reload` from `backend/`).
2. Start the frontend (`npm run dev` from `frontend/`).
3. Open http://localhost:5173 — the Dashboard should show
   **"Backend API: connected"**.
4. `curl http://localhost:8000/api/v1/health` should return
   `{"status":"ok"}`.

If the Dashboard shows "unreachable", check `VITE_API_BASE_URL` in
`frontend/.env` and `CORS_ORIGINS` in `backend/.env` — see
[docs/development.md](./development.md).
