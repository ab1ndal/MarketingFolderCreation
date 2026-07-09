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


@pytest.mark.skipif(not word_available(), reason="MS Word not available")
def test_docx_to_pdf_releases_lock_for_reuse(tmp_path):
    """Regression: converting must CLOSE the document and release its file
    lock, so a persistent Word instance can re-render to the SAME docx path on
    the next update. If Close leaves the doc open (the old doc.Close() bug),
    the second overwrite raises PermissionError (Errno 13) — the live-preview
    crash reported on the 2nd keystroke."""
    import pythoncom
    from docxtpl import DocxTemplate
    from app import _resource_path

    docx_path = tmp_path / "preview.docx"   # fixed name, reused
    pdf_path = tmp_path / "out.pdf"

    def render(text):
        d = DocxTemplate(_resource_path("templates/A250.docx"))
        d.render({"project_title": text})
        d.save(docx_path)                    # overwrite the same path

    pythoncom.CoInitialize()
    try:
        word = create_word()                 # ONE persistent instance
        try:
            render("first")
            docx_to_pdf(word, docx_path, pdf_path)
            # Second cycle overwrites the same docx — must not be locked.
            render("second")                  # would raise Errno 13 if still locked
            docx_to_pdf(word, docx_path, pdf_path)
            assert word.Documents.Count == 0  # doc actually closed, not accumulating
        finally:
            word.Quit()
    finally:
        pythoncom.CoUninitialize()

    assert pdf_path.read_bytes()[:4] == b"%PDF"
