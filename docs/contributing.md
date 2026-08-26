# Contributing

## Before you start

Read [docs/architecture.md](./architecture.md) first — this project has
one non-negotiable rule that shapes every design decision:

> The user's verified resume profile is the only source of truth for
> factual claims about the candidate. The job description is never
> treated as evidence the candidate has a skill. Nothing in this system
> should ever invent, assume, or extrapolate a claim about the candidate.

Any change that risks blurring that line — for example, code that could
cause AI-suggested content to bypass the (future) validation engine and
reach the final document unchecked — should be treated as a serious
architectural concern, not a minor implementation detail.

## Sprint-based workflow

This project is developed sprint by sprint, each with an explicit,
bounded scope. When working on a sprint:

1. **Inspect first.** Before writing code, look at what already exists
   in the repository, and confirm your understanding of current state.
2. **Explain the plan.** Identify which files will be created or
   modified, and describe the implementation approach, before
   implementing.
3. **Implement incrementally**, within the sprint's stated scope only.
   Don't pull forward work from a later sprint, even if it seems small.
4. **Don't rewrite unrelated code** as a side effect of an unrelated
   change.
5. **After implementing:** run the tests, report what passed/failed,
   update documentation, summarize the files changed, and explain how to
   manually verify the feature. Don't move on to the next sprint
   automatically — wait for confirmation.

## Code conventions

- **Backend:** FastAPI + Pydantic + SQLAlchemy + Alembic. Routes are
  thin; business logic goes in `services/`/`core/`; database access is
  confined to `repositories/`. See
  [docs/development.md](./development.md#backend-structure-quick-reference)
  for the full layout.
- **Frontend:** React + TypeScript + Vite + Tailwind CSS. Pages live in
  `src/pages/`, shared chrome in `src/layout/`, API calls centralized in
  `src/api/`.
- **No unnecessary dependencies.** Justify any new dependency in the PR
  description.
- **No secrets in code or in git.** Configuration is env-var based; only
  `.env.example` files are committed.
- **No paid services** unless explicitly requested by the project owner.

## Tests

Every major feature needs tests. See [docs/testing.md](./testing.md) for
how to run and where to add backend (pytest) and frontend (Vitest + RTL)
tests. A sprint isn't complete until its tests pass.

## Documentation

Documentation is part of the implementation, not an afterthought. If a
change affects architecture, setup, the API surface, the database
schema, the AI flow, the matching engine, or the validation engine,
update the corresponding file under `docs/` in the same change. Update
`CHANGELOG.md` for every sprint/feature landed, and keep `README.md`
accurate for a first-time setup.

## Commit hygiene

- Keep commits scoped to the sprint/feature being worked on.
- Write commit messages that describe *what* changed and *why*, not just
  "update files".
- Don't commit generated artifacts (`node_modules/`, `.venv/`, `*.db`,
  `dist/`) — these are covered by `.gitignore`.
