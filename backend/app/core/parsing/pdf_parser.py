"""
PDF text extraction.

Same narrow responsibility as docx_parser.py: bytes in, plain text out.
No structural interpretation happens here.
"""

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PdfParseError(ValueError):
    """Raised when a PDF file cannot be read/parsed."""


def extract_text(content: bytes) -> str:
    """Extract plain text from PDF file bytes.

    Raises PdfParseError if the file is not a valid, readable PDF.
    """
    try:
        reader = PdfReader(io.BytesIO(content))
    except (PdfReadError, Exception) as exc:  # pypdf can raise various errors
        raise PdfParseError(f"Could not read PDF file: {exc}") from exc

    if reader.is_encrypted:
        raise PdfParseError("PDF is encrypted/password-protected and cannot be parsed")

    lines: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - defensive, pypdf-internal
            raise PdfParseError(f"Failed to extract text from PDF page: {exc}") from exc

        for raw_line in page_text.splitlines():
            line = raw_line.strip()
            if line:
                lines.append(line)

    return "\n".join(lines)
