# Sprint 3 — Manual Test Cases

**Scope:** Job description creation, AI-based requirement extraction, review/edit, and verification. Covers the `POST/GET/PUT /job-descriptions` API and the `/jobs`, `/jobs/new`, `/jobs/:id` frontend pages.

**Prerequisites:**
- Backend running with a clean/migrated database (`alembic upgrade head`)
- Frontend running, pointed at the backend
- A sample job description with clear, varied requirement language (some "must have", some "preferred", some "nice to have") ready to paste
- **Optional but recommended:** a running local Ollama instance with a model pulled (set `OLLAMA_BASE_URL`/`OLLAMA_MODEL` accordingly) to exercise the real extraction path. Every test in this document also works correctly **without** Ollama running — the "AI unavailable" path is a first-class, expected outcome, not a bug — so testers without Ollama installed can still complete this whole document; just expect `needs_review` instead of `extracted` wherever extraction succeeding is called out.

Each test case lists **Preconditions**, **Steps**, and **Expected Result**. Cases marked "(API)" can be run with curl/Postman/the `/docs` Swagger UI; "(UI)" cases are run in the browser.

---

## 1. Creating a job description

### TC-1.1 — Create with title, company, and description (API)
**Steps:** `POST /api/v1/job-descriptions` with a JSON body containing `title`, `company`, and a non-empty `description`.
**Expected:** `201 Created`. Response echoes `title`/`company`/`description`, `status` is `"created"`, `requirements` is an empty array.

### TC-1.2 — Create with only description (title/company omitted) (API)
**Steps:** `POST /api/v1/job-descriptions` with only `{"description": "..."}`.
**Expected:** `201 Created`. `title` and `company` are `null` in the response — confirms both are genuinely optional.

### TC-1.3 — Reject empty description (API)
**Steps:** `POST /api/v1/job-descriptions` with `{"description": ""}`.
**Expected:** `422 Unprocessable Entity` (Pydantic validation error naming the `description` field).

### TC-1.4 — Reject missing description field entirely (API)
**Steps:** `POST /api/v1/job-descriptions` with `{"title": "Some role"}` and no `description` key at all.
**Expected:** `422 Unprocessable Entity`.

### TC-1.5 — Create a job description in the UI (UI)
**Steps:** Navigate to `/jobs/new`. Fill in title and company (optional), paste a full job description into the text area, click **Save job description**.
**Expected:** Navigates to `/jobs/:id`. Page shows the entered title/company, the pasted description, and status badge "Saved".

### TC-1.6 — Reject empty description in the UI (UI)
**Steps:** On `/jobs/new`, leave the description blank and click **Save job description**.
**Expected:** Inline error message shown ("Please paste the job description text before saving."). Page stays on `/jobs/new` — no API call made, no navigation.

---

## 2. Extraction

### TC-2.1 — Extract with a real Ollama instance running (API) — *requires Ollama*
**Steps:** Create a JD (TC-1.1) with a description containing clearly stated requirements ("Must have 3+ years of Python", "Preferred: Docker", "Nice to have: Kubernetes", a degree requirement, a soft skill). `POST /job-descriptions/{id}/extract`.
**Expected:** `200 OK`. `status` becomes `"extracted"`. `requirements` array is populated with items whose `requirement_type`, `name`, `importance`, and `source_text` plausibly match the source text. Every requirement has a non-null `source_text` that is an actual excerpt from the description (not empty, not fabricated wording).

### TC-2.2 — Extraction request succeeds even without Ollama running (API)
**Steps:** With no Ollama process running (or `OLLAMA_BASE_URL` pointed at a non-existent host), create a JD and `POST /job-descriptions/{id}/extract`.
**Expected:** `200 OK` — **not** a 500 or a timeout error surfaced to the client. `status` is `"needs_review"`. `extraction_error` is a human-readable message mentioning the AI service is unavailable and suggesting retry or manual entry. `requirements` is an empty array.

