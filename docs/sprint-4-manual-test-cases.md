# Sprint 4 — Manual Test Cases

**Scope:** Deterministic resume↔JD matching, scoring, and the analysis review UI. Covers `POST/GET /analyses` and `GET /analyses/{id}/matches`, and the `/analysis`, `/analysis/:id` frontend pages.

**Prerequisites:**
- Backend running with a clean/migrated database (`alembic upgrade head`)
- Frontend running, pointed at the backend
- At least one **verified** resume and one **verified** job description ready (see Sprint 2/3 manual test docs for how to get there) — matching requires both inputs to already be verified
- No Ollama instance is required for this sprint's tests — requirements can be entered manually via `PUT /job-descriptions/{id}` (see Sprint 3 doc) if extraction isn't available

Each test case lists **Preconditions**, **Steps**, and **Expected Result**. Cases marked "(API)" can be run with curl/Postman/the `/docs` Swagger UI; "(UI)" cases are run in the browser.

---

## 1. The acceptance criteria scenario (do this one first)

### TC-1.1 — Exact reproduction of the spec's example (API)
**Preconditions:** A verified resume with skills exactly `Python, Selenium, Playwright, SQL`. A verified JD with required skills exactly `Python, Selenium, Playwright, Cypress, AWS`.
**Steps:** `POST /api/v1/analyses` with both ids. Then `GET /api/v1/analyses/{id}/matches`.
**Expected:**
- `overall_score` is exactly `80.0`.
- `required_skills_score` is exactly `60.0`.
- In the matches list: Python, Selenium, and Playwright all have `match_type: "exact"`.
- Cypress and AWS both have `match_type: "missing"` and `resume_skill_id: null`.
- `extra_resume_skills` contains exactly `["SQL"]` — SQL never appears as a `matched` requirement, since the JD never asked for it.
- Running the same `POST /analyses` request again (a second, separate analysis) produces an identical `overall_score` of `80.0`.

### TC-1.2 — Same scenario, end to end in the UI (UI)
**Steps:** Navigate to `/analysis`, select the resume and JD from TC-1.1, click **Run analysis**.
**Expected:** Navigates to `/analysis/:id`. Overall score shows **80/100**. Category breakdown shows Required Skills at 60%. "Matched requirements" lists Python, Selenium, Playwright. "Missing requirements" lists Cypress, AWS. "Additional resume skills" shows SQL.

---

## 2. Match type classification

### TC-2.1 — Exact match (API)
**Steps:** Resume skill `"Python"`, JD requirement `"Python"` (identical strings). Run analysis.
**Expected:** `match_type: "exact"`, `confidence: 1.0`.

### TC-2.2 — Case-insensitive exact match (API)
**Steps:** Resume skill `"python"`, JD requirement `"Python"`. Run analysis.
**Expected:** Still `match_type: "exact"` — casing alone doesn't demote the match.

### TC-2.3 — Normalized match: formatting variants (API)
**Steps:** Resume skill `"RESTful API"`, JD requirement `"REST APIs"`. Run analysis.
**Expected:** `match_type: "normalized"`, `confidence: 0.9`. Explanation mentions both normalize to the same value.

### TC-2.4 — Normalized match: known abbreviation (API)
**Steps:** Resume skill `"JS"`, JD requirement `"JavaScript"`. Run analysis.
**Expected:** `match_type: "normalized"`.

### TC-2.5 — Related match: SQL dialect (API)
**Steps:** Resume skill `"PostgreSQL"`, JD requirement `"SQL"`. Run analysis.
**Expected:** `match_type: "related"`, `confidence: 0.6` — lower than a normalized match, since PostgreSQL is SQL-adjacent but not literally what was asked for.

### TC-2.6 — Partial match: broader/narrower term (API)
**Steps:** Resume skill `"AWS"`, JD requirement `"AWS Lambda"`. Run analysis.
**Expected:** `match_type: "partial"`, `confidence: 0.4`.

### TC-2.7 — Partial match is symmetric (API)
**Steps:** Repeat TC-2.6 with the resume/JD skill names swapped (resume has `"AWS Lambda"`, JD requires `"AWS"`).
**Expected:** Still `match_type: "partial"`.

### TC-2.8 — Missing: skill genuinely absent (API)
**Steps:** Resume has no skill resembling `"Kubernetes"`. JD requires `"Kubernetes"`. Run analysis.
**Expected:** `match_type: "missing"`, `confidence: 0.0`, `resume_skill_id: null`, explanation names the missing skill.

