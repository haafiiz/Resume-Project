"""
Test-only fixture builders for DOCX and PDF resume files.

DOCX files are built with python-docx (already a project dependency).
PDFs are hand-assembled as minimal, valid PDF byte streams so tests
don't need to add a PDF-generation library as a dependency just to
create fixtures - pypdf (the project's PDF *reading* dependency) can
read the result back out.
"""

import io

from docx import Document


def build_docx(lines: list[str]) -> bytes:
    document = Document()
    for line in lines:
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def build_pdf(lines: list[str]) -> bytes:
    """Build a minimal single-page PDF containing the given lines of text."""
    content_lines = ["BT", "/F1 12 Tf", "50 750 Td", "14 TL"]
    for i, line in enumerate(lines):
        escaped = _escape_pdf_text(line)
        if i == 0:
            content_lines.append(f"({escaped}) Tj")
        else:
            content_lines.append("T*")
            content_lines.append(f"({escaped}) Tj")
    content_lines.append("ET")
    content_stream = "\n".join(content_lines).encode("latin-1")

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(
        b"<< /Length " + str(len(content_stream)).encode("ascii") + b" >>\nstream\n"
        + content_stream
        + b"\nendstream"
    )

    buffer = io.BytesIO()
    buffer.write(b"%PDF-1.4\n")

    offsets = [0]  # object 0 is the free-list head, not written
    for i, obj_body in enumerate(objects, start=1):
        offsets.append(buffer.tell())
        buffer.write(f"{i} 0 obj\n".encode("ascii"))
        buffer.write(obj_body)
        buffer.write(b"\nendobj\n")

    xref_offset = buffer.tell()
    num_objects = len(objects) + 1
    buffer.write(f"xref\n0 {num_objects}\n".encode("ascii"))
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode("ascii"))

    buffer.write(b"trailer\n")
    buffer.write(f"<< /Size {num_objects} /Root 1 0 R >>\n".encode("ascii"))
    buffer.write(b"startxref\n")
    buffer.write(f"{xref_offset}\n".encode("ascii"))
    buffer.write(b"%%EOF")

    return buffer.getvalue()
