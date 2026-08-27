import pytest

from app.utils.upload_validation import UploadValidationError, validate_upload
from tests.backend.helpers.pdf_docx_builders import build_docx, build_pdf


def test_accepts_valid_docx():
    content = build_docx(["Jane Doe"])

    result = validate_upload(
        "resume.docx",
        content,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert result.extension == ".docx"
    assert result.size_bytes == len(content)


def test_accepts_valid_pdf():
    content = build_pdf(["Jane Doe"])

    result = validate_upload("resume.pdf", content, "application/pdf")

    assert result.extension == ".pdf"


def test_rejects_unsupported_extension():
    with pytest.raises(UploadValidationError, match="Unsupported file type"):
        validate_upload("resume.txt", b"hello world", "text/plain")


def test_rejects_oversized_file(monkeypatch):
    from app.utils import upload_validation

    monkeypatch.setattr(upload_validation.settings, "max_upload_size_mb", 1)

    oversized_content = b"%PDF-1.4\n" + (b"0" * (2 * 1024 * 1024))

    with pytest.raises(UploadValidationError, match="too large"):
        validate_upload("resume.pdf", oversized_content, "application/pdf")


def test_rejects_empty_file():
    with pytest.raises(UploadValidationError, match="empty"):
        validate_upload("resume.pdf", b"", "application/pdf")


def test_rejects_missing_filename():
    with pytest.raises(UploadValidationError, match="filename is required"):
        validate_upload(None, b"%PDF-1.4\ncontent", "application/pdf")


def test_rejects_content_that_does_not_match_extension():
    # A .pdf filename but content that doesn't start with the PDF magic
    # bytes - the file signature is the ground truth, not the extension.
    with pytest.raises(UploadValidationError, match="does not match"):
        validate_upload("resume.pdf", b"not actually a pdf", "application/pdf")


def test_rejects_path_like_filename():
    with pytest.raises(UploadValidationError, match="invalid characters"):
        validate_upload("../../etc/passwd.pdf", b"%PDF-1.4\ncontent", "application/pdf")