---

## 3. Mandatory false-positive guards

These four pairs must **never** be treated as matches. Each should be tested in both directions.

### TC-3.1 — Java vs JavaScript (API)
**Steps:** Resume skill `"JavaScript"`, JD requirement `"Java"`. Run analysis. Then reverse: resume `"Java"`, JD requires `"JavaScript"`.
**Expected:** Both directions produce `match_type: "missing"`.

### TC-3.2 — AWS vs Azure (API)
**Steps:** Resume skill `"Azure"`, JD requirement `"AWS"`, and reversed.
**Expected:** Both directions `missing`.

### TC-3.3 — Selenium vs Playwright (API)
**Steps:** Resume skill `"Playwright"`, JD requirement `"Selenium"`, and reversed.
**Expected:** Both directions `missing`.

### TC-3.4 — React vs Angular (API)
**Steps:** Resume skill `"Angular"`, JD requirement `"React"`, and reversed.
**Expected:** Both directions `missing`.

### TC-3.5 — Verify these pairs visually in the UI (UI)
**Steps:** Run an analysis with a resume/JD pair covering all four dangerous pairs (e.g. resume has JavaScript/Azure/Playwright/Angular; JD requires Java/AWS/Selenium/React). View `/analysis/:id`.
**Expected:** All four requirements appear under "Missing requirements", none under "Matched" or "Partial".

---

## 4. Scoring and weighting

### TC-4.1 — Perfect match scores 100 (API)
**Steps:** Resume and JD with identical, fully-covered requirements across every category (skills, responsibilities, experience, education, keywords). Run analysis.
**Expected:** `overall_score` at or near `100.0` (freetext categories top out at 0.9 confidence for full coverage, so a JD with only skill requirements will hit exactly 100; one with freetext categories may land slightly under, which is expected and documented).

### TC-4.2 — Empty JD requirements category scores neutral, not zero (API)
**Steps:** A JD with only `required_skill` requirements (no responsibilities/experience/education/preferred_skills/keywords at all). Run analysis.
**Expected:** `responsibilities_score`, `experience_score`, `education_score`, `preferred_skills_score`, and `keywords_score` are all `100.0` (not `0.0`) in the response — confirms the "empty category = neutral" rule.

### TC-4.3 — All-missing required skills still yields a non-zero score (API)
**Steps:** JD requires 2 skills, resume has neither. Run analysis.
**Expected:** `required_skills_score` is `0.0`, but `overall_score` is `50.0` (since required skills is 50% weight and every other category is empty/neutral at 100%: `0.5*0 + 0.5*100 = 50`).

### TC-4.4 — Weights sum to 1.0 and are visible in the response (API)
**Steps:** Run any analysis. Inspect the `weights` field.
**Expected:** `weights.required_skills` is `0.5`, and all six values sum to exactly `1.0`.

### TC-4.5 — Custom weights via environment variables (API) — *requires restarting the backend with different env vars*
**Steps:** Set `MATCH_WEIGHT_REQUIRED_SKILLS=0.9` and reduce the other five weights so they still sum to 1.0 in `backend/.env`, restart the backend, run a new analysis on the same resume/JD as TC-1.1.
**Expected:** The `weights` field in the response reflects the new values, and `overall_score` changes accordingly (required skills now dominates even more heavily). Restore the default `.env` afterward.

### TC-4.6 — View the category breakdown in the UI (UI)
**Steps:** Open any `/analysis/:id` page.
**Expected:** Six colored bars, one per category, each showing percentage, weight, and requirement count. Colors reflect score tier (green ≥80%, amber 50-79%, red <50%).

---

## 5. Reproducibility

### TC-5.1 — Repeated analysis of the same pair yields identical scores (API)
**Steps:** `POST /analyses` twice with the same `resume_id`/`job_description_id`.
**Expected:** Both responses have identical `overall_score` and identical per-category scores, but different `id` values (two separate analysis records).

### TC-5.2 — Result doesn't depend on skill list order (API)
**Steps:** Not directly controllable via the API (skills are stored and returned in whatever order the database gives), but can be inferred: run the same analysis on two different resumes that have the identical set of skills entered in a different order.
**Expected:** Identical scores and match classifications regardless of entry order.

---

## 6. The critical rule: never fabricate a match

### TC-6.1 — A JD requirement not on the resume is always "missing" (API)
**Steps:** JD requires a skill that genuinely doesn't appear anywhere on the resume (no exact/normalized/related/partial candidate exists). Run analysis.
**Expected:** `match_type: "missing"`. Nothing in the response implies the candidate has this skill.

