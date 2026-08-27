"""
Safe on-disk storage for uploaded resume files.

Responsibilities:
- Generate collision-free, filesystem-safe stored filenames (never trust
  or reuse the client-provided filename for the on-disk name).
- Write uploaded bytes under storage/uploads/.
- Never expose the resulting filesystem path to API responses - callers
  should only ever hand back a resume's database id.
"""

import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()


def get_upload_dir() -> Path:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def generate_stored_filename(extension: str) -> str:
    """Generate a unique, safe filename for storing an uploaded file.

    Uses a UUID so it can never collide with an existing file and never
    leaks anything about the original filename (which may contain
    arbitrary/unsafe characters or path segments).
    """
    ext = extension.lower().lstrip(".")
    return f"{uuid.uuid4()}.{ext}"


def save_upload(content: bytes, extension: str) -> tuple[str, Path]:
    """Persist uploaded file content under storage/uploads/.

    Returns (stored_filename, full_path). Guarantees the target path did
    not already exist before writing (an uploaded file is never
    overwritten) by regenerating the filename on the rare UUID collision.
    """
    upload_dir = get_upload_dir()

    stored_filename = generate_stored_filename(extension)
    target_path = upload_dir / stored_filename

    # Practically unreachable given UUID4 collision odds, but guard it
    # explicitly rather than silently overwriting an existing upload.
    while target_path.exists():
        stored_filename = generate_stored_filename(extension)
        target_path = upload_dir / stored_filename

    target_path.write_bytes(content)
    return stored_filename, target_path


def get_upload_path(stored_filename: str) -> Path:
    return get_upload_dir() / stored_filename


def delete_upload(stored_filename: str) -> None:
    path = get_upload_path(stored_filename)
    if path.exists():
        path.unlink()