### TC-2.3 — Extract in the UI without Ollama running (UI)
**Steps:** Create a JD via `/jobs/new`. On its detail page, click **Extract requirements**.
**Expected:** Button shows "Extracting…" while in flight, then completes without a crash or unhandled error screen. Status badge updates to "Needs review". An amber message box shows the extraction error explanation. Description and other fields remain intact and editable.

### TC-2.4 — Extract in the UI with Ollama running (UI) — *requires Ollama*
**Steps:** Same as TC-2.3 but with Ollama available.
**Expected:** Status badge updates to "Extracted". A confirmation message states how many requirements were found. The Requirements section, grouped by type, shows the extracted items.

### TC-2.5 — Required vs. preferred vs. nice-to-have importance is distinguished (API) — *requires Ollama, or use TC-3.2's manual entry as a substitute*
**Steps:** Extract a JD whose description has at least one clearly "must have" item, one "preferred" item, and one "nice to have" item.
**Expected:** The corresponding requirements in the response have `importance` values `"required"`, `"preferred"`, and `"nice_to_have"` respectively — not all defaulted to the same value.

### TC-2.6 — Extraction on a JD with vague/no explicit requirements (API) — *requires Ollama*
**Steps:** Create a JD with a description that has no concrete requirements (e.g. a single vague marketing sentence). Extract.
**Expected:** `200 OK`. Either `requirements` is empty with `status: "needs_review"` and an explanatory `extraction_error` ("found no identifiable requirements"), or a very short list — but never fabricated specifics (e.g. never a "5+ years experience" requirement appearing from a description that states no years at all).

### TC-2.7 — Extraction on a missing JD returns 404 (API)
**Steps:** `POST /job-descriptions/does-not-exist/extract`.
**Expected:** `404 Not Found`.

### TC-2.8 — Re-extraction replaces the previous requirement list (API) — *requires Ollama*
**Steps:** Extract a JD once. Edit the description via `PUT`. Extract again.
**Expected:** The second extraction's `requirements` array reflects only the new extraction — no duplicate/stale items from the first pass persist alongside the new ones.

---

## 3. Review and correction

### TC-3.1 — View requirements grouped by type (UI)
**Steps:** On a JD detail page with extracted (or manually entered) requirements, observe the Requirements section.
**Expected:** Items are grouped under headings for each of the 9 requirement types (Required skill, Preferred skill, Technology, Responsibility, Education, Experience, Domain, Keyword, Soft skill). Groups with no items show "None identified." rather than being hidden entirely.

### TC-3.2 — Manually add a requirement (no extraction needed) (API)
**Steps:** Create a JD. Without extracting, `PUT /job-descriptions/{id}` with a `requirements` array containing one item.
**Expected:** `200 OK`. `status` transitions from `"created"` to `"extracted"` (the presence of real, user-supplied requirements promotes the status even though no AI extraction ran). The requirement's `normalized_name` is correctly computed (lowercased/trimmed) from the submitted `name`.

### TC-3.3 — Manually add a requirement in the UI (UI)
**Steps:** On a JD detail page, in any requirement-type group, click "+ Add …". Fill in name, choose an importance level, optionally fill in source text, save.
**Expected:** New requirement appears in the correct group after save. Re-fetching the page shows it persisted.

### TC-3.4 — Edit an existing requirement's fields (API)
**Steps:** Extract or manually add requirements, then `PUT` with a modified `name`/`importance`/`source_text` for one item (full requirements list resubmitted per the full-replace contract).
**Expected:** `200 OK`. The updated fields reflect the changes; `normalized_name` is recomputed from the new `name`.

### TC-3.5 — Edit a requirement in the UI (UI)
**Steps:** On a JD detail page, change a requirement's name or importance dropdown, click **Save changes**.
**Expected:** "Changes saved." confirmation. Reloading the page shows the edit persisted.

### TC-3.6 — Remove a requirement (UI)
**Steps:** Click "Remove" on a requirement, then **Save changes**.
**Expected:** The item disappears from its group immediately, and stays gone after reload.

### TC-3.7 — Normalization is consistent regardless of input casing/whitespace (API)
**Steps:** Submit requirements with names `"  Python  "`, `"PYTHON"`, and `"python"` in three separate JDs (or as three items).
**Expected:** All three produce `normalized_name: "python"`.

