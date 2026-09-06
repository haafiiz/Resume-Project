import pytest
from fastapi.testclient import TestClient

import app.services.jd_service as jd_service_module
from app.core.ai.base import AIProvider, AIProviderUnavailableError
from app.main import app

client = TestClient(app)

SAMPLE_DESCRIPTION = (
    "We are looking for a QA Automation Engineer. Must have 3+ years of "
    "Python experience. Required: experience with Selenium and pytest. "
    "Preferred: experience with CI/CD pipelines. Nice to have: Kubernetes "
    "knowledge. Bachelor's degree in Computer Science required. Strong "
    "communication skills."
)

GOOD_AI_RESPONSE = """{"requirements": [
  {"requirement_type": "required_skill", "name": "Python", "importance": "required", "source_text": "3+ years of Python experience"},
  {"requirement_type": "required_skill", "name": "Selenium", "importance": "required", "source_text": "experience with Selenium and pytest"},
  {"requirement_type": "preferred_skill", "name": "CI/CD", "importance": "preferred", "source_text": "Preferred: experience with CI/CD pipelines"},
  {"requirement_type": "technology", "name": "Kubernetes", "importance": "nice_to_have", "source_text": "Nice to have: Kubernetes knowledge"},
  {"requirement_type": "education", "name": "Bachelor's in Computer Science", "importance": "required", "source_text": "Bachelor's degree in Computer Science required"},
  {"requirement_type": "soft_skill", "name": "Communication", "importance": "required", "source_text": "Strong communication skills"}
]}"""


class FakeProvider(AIProvider):
    def __init__(self, response: str | None = None, error: Exception | None = None):
        self.response = response
        self.error = error

    def generate(self, prompt: str, system: str | None = None) -> str:
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


def _use_fake_provider(monkeypatch, provider: AIProvider):
    """JDService resolves its AIProvider lazily via core.ai.factory - patch
    the factory function it calls so extraction uses our fake instead of
    trying to reach a real Ollama instance."""
    monkeypatch.setattr(jd_service_module, "get_ai_provider", lambda: provider)


def _create_sample_jd():
    return client.post(
        "/api/v1/job-descriptions",
        json={
            "title": "QA Automation Engineer",
            "company": "Example Company",
            "description": SAMPLE_DESCRIPTION,
        },
    )


class TestJobDescriptionCreation:
    def test_create_with_title_and_company_returns_201(self):
        response = _create_sample_jd()

        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "QA Automation Engineer"
        assert body["company"] == "Example Company"
        assert body["description"] == SAMPLE_DESCRIPTION
        assert body["status"] == "created"
        assert body["requirements"] == []

    def test_create_without_title_and_company_succeeds(self):
        response = client.post(
            "/api/v1/job-descriptions", json={"description": SAMPLE_DESCRIPTION}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["title"] is None
        assert body["company"] is None

    def test_create_with_empty_description_is_rejected(self):
        response = client.post("/api/v1/job-descriptions", json={"description": ""})

        assert response.status_code == 422

    def test_create_with_missing_description_is_rejected(self):
        response = client.post("/api/v1/job-descriptions", json={"title": "Some role"})

        assert response.status_code == 422

    def test_create_with_whitespace_only_title_is_still_accepted(self):
        # Title/company are optional free text - only description has a
        # non-empty requirement per the spec.
        response = client.post(
            "/api/v1/job-descriptions",
            json={"title": "  ", "description": SAMPLE_DESCRIPTION},
        )

        assert response.status_code == 201


class TestRequirementExtraction:
    def test_extraction_with_valid_ai_response_populates_requirements(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response=GOOD_AI_RESPONSE))
        jd_id = _create_sample_jd().json()["id"]

        response = client.post(f"/api/v1/job-descriptions/{jd_id}/extract")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "extracted"
        assert body["extraction_error"] is None
        assert len(body["requirements"]) == 6

    def test_extraction_sets_normalized_name_on_every_requirement(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response=GOOD_AI_RESPONSE))
        jd_id = _create_sample_jd().json()["id"]

        body = client.post(f"/api/v1/job-descriptions/{jd_id}/extract").json()

        python_req = next(r for r in body["requirements"] if r["name"] == "Python")
        assert python_req["normalized_name"] == "python"

    def test_required_vs_preferred_importance_is_preserved(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response=GOOD_AI_RESPONSE))
        jd_id = _create_sample_jd().json()["id"]

        body = client.post(f"/api/v1/job-descriptions/{jd_id}/extract").json()

        python_req = next(r for r in body["requirements"] if r["name"] == "Python")
        cicd_req = next(r for r in body["requirements"] if r["name"] == "CI/CD")
        k8s_req = next(r for r in body["requirements"] if r["name"] == "Kubernetes")

        assert python_req["importance"] == "required"
        assert cicd_req["importance"] == "preferred"
        assert k8s_req["importance"] == "nice_to_have"

    def test_every_requirement_carries_source_text(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response=GOOD_AI_RESPONSE))
        jd_id = _create_sample_jd().json()["id"]

        body = client.post(f"/api/v1/job-descriptions/{jd_id}/extract").json()

        for req in body["requirements"]:
            assert req["source_text"]

    def test_extraction_on_missing_jd_returns_404(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response=GOOD_AI_RESPONSE))

        response = client.post("/api/v1/job-descriptions/does-not-exist/extract")

        assert response.status_code == 404


