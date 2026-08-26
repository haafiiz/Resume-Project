# Setup

This guide takes a developer who has never seen the project from a clean
checkout to a running frontend and backend.

## Prerequisites

- **Python** 3.10+ (developed/tested with 3.12)
- **Node.js** 18+ and **npm** (developed/tested with Node 22)
- No external services required — V1 uses SQLite (file-based, no server)
  and, once AI features land in a later sprint, a locally running
  [Ollama](https://ollama.com) instance.

## 1. Clone and inspect

```bash
cd resume-tailor
```

You should see:

```
resume-tailor/
├── backend/
├── frontend/
├── tests/
├── docs/
├── storage/
├── README.md
├── CHANGELOG.md
├── .gitignore
└── .env.example
```

## 2. Environment variables

Copy the example environment file into the backend directory (this is
where the app currently reads it from):

```bash
cp .env.example backend/.env
```

The defaults in `.env.example` work out of the box for local development
— you don't need to change anything to get started. See
[docs/development.md](./development.md) for what each variable does.

## 3. Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --reload
```

The backend starts on **http://localhost:8000**. On startup it will
create the SQLite database file (`backend/storage/app.db`) automatically
if it doesn't already exist.

Verify it's alive:

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok"}
```

Interactive API docs are available at http://localhost:8000/docs.

## 4. Frontend setup

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend starts on **http://localhost:5173** (Vite's default) and
is already configured (via `frontend/.env` / `VITE_API_BASE_URL`, see
`frontend/.env.example`) to call the backend at
`http://localhost:8000/api/v1`.

Open http://localhost:5173 in a browser. The Dashboard page shows a
"Backend API: connected" indicator once it successfully reaches
`/api/v1/health` — this is the quickest way to confirm both halves of
the stack are talking to each other.

## 5. Run the tests

Backend (from `backend/`, with the virtualenv active):

```bash
pytest
```

Frontend (from `frontend/`):

```bash
npm test
```

Both should pass on a clean checkout. See
[docs/testing.md](./testing.md) for details on what's covered and how to
add new tests.

## Troubleshooting

If something doesn't start as expected, see the "Troubleshooting" section
of the root `README.md`, and double-check [docs/development.md](./development.md)
for the environment variables and ports each part of the stack expects.
