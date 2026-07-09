import pytest
from utils.docx_pdf import word_available, create_word, docx_to_pdf


def test_word_available_returns_bool():
    result = word_available()
    assert isinstance(result, bool)


@pytest.mark.skipif(not word_available(), reason="MS Word not available")
def test_docx_to_pdf_produces_pdf(tmp_path):
    import pythoncom
    from docxtpl import DocxTemplate
    from app import _resource_path

    # Render the real A250 template with a minimal context to a temp docx.
    docx_path = tmp_path / "in.docx"
    doc = DocxTemplate(_resource_path("templates/A250.docx"))
    doc.render({})
    doc.save(docx_path)

    pdf_path = tmp_path / "out.pdf"
    pythoncom.CoInitialize()
    try:
        word = create_word()
        try:
            docx_to_pdf(word, docx_path, pdf_path)
        finally:
            word.Quit()
    finally:
        pythoncom.CoUninitialize()

    assert pdf_path.exists()
    assert pdf_path.read_bytes()[:4] == b"%PDF"