### TC-3.8 — Partial scalar update leaves requirements untouched (API)
**Steps:** Extract/add requirements to a JD, then `PUT` with only `{"title": "New title"}` (no `requirements` key).
**Expected:** `title` updates; `requirements` array is completely unchanged.

### TC-3.9 — Toggle "verified" on an individual requirement (UI)
**Steps:** Toggle the "Verified" checkbox on one requirement, save, then confirm via `GET /job-descriptions/{id}` (API) that the item's `verified` field matches.
**Expected:** Backend value matches what was set in the UI.

### TC-3.10 — Update on a missing JD returns 404 (API)
**Steps:** `PUT /job-descriptions/does-not-exist` with any payload.
**Expected:** `404 Not Found`.

---

## 4. Malformed AI output (requires ability to point the backend at a fake/misbehaving endpoint, or code-level testing)

*These cases are primarily covered by the automated test suite (`tests/backend/test_jd_extraction.py`, `test_jd_api.py`) using a fake AI provider, since reliably forcing a real Ollama model to return malformed output on demand isn't practical. Included here for completeness / exploratory testing if a test double is wired in manually.*

### TC-4.1 — Non-JSON AI response is handled gracefully
**Expected:** JD status becomes `"needs_review"`, `extraction_error` mentions the response wasn't valid JSON, no 500 error, no partial/corrupt requirement rows created.

### TC-4.2 — Valid JSON with the wrong shape (e.g. missing `requirements` key) is handled gracefully
**Expected:** Same as TC-4.1 — treated as malformed, not silently accepted as "zero requirements".

### TC-4.3 — Valid JSON with an invalid `requirement_type` value is handled gracefully
**Expected:** Same as TC-4.1.

---

## 5. Verification

### TC-5.1 — Cannot verify a JD that hasn't been extracted or manually populated (API)
**Steps:** Create a JD, `POST /job-descriptions/{id}/verify` without ever extracting or adding requirements.
**Expected:** `409 Conflict` — message explains the JD hasn't been extracted yet.

### TC-5.2 — Verify after successful extraction (API)
**Steps:** Extract (or manually add requirements to) a JD, then `POST /job-descriptions/{id}/verify`.
**Expected:** `200 OK`. `status` becomes `"verified"`, `verified_at` is set.

### TC-5.3 — A needs_review JD can still be verified as-is (API)
**Steps:** Extract a JD such that it ends up `needs_review` (e.g. AI unavailable, or legitimately no requirements found), then verify it without adding requirements.
**Expected:** `200 OK`, transitions to `"verified"` — mirrors the resume domain's rule that needs_review doesn't block verification, since the user may have genuinely reviewed and confirmed there's nothing to extract.

### TC-5.4 — Cannot update a verified JD (API)
**Steps:** Verify a JD (TC-5.2), then `PUT /job-descriptions/{id}` with any payload.
**Expected:** `409 Conflict`.

### TC-5.5 — Cannot re-extract a verified JD (API)
**Steps:** Verify a JD, then `POST /job-descriptions/{id}/extract`.
**Expected:** `409 Conflict`.

### TC-5.6 — Verifying twice is idempotent (API)
**Steps:** `POST /job-descriptions/{id}/verify` twice in a row on an already-extracted JD.
**Expected:** Both calls return `200 OK` with `status: "verified"`.

### TC-5.7 — Verify a missing JD returns 404 (API)
**Steps:** `POST /job-descriptions/does-not-exist/verify`.
**Expected:** `404 Not Found`.

### TC-5.8 — Verify in the UI (UI)
**Steps:** On a JD detail page with at least one requirement, click **"Mark Requirements as Verified"**.
**Expected:** Confirmation message shown. Status badge updates to "Verified". All fields (title/company/description and every requirement editor) become disabled. Save/Extract/Verify buttons disappear, replaced by a message that further changes require a new job description.

### TC-5.9 — Verified JD UI state persists across reload (UI)
**Steps:** After TC-5.8, reload the page.
**Expected:** Still shows Verified, still disabled — confirms state is re-fetched from the backend, not just a client-side flag.

