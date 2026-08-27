import io

from fastapi.testclient import TestClient

from app.main import app
from tests.backend.helpers.pdf_docx_builders import build_docx, build_pdf

client = TestClient(app)

SAMPLE_DOCX_LINES = [
    "Jane Doe",
    "jane.doe@example.com",
    "(512) 555-1234",
    "Austin, TX",
    "Summary",
    "Experienced software engineer with a passion for backend systems.",
    "Experience",
    "Senior Software Engineer, Acme Corp",
    "Austin, TX | Jan 2020 - Present",
    "- Built scalable APIs using Python and FastAPI",
    "Education",
    "University of Texas at Austin",
    "Bachelor of Science in Computer Science",
    "Aug 2013 - May 2017",
    "Skills",
    "Python, FastAPI, Django, SQL",
]


def _upload_sample_docx():
    content = build_docx(SAMPLE_DOCX_LINES)
    response = client.post(
        "/api/v1/resumes",
        files={
            "file": (
                "resume.docx",
                io.BytesIO(content),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    return response


class TestResumeUpload:
    def test_upload_valid_docx_returns_201_and_parsed_status(self):
        response = _upload_sample_docx()

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "parsed"
        assert body["parse_error"] is None
        assert "id" in body

    def test_upload_valid_pdf_returns_201(self):
        content = build_pdf(["John Smith", "Skills", "Java, Kotlin"])
        response = client.post(
            "/api/v1/resumes",
            files={"file": ("resume.pdf", io.BytesIO(content), "application/pdf")},
        )

        assert response.status_code == 201
        assert response.json()["status"] in {"parsed", "needs_review"}

    def test_upload_unsupported_file_type_is_rejected(self):
        response = client.post(
            "/api/v1/resumes",
            files={"file": ("resume.txt", io.BytesIO(b"hello"), "text/plain")},
        )

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_upload_oversized_file_is_rejected(self):
        from app.config import get_settings

        get_settings().max_upload_size_mb  # ensure settings loaded
        oversized_content = b"%PDF-1.4\n" + (b"0" * (11 * 1024 * 1024))

        response = client.post(
            "/api/v1/resumes",
            files={"file": ("resume.pdf", io.BytesIO(oversized_content), "application/pdf")},
        )

        assert response.status_code == 400
        assert "too large" in response.json()["detail"]

    def test_upload_empty_document_is_stored_but_needs_review(self):
        # An empty-but-valid DOCX is a legitimate (if useless) file - it
        # should be accepted and stored, but flagged for manual review
        # rather than silently producing an empty profile.
        content = build_docx([])
        response = client.post(
            "/api/v1/resumes",
            files={
                "file": (
                    "empty.docx",
                    io.BytesIO(content),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "needs_review"
        assert body["parse_error"] is not None

    def test_upload_zero_byte_file_is_rejected(self):
        response = client.post(
            "/api/v1/resumes",
            files={"file": ("resume.pdf", io.BytesIO(b""), "application/pdf")},
        )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"]


class TestResumeProfile:
    def test_get_profile_returns_structured_data(self):
        upload_response = _upload_sample_docx()
        resume_id = upload_response.json()["id"]

        response = client.get(f"/api/v1/resumes/{resume_id}/profile")

        assert response.status_code == 200
        body = response.json()
        assert body["full_name"] == "Jane Doe"
        assert body["email"] == "jane.doe@example.com"
        assert {s["name"] for s in body["skills"]} == {"Python", "FastAPI", "Django", "SQL"}
        assert len(body["experiences"]) == 1
        assert len(body["education_entries"]) == 1

        # Every extracted item must carry source-of-truth metadata.
        for skill in body["skills"]:
            assert skill["source"] == "resume"
            assert skill["verified"] is False

    def test_get_profile_for_missing_resume_returns_404(self):
        response = client.get("/api/v1/resumes/does-not-exist/profile")

        assert response.status_code == 404

    def test_list_resumes_returns_uploaded_resume(self):
        _upload_sample_docx()

        response = client.get("/api/v1/resumes")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["full_name"] == "Jane Doe"


class TestResumeUpdate:
    def test_update_corrects_name_and_replaces_skills(self):
        upload_response = _upload_sample_docx()
        resume_id = upload_response.json()["id"]

        response = client.put(
            f"/api/v1/resumes/{resume_id}",
            json={
                "full_name": "Jane A. Doe",
                "skills": [
                    {"name": "Python", "verified": True},
                    {"name": "Kubernetes", "verified": True},
                ],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["full_name"] == "Jane A. Doe"
        skill_names = {s["name"] for s in body["skills"]}
        assert skill_names == {"Python", "Kubernetes"}
        for skill in body["skills"]:
            assert skill["source"] == "user"
            assert skill["verified"] is True

    def test_update_missing_resume_returns_404(self):
        response = client.put(
            "/api/v1/resumes/does-not-exist", json={"full_name": "Someone"}
        )

        assert response.status_code == 404

    def test_update_partial_payload_leaves_other_fields_unchanged(self):
        upload_response = _upload_sample_docx()
        resume_id = upload_response.json()["id"]

        response = client.put(f"/api/v1/resumes/{resume_id}", json={"phone": "555-0000"})

        assert response.status_code == 200
        body = response.json()
        assert body["phone"] == "555-0000"
        # Untouched fields (extracted at upload time) must survive.
        assert body["full_name"] == "Jane Doe"
        assert len(body["skills"]) == 4


class TestResumeVerification:
    def test_verify_transitions_status_to_verified(self):
        upload_response = _upload_sample_docx()
        resume_id = upload_response.json()["id"]

        response = client.post(f"/api/v1/resumes/{resume_id}/verify")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "verified"
        assert body["verified_at"] is not None

    def test_cannot_update_a_verified_resume(self):
        upload_response = _upload_sample_docx()
        resume_id = upload_response.json()["id"]
        client.post(f"/api/v1/resumes/{resume_id}/verify")

        response = client.put(f"/api/v1/resumes/{resume_id}", json={"full_name": "Someone Else"})

        assert response.status_code == 409

    def test_verify_missing_resume_returns_404(self):
        response = client.post("/api/v1/resumes/does-not-exist/verify")

        assert response.status_code == 404

    def test_verifying_twice_is_idempotent(self):
        upload_response = _upload_sample_docx()
        resume_id = upload_response.json()["id"]

        first = client.post(f"/api/v1/resumes/{resume_id}/verify")
        second = client.post(f"/api/v1/resumes/{resume_id}/verify")

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["status"] == "verified"
