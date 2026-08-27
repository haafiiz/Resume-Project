"""
Upload validation for resume files.

Validates filename, extension, declared content-type, actual file
signature (magic bytes), and size before a file is ever written to disk
or handed to a parser. Rejects anything that doesn't clearly look like a
genuine PDF or DOCX file - client-declared content-type is never trusted
on its own, since it's trivial to spoof.
"""

from dataclasses import dataclass

from app.config import get_settings

settings = get_settings()

# Signature (magic bytes) each supported extension's real file format
# should start with. DOCX files are ZIP archives (OOXML), so they share
# the ZIP signature.
_SIGNATURES: dict[str, bytes] = {
    ".pdf": b"%PDF",
    ".docx": b"PK\x03\x04",
}

# Content-types browsers/clients commonly declare for each extension.
# Used as a plausibility check, not the sole source of truth.
_ACCEPTABLE_CONTENT_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",  # some clients don't set a specific type
        "application/zip",
    },
}


class UploadValidationError(ValueError):
    """Raised when an uploaded file fails validation. The message is
    safe to return directly to the client."""


@dataclass
class ValidatedUpload:
    extension: str
    content_type: str
    size_bytes: int


def _get_extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def validate_upload(
    filename: str | None, content: bytes, declared_content_type: str | None
) -> ValidatedUpload:
    """Validate an uploaded resume file. Raises UploadValidationError on
    any failure; returns the validated extension/content-type/size on
    success."""

    if not filename or not filename.strip():
        raise UploadValidationError("A filename is required.")

    # Reject path-like or otherwise unsafe filenames outright - we never
    # use the client filename for storage, but a suspicious filename is
    # still a signal to reject the upload rather than silently sanitize
    # and proceed.
    if "/" in filename or "\\" in filename or filename in {".", ".."}:
        raise UploadValidationError("Filename contains invalid characters.")

    if len(filename) > 255:
        raise UploadValidationError("Filename is too long.")

    extension = _get_extension(filename)
    if extension not in settings.allowed_upload_extension_list:
        allowed = ", ".join(settings.allowed_upload_extension_list)
        raise UploadValidationError(
            f"Unsupported file type '{extension or 'unknown'}'. Allowed types: {allowed}."
        )

    size_bytes = len(content)
    if size_bytes == 0:
        raise UploadValidationError("The uploaded file is empty.")

    if size_bytes > settings.max_upload_size_bytes:
        raise UploadValidationError(
            f"File is too large ({size_bytes / 1_048_576:.1f} MB). "
            f"Maximum allowed size is {settings.max_upload_size_mb} MB."
        )

    expected_signature = _SIGNATURES.get(extension)
    if expected_signature and not content.startswith(expected_signature):
        raise UploadValidationError(
            "File content does not match its extension - "
            "the file may be corrupted or mislabeled."
        )

    content_type = (declared_content_type or "").split(";")[0].strip().lower()
    acceptable = _ACCEPTABLE_CONTENT_TYPES.get(extension, set())
    if content_type and acceptable and content_type not in acceptable:
        raise UploadValidationError(
            f"Declared content type '{content_type}' does not match the "
            f"expected type for a {extension} file."
        )

    return ValidatedUpload(
        extension=extension,
        content_type=content_type or (next(iter(acceptable)) if acceptable else "application/octet-stream"),
        size_bytes=size_bytes,
    )