---

## 6. Retrieval and listing

### TC-6.1 — Get a JD by id (API)
**Steps:** `GET /job-descriptions/{id}` for a created JD.
**Expected:** `200 OK`, full JD object with `requirements` array (empty if not yet extracted).

### TC-6.2 — Get a missing JD returns 404 (API)
**Steps:** `GET /job-descriptions/does-not-exist`.
**Expected:** `404 Not Found`.

### TC-6.3 — List all job descriptions (API)
**Steps:** Create 2–3 JDs, `GET /job-descriptions`.
**Expected:** `200 OK`, array of lightweight summaries (id, title, company, status, timestamps) — no nested `requirements` in the list view.

### TC-6.4 — List job descriptions in the UI (UI)
**Steps:** Navigate to `/jobs` after creating a few job descriptions.
**Expected:** Each JD listed with title/company and a status badge; clicking navigates to its detail page. Empty state shown when none exist.

---

## 7. Database persistence

### TC-7.1 — Job description and requirements persist across requests (API)
**Steps:** Create and extract/populate a JD. Make a completely separate `GET` request (simulating a new client/session) for the same id.
**Expected:** All data identical to what was saved — no in-memory-only state.

### TC-7.2 — Backend restart preserves JD data (API)
**Steps:** Create, extract/populate, and verify a JD. Restart the backend process. `GET /job-descriptions/{id}` again.
**Expected:** Data persisted (SQLite file-based storage) — identical to before restart.

### TC-7.3 — Deleting the parent JD (if/when a delete endpoint exists) cascades to requirements
**Steps:** Not currently testable — no delete endpoint exists yet in this sprint. Flagged here as a reminder to verify cascade behavior (`ON DELETE CASCADE` is already configured on `jd_requirements.job_description_id`) once a delete endpoint is added.

---

## 8. Cross-cutting / integration

### TC-8.1 — CORS allows the frontend origin for JD routes (API)
**Steps:** Send an `OPTIONS` preflight to `POST /job-descriptions` with `Origin: http://localhost:5173`.
**Expected:** `200 OK`, `Access-Control-Allow-Origin` header present and matches.

### TC-8.2 — Full happy-path flow end-to-end (UI) — *requires Ollama for the "extracted" branch, otherwise substitute manual entry*
**Steps:** `/jobs/new` → paste a JD → save → on detail page click Extract → review results (or, without Ollama, see the needs_review explanation and manually add a couple of requirements instead) → correct at least one requirement → save → click Mark Requirements as Verified → confirm it shows Verified in the `/jobs` list.
**Expected:** Every step succeeds without error; final state consistent between list page, detail page, and a direct `GET /job-descriptions/{id}` call.

### TC-8.3 — Job descriptions and resumes coexist without interference
**Steps:** With at least one resume and one job description both saved/verified, navigate between `/resumes`, `/resumes/:id`, `/jobs`, `/jobs/:id`.
**Expected:** Each domain's data is independent; no cross-contamination, no shared state bugs, navigation between the two sections works cleanly via the top nav.

### TC-8.4 — Extraction never invents a requirement not present in the text (manual judgment call) — *requires Ollama*
**Steps:** Extract a JD with a deliberately sparse description (e.g. only mentions "Python" and nothing else — no years of experience, no degree, no soft skills).
**Expected:** Extracted requirements should only include what's actually stated (e.g. just a `required_skill` for Python). No requirement should appear for experience level, education, or soft skills that were never mentioned in the source text. Every requirement's `source_text` should be a real, verifiable excerpt — not a paraphrase of something implied.

---

## Test summary template

| TC ID | Result (Pass/Fail) | Notes |
|---|---|---|
| TC-1.1 | | |
| TC-1.2 | | |
| … | | |

Log any failure with: the exact request/steps used, actual vs. expected response, and whether it reproduces consistently. For extraction-quality cases (Section 2, TC-8.4), also record the exact JD text used and the model/version running in Ollama, since output can vary by model.
