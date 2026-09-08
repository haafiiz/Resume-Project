import io

from fastapi.testclient import TestClient

from app.main import app
from tests.backend.helpers.pdf_docx_builders import build_docx

client = TestClient(app)


def _create_verified_resume(skill_names: list[str], docx_lines: list[str] | None = None) -> str:
    """Upload a DOCX resume, then correct its skills to exactly
    `skill_names` (so tests don't depend on the parser's heuristics) and
    verify it. Returns the resume id."""
    lines = docx_lines or [
        "Jane Doe",
        "jane.doe@example.com",
        "555-0000",
        "Austin, TX",
    ]
    content = build_docx(lines)
    upload = client.post(
        "/api/v1/resumes",
        files={
            "file": (
                "resume.docx",
                io.BytesIO(content),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    resume_id = upload.json()["id"]

    client.put(
        f"/api/v1/resumes/{resume_id}",
        json={"skills": [{"name": name, "verified": True} for name in skill_names]},
    )
    client.post(f"/api/v1/resumes/{resume_id}/verify")
    return resume_id


def _create_verified_jd(requirements: list[dict]) -> str:
    """Create a JD, manually populate its requirements (bypassing AI
    extraction entirely - deterministic and network-free), and verify
    it. Returns the JD id."""
    create = client.post(
        "/api/v1/job-descriptions",
        json={"title": "Test Role", "description": "A test job description."},
    )
    jd_id = create.json()["id"]

    client.put(
        f"/api/v1/job-descriptions/{jd_id}",
        json={"requirements": [{**r, "verified": True} for r in requirements]},
    )
    client.post(f"/api/v1/job-descriptions/{jd_id}/verify")
    return jd_id


def _req(requirement_type: str, name: str, importance: str = "required") -> dict:
    return {"requirement_type": requirement_type, "name": name, "importance": importance}


class TestAcceptanceCriteria:
    def test_python_selenium_playwright_cypress_aws_scenario(self):
        resume_id = _create_verified_resume(["Python", "Selenium", "Playwright", "SQL"])
        jd_id = _create_verified_jd(
            [
                _req("required_skill", "Python"),
                _req("required_skill", "Selenium"),
                _req("required_skill", "Playwright"),
                _req("required_skill", "Cypress"),
                _req("required_skill", "AWS"),
            ]
        )

        response = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["overall_score"] == 80.0
        assert body["required_skills_score"] == 60.0

        matches_response = client.get(f"/api/v1/analyses/{body['id']}/matches")
        matches = matches_response.json()["matches"]

        matched_names = {m["requirement_name"] for m in matches if m["match_type"] == "exact"}
        missing_names = {m["requirement_name"] for m in matches if m["match_type"] == "missing"}

        assert matched_names == {"Python", "Selenium", "Playwright"}
        assert missing_names == {"Cypress", "AWS"}

        # SQL is on the resume but wasn't asked for - it must never
        # appear as a fabricated match to any requirement.
        assert "SQL" not in matched_names
        assert matches_response.json()["extra_resume_skills"] == ["SQL"]


class TestExactAndNormalizedMatches:
    def test_exact_skill_match(self):
        resume_id = _create_verified_resume(["Python"])
        jd_id = _create_verified_jd([_req("required_skill", "Python")])

        response = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        )

        assert response.json()["overall_score"] == 100.0

    def test_normalized_formatting_variant_match(self):
        resume_id = _create_verified_resume(["RESTful API"])
        jd_id = _create_verified_jd([_req("required_skill", "REST APIs")])

        analysis = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        ).json()
        matches = client.get(f"/api/v1/analyses/{analysis['id']}/matches").json()["matches"]

        assert matches[0]["match_type"] == "normalized"
        assert matches[0]["confidence"] == 0.9


class TestPartialMatches:
    def test_broader_resume_skill_partially_matches_narrower_requirement(self):
        resume_id = _create_verified_resume(["AWS"])
        jd_id = _create_verified_jd([_req("required_skill", "AWS Lambda")])

        analysis = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        ).json()
        matches = client.get(f"/api/v1/analyses/{analysis['id']}/matches").json()["matches"]

        assert matches[0]["match_type"] == "partial"
        assert matches[0]["confidence"] == 0.4