class TestMalformedAiOutput:
    def test_non_json_ai_response_marks_needs_review(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response="not valid json"))
        jd_id = _create_sample_jd().json()["id"]

        response = client.post(f"/api/v1/job-descriptions/{jd_id}/extract")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "needs_review"
        assert body["extraction_error"] is not None
        assert body["requirements"] == []

    def test_ai_response_with_wrong_schema_marks_needs_review(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response='{"unexpected": "shape"}'))
        jd_id = _create_sample_jd().json()["id"]

        response = client.post(f"/api/v1/job-descriptions/{jd_id}/extract")

        assert response.status_code == 200
        assert response.json()["status"] == "needs_review"

    def test_extraction_finding_nothing_marks_needs_review(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response='{"requirements": []}'))
        jd_id = _create_sample_jd().json()["id"]

        response = client.post(f"/api/v1/job-descriptions/{jd_id}/extract")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "needs_review"
        assert body["requirements"] == []


class TestAiUnavailable:
    def test_provider_unreachable_marks_needs_review_not_a_500(self, monkeypatch):
        _use_fake_provider(
            monkeypatch,
            FakeProvider(error=AIProviderUnavailableError("connection refused")),
        )
        jd_id = _create_sample_jd().json()["id"]

        response = client.post(f"/api/v1/job-descriptions/{jd_id}/extract")

        # The HTTP request itself must succeed - AI unavailability is a
        # normal, recoverable outcome, not a server error.
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "needs_review"
        assert "unavailable" in body["extraction_error"].lower()

    def test_jd_is_still_saved_and_retrievable_after_ai_unavailable(self, monkeypatch):
        _use_fake_provider(
            monkeypatch, FakeProvider(error=AIProviderUnavailableError("down"))
        )
        jd_id = _create_sample_jd().json()["id"]
        client.post(f"/api/v1/job-descriptions/{jd_id}/extract")

        response = client.get(f"/api/v1/job-descriptions/{jd_id}")

        assert response.status_code == 200
        assert response.json()["description"] == SAMPLE_DESCRIPTION


class TestJobDescriptionRetrieval:
    def test_get_by_id_returns_full_jd(self):
        jd_id = _create_sample_jd().json()["id"]

        response = client.get(f"/api/v1/job-descriptions/{jd_id}")

        assert response.status_code == 200
        assert response.json()["id"] == jd_id

    def test_get_missing_jd_returns_404(self):
        response = client.get("/api/v1/job-descriptions/does-not-exist")

        assert response.status_code == 404

    def test_list_returns_created_job_descriptions(self):
        _create_sample_jd()
        _create_sample_jd()

        response = client.get("/api/v1/job-descriptions")

        assert response.status_code == 200
        assert len(response.json()) == 2


