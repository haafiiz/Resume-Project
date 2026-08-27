import pytest

from app.core.parsing.pdf_parser import PdfParseError, extract_text
from tests.backend.helpers.pdf_docx_builders import build_pdf


def test_extracts_text_lines_in_order():
    content = build_pdf(["John Smith", "john.smith@example.com", "Seattle, WA"])

    text = extract_text(content)

    lines = text.split("\n")
    assert lines == ["John Smith", "john.smith@example.com", "Seattle, WA"]


def test_raises_on_invalid_pdf_bytes():
    with pytest.raises(PdfParseError):
        extract_text(b"this is not a real pdf file")


def test_empty_pdf_produces_empty_text():
    content = build_pdf([])

    text = extract_text(content)

    assert text == ""