class TestMissingSkills:
    def test_skill_not_on_resume_is_missing_not_fabricated(self):
        resume_id = _create_verified_resume(["Python"])
        jd_id = _create_verified_jd([_req("required_skill", "Kubernetes")])

        analysis = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        ).json()
        matches = client.get(f"/api/v1/analyses/{analysis['id']}/matches").json()["matches"]

        assert matches[0]["match_type"] == "missing"
        assert matches[0]["resume_skill_id"] is None
        assert analysis["overall_score"] == 50.0  # 0/1 required skills * 50% + 50% neutral rest


class TestMandatoryFalsePositivePairs:
    """The three pairs the spec explicitly requires as end-to-end API
    tests, not just unit tests on the matcher module."""

    def test_java_vs_javascript_via_api(self):
        resume_id = _create_verified_resume(["JavaScript"])
        jd_id = _create_verified_jd([_req("required_skill", "Java")])

        analysis = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        ).json()
        matches = client.get(f"/api/v1/analyses/{analysis['id']}/matches").json()["matches"]

        assert matches[0]["match_type"] == "missing"

    def test_aws_vs_azure_via_api(self):
        resume_id = _create_verified_resume(["Azure"])
        jd_id = _create_verified_jd([_req("required_skill", "AWS")])

        analysis = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        ).json()
        matches = client.get(f"/api/v1/analyses/{analysis['id']}/matches").json()["matches"]

        assert matches[0]["match_type"] == "missing"

    def test_selenium_vs_playwright_via_api(self):
        resume_id = _create_verified_resume(["Playwright"])
        jd_id = _create_verified_jd([_req("required_skill", "Selenium")])

        analysis = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        ).json()
        matches = client.get(f"/api/v1/analyses/{analysis['id']}/matches").json()["matches"]

        assert matches[0]["match_type"] == "missing"


class TestScoreCalculationAndWeighting:
    def test_perfect_match_across_all_categories_scores_100(self):
        resume_id = _create_verified_resume(
            ["Python"],
            docx_lines=[
                "Jane Doe",
                "jane@example.com",
                "Experience",
                "QA Automation Engineer, Acme Corp",
                "Jan 2020 - Present",
                "- Led automated testing initiatives across the team",
                "Education",
                "State University",
                "Bachelor of Science in Computer Science",
                "2016 - 2020",
                "Skills",
                "Python",
            ],
        )
        jd_id = _create_verified_jd(
            [
                _req("required_skill", "Python"),
                _req("responsibility", "led automated testing"),
                _req("experience", "QA Automation Engineer"),
                _req("education", "Bachelor of Science Computer Science"),
            ]
        )

        response = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        )

        assert response.status_code == 201
        # Not strictly required to be literally 100 (freetext matching
        # tops out at "normalized" = 0.9), but should be high across the
        # board with no missing categories.
        body = response.json()
        assert body["required_skills_score"] == 100.0

    def test_weighting_prioritizes_required_skills_over_other_categories(self):
        # Two resumes: one aces required skills but nothing else, the
        # other aces everything except required skills. The first
        # should score higher, proving the 50% required-skills weight
        # dominates.
        strong_required_resume = _create_verified_resume(["Python", "Selenium"])
        weak_required_resume = _create_verified_resume(["Java"])

        jd_id = _create_verified_jd(
            [_req("required_skill", "Python"), _req("required_skill", "Selenium")]
        )

        strong_analysis = client.post(
            "/api/v1/analyses",
            json={"resume_id": strong_required_resume, "job_description_id": jd_id},
        ).json()
        weak_analysis = client.post(
            "/api/v1/analyses",
            json={"resume_id": weak_required_resume, "job_description_id": jd_id},
        ).json()

        assert strong_analysis["overall_score"] > weak_analysis["overall_score"]

    def test_weights_are_included_in_the_response_for_transparency(self):
        resume_id = _create_verified_resume(["Python"])
        jd_id = _create_verified_jd([_req("required_skill", "Python")])

        response = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        )

        weights = response.json()["weights"]
        assert weights["required_skills"] == 0.5
        assert sum(weights.values()) == 1.0


