import pytest

from app.core.parsing.docx_parser import DocxParseError, extract_text
from tests.backend.helpers.pdf_docx_builders import build_docx


def test_extracts_paragraph_text_in_order():
    content = build_docx(["Jane Doe", "Software Engineer", "Skills: Python, SQL"])

    text = extract_text(content)

    lines = text.split("\n")
    assert lines == ["Jane Doe", "Software Engineer", "Skills: Python, SQL"]


def test_skips_empty_paragraphs():
    content = build_docx(["Jane Doe", "", "", "Software Engineer"])

    text = extract_text(content)

    assert "Jane Doe" in text
    assert "Software Engineer" in text
    assert text == "Jane Doe\nSoftware Engineer"


def test_raises_on_invalid_docx_bytes():
    with pytest.raises(DocxParseError):
        extract_text(b"this is not a real docx file")


def test_empty_document_produces_empty_text():
    content = build_docx([])

    text = extract_text(content)

    assert text == ""
