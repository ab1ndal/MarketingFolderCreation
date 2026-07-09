"""Background worker that renders the A250 docx and converts it to PDF.

Lives on its own QThread (moveToThread pattern). COM is initialized on this
thread; a single hidden Word instance is reused across renders. Rapid requests
coalesce to the latest input.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from utils import docx_pdf

# NOTE: render_a250_docx lives in app.py, which imports this module — importing
# it at module top would create a cycle. It is resolved lazily in _run().


class A250PreviewWorker(QObject):
    finished = pyqtSignal(str)   # pdf path
    failed = pyqtSignal(str)     # error message

    def __init__(self, render_fn=None, converter=None, parent=None):
        super().__init__(parent)
        # render_fn defaults to app.render_a250_docx, resolved lazily to avoid
        # an import cycle. Tests inject a fake render_fn directly.
        self._render_fn = render_fn
        # converter(docx_path, pdf_path) -> None; None means use the real Word path.
        self._converter = converter
        self._word = None
        self._busy = False
        self._pending = None            # latest raw dict awaiting render, or None
        self._tmp_dir = Path(tempfile.gettempdir()) / "a250_preview"
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        self._toggle = False            # ping-pong between two pdf paths

    @pyqtSlot()
    def setup(self):
        """Runs in the worker thread (connected to QThread.started)."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

    @pyqtSlot(dict)
    def request_render(self, raw: dict):
        if self._busy:
            self._pending = raw          # keep only the latest
            return
        self._run(raw)

    def _drain_pending(self):
        if self._pending is not None and not self._busy:
            raw, self._pending = self._pending, None
            self._run(raw)

    def _run(self, raw: dict):
        self._busy = True
        try:
            if self._render_fn is None:
                from app import render_a250_docx  # lazy — breaks import cycle
                self._render_fn = render_a250_docx
            docx_path = self._tmp_dir / "preview.docx"
            self._toggle = not self._toggle
            pdf_path = self._tmp_dir / ("preview_a.pdf" if self._toggle else "preview_b.pdf")
            self._render_fn(raw, docx_path)
            self._convert(docx_path, pdf_path)
            self.finished.emit(str(pdf_path))
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            self._busy = False
            self._drain_pending()

    def _convert(self, docx_path: Path, pdf_path: Path):
        if self._converter is not None:
            self._converter(docx_path, pdf_path)
            return
        if self._word is None:
            self._word = docx_pdf.create_word()
        docx_pdf.docx_to_pdf(self._word, docx_path, pdf_path)

    @pyqtSlot()
    def shutdown(self):
        if self._word is not None:
            try:
                self._word.Quit()
            except Exception:
                pass
            self._word = None
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass
        for p in self._tmp_dir.glob("preview*.*"):
            try:
                p.unlink()
            except Exception:
                pass