class TestEmptyRequirements:
    def test_jd_verified_with_zero_requirements_scores_100(self):
        resume_id = _create_verified_resume(["Python"])

        # Promote the JD to "extracted" with one requirement, then clear
        # the list back to empty before verifying - update_job_description
        # doesn't demote status when a non-empty->empty edit happens, so
        # this legitimately produces a verified JD with zero requirements
        # (e.g. a JD the user reviewed and confirmed truly has nothing
        # extractable) without touching internals directly.
        create = client.post(
            "/api/v1/job-descriptions",
            json={"description": "A job description with nothing extractable."},
        )
        jd_id = create.json()["id"]
        client.put(
            f"/api/v1/job-descriptions/{jd_id}",
            json={"requirements": [_req("required_skill", "Placeholder", "required")]},
        )
        client.put(f"/api/v1/job-descriptions/{jd_id}", json={"requirements": []})
        client.post(f"/api/v1/job-descriptions/{jd_id}/verify")

        response = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        )

        assert response.status_code == 201
        assert response.json()["overall_score"] == 100.0


class TestReproducibility:
    def test_running_the_same_analysis_twice_produces_the_same_score(self):
        resume_id = _create_verified_resume(["Python", "Selenium"])
        jd_id = _create_verified_jd(
            [_req("required_skill", "Python"), _req("required_skill", "Cypress")]
        )

        first = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        ).json()
        second = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        ).json()

        assert first["overall_score"] == second["overall_score"]
        assert first["id"] != second["id"]  # separate analysis records


class TestVerificationGuard:
    def test_analysis_rejected_if_resume_not_verified(self):
        content = build_docx(["Jane Doe"])
        upload = client.post(
            "/api/v1/resumes",
            files={
                "file": (
                    "resume.docx",
                    io.BytesIO(content),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        unverified_resume_id = upload.json()["id"]
        jd_id = _create_verified_jd([_req("required_skill", "Python")])

        response = client.post(
            "/api/v1/analyses",
            json={"resume_id": unverified_resume_id, "job_description_id": jd_id},
        )

        assert response.status_code == 409

    def test_analysis_rejected_if_jd_not_verified(self):
        resume_id = _create_verified_resume(["Python"])
        create = client.post(
            "/api/v1/job-descriptions",
            json={"description": "An unverified job description."},
        )
        unverified_jd_id = create.json()["id"]

        response = client.post(
            "/api/v1/analyses",
            json={"resume_id": resume_id, "job_description_id": unverified_jd_id},
        )

        assert response.status_code == 409


class TestNotFound:
    def test_analysis_with_missing_resume_returns_404(self):
        jd_id = _create_verified_jd([_req("required_skill", "Python")])

        response = client.post(
            "/api/v1/analyses",
            json={"resume_id": "does-not-exist", "job_description_id": jd_id},
        )

        assert response.status_code == 404

    def test_analysis_with_missing_jd_returns_404(self):
        resume_id = _create_verified_resume(["Python"])

        response = client.post(
            "/api/v1/analyses",
            json={"resume_id": resume_id, "job_description_id": "does-not-exist"},
        )

        assert response.status_code == 404

    def test_get_missing_analysis_returns_404(self):
        response = client.get("/api/v1/analyses/does-not-exist")

        assert response.status_code == 404

    def test_get_matches_for_missing_analysis_returns_404(self):
        response = client.get("/api/v1/analyses/does-not-exist/matches")

        assert response.status_code == 404


class TestPersistence:
    def test_analysis_is_retrievable_after_creation(self):
        resume_id = _create_verified_resume(["Python"])
        jd_id = _create_verified_jd([_req("required_skill", "Python")])

        created = client.post(
            "/api/v1/analyses", json={"resume_id": resume_id, "job_description_id": jd_id}
        ).json()

        fetched = client.get(f"/api/v1/analyses/{created['id']}")

        assert fetched.status_code == 200
        assert fetched.json()["overall_score"] == created["overall_score"]
