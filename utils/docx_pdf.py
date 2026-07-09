"""Convert docx to PDF via Microsoft Word COM automation.

Windows + Word only. Uses dynamic Dispatch (never EnsureDispatch) so no
gen_py makepy cache is required — that cache breaks a PyInstaller-frozen exe.
"""
from __future__ import annotations

from pathlib import Path

# wdExportFormatPDF
_WD_EXPORT_FORMAT_PDF = 17

_word_available_cache: bool | None = None


def word_available() -> bool:
    """Return True if Word can be launched via COM. Cached after first probe."""
    global _word_available_cache
    if _word_available_cache is not None:
        return _word_available_cache
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        try:
            app = win32com.client.Dispatch("Word.Application")
            app.Quit()
            _word_available_cache = True
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        _word_available_cache = False
    return _word_available_cache


def create_word():
    """Create and return a hidden Word Application COM object.

    Caller is responsible for CoInitialize on its thread before calling this
    and for calling app.Quit() when done.
    """
    import win32com.client

    app = win32com.client.Dispatch("Word.Application")
    app.Visible = False
    app.DisplayAlerts = 0  # wdAlertsNone
    return app


def docx_to_pdf(word_app, docx_path: Path, pdf_path: Path) -> None:
    """Convert docx_path to pdf_path using an already-open Word instance."""
    doc = word_app.Documents.Open(
        str(Path(docx_path).resolve()),
        ReadOnly=True,
        AddToRecentFiles=False,
    )
    try:
        doc.ExportAsFixedFormat(
            OutputFileName=str(Path(pdf_path).resolve()),
            ExportFormat=_WD_EXPORT_FORMAT_PDF,
        )
    finally:
        try:
            doc.Close(False)
        except Exception:
            # Word COM can disconnect after export; the PDF is already written
            pass
