# AI Architecture

This document covers the `AIProvider` abstraction and how it's used for
job description requirement extraction — the first (and, as of Sprint 3,
only) feature in the platform that calls an LLM.

## Why an abstraction at all

The project's architecture explicitly forbids letting the rest of the
application depend on Ollama (or any specific vendor) directly:

```
AIProvider
├── OllamaProvider       (implemented, Sprint 3)
├── OpenAIProvider       (future)
└── GeminiProvider       (future)
```

The reasoning is practical, not just architectural purism: Ollama is a
local process that may not be running, may not have the configured model
pulled, or may simply be slow. Every place in the codebase that calls an
AI provider has to handle "it didn't answer" as a normal, expected
outcome - and that handling should look the same regardless of which
provider is behind it. A single interface makes that possible.

## The interface

`app/core/ai/base.py` defines the whole contract:

```python
class AIProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str:
        ...
```

That's it — one method, text in, text out. Deliberately generic: it
knows nothing about job descriptions, resumes, or matching. Domain logic
(prompt construction, response validation) lives in the caller, not the
provider. This means the same `AIProvider` interface will be reusable
for matching/tailoring in a later sprint without modification.

Two exception types complete the contract:

- `AIProviderUnavailableError` — the provider couldn't be reached at all
  (connection refused, timeout, non-200 response, malformed response
  envelope). This is the "infrastructure" failure mode.
- `AIProviderResponseError` — the provider was reached and answered, but
  the answer isn't usable (not valid JSON, or valid JSON that doesn't
  match the expected schema). This is the "the model didn't cooperate"
  failure mode.

Callers are expected to catch both and degrade gracefully — see
"Failure handling" below.

## OllamaProvider

`app/core/ai/ollama_provider.py` is the only module in the codebase that
knows Ollama's request/response shape. It POSTs to
`{OLLAMA_BASE_URL}/api/generate` with `format: "json"` (Ollama's
instruction to constrain output to valid JSON, where the loaded model
supports it — an extra guardrail, not a replacement for validating the
response ourselves) and `stream: false`. Connection failures, timeouts,
and non-200 responses are all normalized into
`AIProviderUnavailableError`.

Configuration (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`) comes from
`app/config.py`, sourced from environment variables — see
[docs/development.md](./development.md) for the full variable list.

## Getting a provider: the factory

`app/core/ai/factory.py` has one function:

```python
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)
```

`JDService` calls this lazily (only when extraction is actually
requested — creating, listing, or reading a JD never touches it) and
accepts an optional `ai_provider` constructor argument so tests can
inject a fake provider instead of monkeypatching HTTP calls. This is
also the seam a future `OpenAIProvider`/`GeminiProvider` would plug into
— swap what this function returns, and every caller keeps working
unchanged.

## JD requirement extraction

`app/core/ai/jd_extraction.py` is the only module that knows the JD
extraction prompt and response shape. `extract_requirements(provider,
description)` takes any `AIProvider` and returns a validated
`JDExtractionResult` (`app/core/ai/schemas.py`) or raises one of the two
exception types above.

### The structured output contract

```python
class RequirementType(str, Enum):
    REQUIRED_SKILL = "required_skill"
    PREFERRED_SKILL = "preferred_skill"
    TECHNOLOGY = "technology"
    RESPONSIBILITY = "responsibility"
    EDUCATION = "education"
    EXPERIENCE = "experience"
    DOMAIN = "domain"
    KEYWORD = "keyword"
    SOFT_SKILL = "soft_skill"