### TC-6.2 — Extra resume skills are never counted as matches (API)
**Steps:** Resume has more skills than the JD asks for (as in TC-1.1's SQL). Run analysis.
**Expected:** The extra skill never appears in `matches` with a positive match type — it only appears in `extra_resume_skills`, clearly separated.

### TC-6.3 — Analysis requires both inputs to be verified (API)
**Steps:** Attempt `POST /analyses` with a resume that is `parsed` but not yet `verified`.
**Expected:** `409 Conflict`, message explains the resume must be verified first. Repeat with an unverified job description.
**Expected:** `409 Conflict` for the JD case too.

### TC-6.4 — Verification guard in the UI (UI)
**Steps:** With only unverified resumes/JDs available, navigate to `/analysis`.
**Expected:** The picker shows a message that no verified resumes/job descriptions exist yet, and does not offer them as options (drafts never appear in the dropdowns).

---

## 7. Retrieval, persistence, and error handling

### TC-7.1 — Get an analysis by id (API)
**Steps:** `GET /api/v1/analyses/{id}` for a previously created analysis.
**Expected:** `200 OK`, same shape and values as the original creation response.

### TC-7.2 — Get matches for an analysis (API)
**Steps:** `GET /api/v1/analyses/{id}/matches`.
**Expected:** `200 OK`, one entry per JD requirement in the analyzed JD, each with `match_type`, `confidence`, `explanation`, and either `resume_skill_id` or `matched_resume_label`/`matched_resume_text` populated (never both, and both null only for `missing`/`unknown`).

### TC-7.3 — 404 for a missing analysis (API)
**Steps:** `GET /api/v1/analyses/does-not-exist` and `GET /api/v1/analyses/does-not-exist/matches`.
**Expected:** Both return `404 Not Found`.

### TC-7.4 — 404 for a missing resume or JD id at creation time (API)
**Steps:** `POST /analyses` with a `resume_id` that doesn't exist (but a valid `job_description_id`), and separately with a valid `resume_id` but a nonexistent `job_description_id`.
**Expected:** Both return `404 Not Found`.

### TC-7.5 — Analysis persists across a backend restart (API)
**Steps:** Create an analysis, restart the backend, `GET` it again.
**Expected:** Identical data — confirms it's genuinely persisted, not held in memory.

---

## 8. Freetext categories (responsibilities, experience, education, domain, keywords, soft skills)

*These categories are informational best-effort matches (token-overlap based) rather than a strict skill-name comparison — see [docs/matching-engine.md](../docs/matching-engine.md#freetext-categories) for the exact rule. These tests confirm the behavior is sane and explainable, not that it perfectly understands prose.*

### TC-8.1 — Responsibility requirement matched by experience description (API)
**Steps:** Resume experience description includes "Led automated testing initiatives". JD has a `responsibility` requirement named "led automated testing". Run analysis.
**Expected:** `match_type: "normalized"` (full token coverage), explanation names which experience entry covered it.

### TC-8.2 — Responsibility requirement with no coverage (API)
**Steps:** JD has a `responsibility` requirement describing something the resume never mentions (e.g. "conducted machine learning research"). Run analysis.
**Expected:** `match_type: "missing"`.

### TC-8.3 — Education requirement matched by degree text (API)
**Steps:** Resume has an education entry with degree "Bachelor of Science" and field of study "Computer Science". JD has an `education` requirement "Bachelor of Science Computer Science". Run analysis.
**Expected:** `match_type: "normalized"` or `"partial"` depending on exact token overlap — never `missing` when the words genuinely appear.

### TC-8.4 — View freetext matches in the UI (UI)
**Steps:** Run an analysis with a JD that includes at least one responsibility, experience, and education requirement. View `/analysis/:id`.
**Expected:** These requirements appear correctly grouped under Matched/Partial/Missing alongside skill-based ones, each with a readable explanation (not raw technical jargon).

---

## Test summary template

| TC ID | Result (Pass/Fail) | Notes |
|---|---|---|
| TC-1.1 | | |
| TC-1.2 | | |
| … | | |

Log any failure with: the exact resume/JD skill and requirement names used, the actual vs. expected match_type/score, and whether it reproduces consistently. For anything involving the mandatory false-positive pairs (Section 3), treat a failure as high priority — this is the platform's core truth-constraint guarantee being tested directly.