class TestJobDescriptionUpdate:
    def test_update_scalar_fields(self):
        jd_id = _create_sample_jd().json()["id"]

        response = client.put(
            f"/api/v1/job-descriptions/{jd_id}", json={"title": "Senior QA Engineer"}
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Senior QA Engineer"

    def test_update_replaces_requirements_and_normalizes_names(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response=GOOD_AI_RESPONSE))
        jd_id = _create_sample_jd().json()["id"]
        client.post(f"/api/v1/job-descriptions/{jd_id}/extract")

        response = client.put(
            f"/api/v1/job-descriptions/{jd_id}",
            json={
                "requirements": [
                    {
                        "requirement_type": "required_skill",
                        "name": "  TypeScript  ",
                        "importance": "required",
                        "verified": True,
                    }
                ]
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["requirements"]) == 1
        assert body["requirements"][0]["name"] == "  TypeScript  "
        assert body["requirements"][0]["normalized_name"] == "typescript"
        assert body["requirements"][0]["verified"] is True

    def test_manually_adding_requirements_promotes_status_from_created(self):
        jd_id = _create_sample_jd().json()["id"]

        response = client.put(
            f"/api/v1/job-descriptions/{jd_id}",
            json={
                "requirements": [
                    {
                        "requirement_type": "required_skill",
                        "name": "Python",
                        "verified": True,
                    }
                ]
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "extracted"

    def test_update_missing_jd_returns_404(self):
        response = client.put("/api/v1/job-descriptions/does-not-exist", json={"title": "X"})

        assert response.status_code == 404


class TestJobDescriptionVerification:
    def test_cannot_verify_unextracted_jd(self):
        jd_id = _create_sample_jd().json()["id"]

        response = client.post(f"/api/v1/job-descriptions/{jd_id}/verify")

        assert response.status_code == 409

    def test_verify_after_extraction_succeeds(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response=GOOD_AI_RESPONSE))
        jd_id = _create_sample_jd().json()["id"]
        client.post(f"/api/v1/job-descriptions/{jd_id}/extract")

        response = client.post(f"/api/v1/job-descriptions/{jd_id}/verify")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "verified"
        assert body["verified_at"] is not None

    def test_cannot_update_a_verified_jd(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response=GOOD_AI_RESPONSE))
        jd_id = _create_sample_jd().json()["id"]
        client.post(f"/api/v1/job-descriptions/{jd_id}/extract")
        client.post(f"/api/v1/job-descriptions/{jd_id}/verify")

        response = client.put(f"/api/v1/job-descriptions/{jd_id}", json={"title": "New title"})

        assert response.status_code == 409

    def test_cannot_reextract_a_verified_jd(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response=GOOD_AI_RESPONSE))
        jd_id = _create_sample_jd().json()["id"]
        client.post(f"/api/v1/job-descriptions/{jd_id}/extract")
        client.post(f"/api/v1/job-descriptions/{jd_id}/verify")

        response = client.post(f"/api/v1/job-descriptions/{jd_id}/extract")

        assert response.status_code == 409

    def test_verify_missing_jd_returns_404(self):
        response = client.post("/api/v1/job-descriptions/does-not-exist/verify")

        assert response.status_code == 404

    def test_verifying_twice_is_idempotent(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response=GOOD_AI_RESPONSE))
        jd_id = _create_sample_jd().json()["id"]
        client.post(f"/api/v1/job-descriptions/{jd_id}/extract")

        first = client.post(f"/api/v1/job-descriptions/{jd_id}/verify")
        second = client.post(f"/api/v1/job-descriptions/{jd_id}/verify")

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["status"] == "verified"

    def test_needs_review_jd_can_still_be_verified(self, monkeypatch):
        # A JD whose extraction failed can be verified once the user has
        # manually reviewed/added requirements is out of scope here -
        # but verifying a needs_review JD as-is (e.g. legitimately empty)
        # must still be allowed, matching the resume domain's rule.
        _use_fake_provider(monkeypatch, FakeProvider(response='{"requirements": []}'))
        jd_id = _create_sample_jd().json()["id"]
        client.post(f"/api/v1/job-descriptions/{jd_id}/extract")

        response = client.post(f"/api/v1/job-descriptions/{jd_id}/verify")

        assert response.status_code == 200
        assert response.json()["status"] == "verified"


class TestPersistence:
    def test_job_description_persists_across_requests(self, monkeypatch):
        _use_fake_provider(monkeypatch, FakeProvider(response=GOOD_AI_RESPONSE))
        jd_id = _create_sample_jd().json()["id"]
        client.post(f"/api/v1/job-descriptions/{jd_id}/extract")

        # Simulate a fresh request cycle - a new client call should see
        # exactly what was persisted, not any in-memory state.
        response = client.get(f"/api/v1/job-descriptions/{jd_id}")

        body = response.json()
        assert body["status"] == "extracted"
        assert len(body["requirements"]) == 6