class Importance(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    NICE_TO_HAVE = "nice_to_have"

class ExtractedRequirement(BaseModel):
    requirement_type: RequirementType
    name: str
    importance: Importance = Importance.REQUIRED
    description: str | None = None
    source_text: str | None = None

class JDExtractionResult(BaseModel):
    requirements: list[ExtractedRequirement]   # required key, no default
```

`requirements` has **no default value**. This is deliberate: a response
that omits the key entirely is a different failure than a response that
explicitly says `{"requirements": []}`. The former is malformed output
(the model didn't follow the contract); the latter is a legitimate
"found nothing" result. Giving `requirements` a default of `[]` would
silently collapse that distinction and let malformed responses through
as if they were valid — this was caught during manual testing and fixed
by making the field required.

### The prompt

The system prompt (`SYSTEM_PROMPT` in `jd_extraction.py`) instructs the
model to:

- Only extract requirements literally stated in the text — never invent,
  infer, or assume one that isn't explicitly present, and omit anything
  it isn't confident about rather than guessing.
- Attach a `source_text` excerpt to every requirement, so each extracted
  item is traceable back to real text in the job description rather than
  being an unattributed claim.
- Classify into exactly one of the nine `requirement_type` values and
  set `importance` based on the language used ("must have" → required,
  "nice to have" / "a plus" → nice_to_have, "preferred" → preferred).
- Respond with only a single JSON object matching the schema — no
  markdown fences, no commentary.

This mirrors the platform's core truth-constrained principle even though
JD extraction doesn't touch candidate claims directly: an
over-eager extraction (e.g. inferring "5+ years of experience" as a
requirement when the JD only vaguely says "experienced professional")
would poison downstream matching in a later sprint, so the same
discipline applies here.

### Response validation

The raw response goes through, in order:

1. **Markdown fence stripping** — some models wrap JSON in ` ```json
   ... ``` ` fences despite being told not to; stripped defensively
   before parsing.
2. **JSON parsing** — a `json.JSONDecodeError` becomes
   `AIProviderResponseError`.
3. **Pydantic validation** against `JDExtractionResult` — any shape
   mismatch (missing `requirements` key, invalid `requirement_type`
   value, missing `name`, etc.) becomes `AIProviderResponseError` via
   Pydantic's `ValidationError`.

Nothing is coerced or partially accepted — the response either matches
the schema exactly or it's treated as malformed and handled by
`JDService` accordingly.

### Normalization stays outside the AI's hands

`app/utils/text_normalization.py`'s `normalize_name()` (lowercase, trim,
collapse whitespace) is applied to every requirement's `name` by
`JDService` **after** validation, not requested from the model. This is
a mechanical transformation, not a judgment call, so it belongs in
plain, deterministic, testable code — consistent with never letting the
AI perform a step that should be auditable and repeatable.

## Failure handling

`JDService.extract_requirements_for()` never lets an AI failure become a
failed HTTP request. Both exception types are caught and mapped to the
job description's `needs_review` status with a human-readable
`extraction_error`:

| Situation | Result |
|---|---|
| Ollama not running / unreachable | `AIProviderUnavailableError` → `needs_review`, error explains the service is unavailable and suggests retrying or adding requirements manually |
| Model returns non-JSON or wrong-shaped JSON | `AIProviderResponseError` → `needs_review`, error explains the response was unusable |
| Model returns valid, well-formed JSON with zero requirements | Not an error — `needs_review` with an explanation that nothing was found, since an empty result still needs the user's attention |
| Model returns at least one valid requirement | `extracted` |

In every case, **the job description itself is never lost or blocked**
— it stays saved and fully editable; only the extraction attempt failed.
The user can retry extraction, or add requirements by hand through
`PUT /job-descriptions/{id}` (which promotes the status to `extracted`
once real requirements are present, mirroring the same rule in the
resume domain).

This sandbox environment has no Ollama process running, which made
"AI unavailable" a naturally occurring case during manual testing rather
than only a mocked one — confirmed the whole path degrades cleanly with
a `200` response and a clear explanation, never a `500`.

## Testing without a real Ollama instance

`tests/backend/test_jd_extraction.py` exercises `extract_requirements()`
directly against a `FakeProvider` test double (implements `AIProvider`,
returns a canned string or raises an error) — no network access, no
running Ollama required. `tests/backend/test_jd_api.py` does the same at
the API level by monkeypatching `app.services.jd_service.get_ai_provider`
to return a fake provider, so the full `POST .../extract` flow (auth →
service → repository → response) is tested end-to-end without ever
calling a real model.
