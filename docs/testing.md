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

**What's covered:**

- `test_health.py` — `GET /api/v1/health` returns `{"status": "ok"}`,
  and the root `/` endpoint responds.
- `test_database.py` — the SQLAlchemy engine connects, a session can
  execute a query, and `init_db()` runs without error.
- `test_docx_parser.py` / `test_pdf_parser.py` — text extraction from
  DOCX/PDF bytes, including invalid-file and empty-document cases.
- `test_resume_parser.py` — structured extraction (skills, experience,
  education, projects, certifications) from raw text, including
  multi-entry splitting and regression tests for two real bugs found
  during manual testing (experience entries bleeding into each other;
  a project description sentence being mistaken for the next project's
  name).
- `test_upload_validation.py` — extension, size, empty-file,
  missing/unsafe-filename, and signature-mismatch rejection.
- `test_resume_api.py` — end-to-end API coverage: upload (valid DOCX/PDF,
  unsupported type, oversized, empty document, zero-byte file), profile
  retrieval, updates (corrections replace sections and flip
  `source`/`verified`), and verification (state transition, idempotency,
  and the 409 lock against editing a verified resume).
- `test_jd_extraction.py` — `extract_requirements()` tested directly
  against a `FakeProvider` test double (no network, no real Ollama
  required): valid responses, markdown-fence stripping, malformed JSON,
  wrong-shaped JSON, invalid enum values, provider-unavailable
  propagation, and `normalize_name()` behavior.
- `test_jd_api.py` — end-to-end API coverage: JD creation (with/without
  optional title/company, empty-description rejection), extraction with
  a fake AI provider injected via monkeypatching
  `app.services.jd_service.get_ai_provider` (valid extraction,
  normalization, required-vs-preferred importance, source_text
  presence), malformed AI output and AI-unavailable handling (both
  confirmed to return `200`/`needs_review` rather than a server error),
  corrections, verification state machine, and persistence across
  requests.

Test fixtures for DOCX/PDF files are built in
`tests/backend/helpers/pdf_docx_builders.py` rather than checked-in
binary files, so fixtures stay easy to read/modify in review, and PDFs
are hand-assembled as minimal valid byte streams rather than pulling in
a PDF-generation library as a test-only dependency.

`tests/backend/conftest.py` also resets the database schema and the
upload directory before every test function, so tests never see data
left over from a previous test.

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

**What's covered:**

- `App.test.tsx` — renders the full app shell (router + layout), asserts
  the navigation links for all four sections are present, asserts the
  Dashboard heading renders by default, and waits for the mocked backend
  health check to resolve to "connected". The real `api/client` module is
  mocked (`vi.mock("./api/client", ...)`) so this test never depends on a
  running backend.
- `pages/ResumeNew.test.tsx` — renders the upload prompt, simulates
  selecting a file and asserts a successful upload navigates to the new
  resume's detail page, and asserts a failed upload (mocked `ApiError`)
  surfaces the error message inline. `api/resumes` is mocked so no real
  network call is made.
- `pages/JobNew.test.tsx` — renders the form, rejects submission with an
  empty description without calling the API, saves a job description
  and navigates to its detail page on success, and surfaces an inline
  error message on failure. `api/jobDescriptions` is mocked.

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
