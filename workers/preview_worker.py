"""Background worker that renders the A250 docx and converts it to PDF.

Lives on its own QThread (moveToThread pattern). COM is initialized on this
thread; a single hidden Word instance is reused across renders. Rapid requests
coalesce to the latest input.
"""
from __future__ import annotations

import shutil
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
        # Private per-instance temp dir. A fixed shared path (e.g.
        # %TEMP%/a250_preview/preview.docx) can be locked by a leftover/zombie
        # Word process from a prior session, permanently blocking renders with
        # "file in use" / PermissionError (Errno 13). A unique dir per worker
        # isolates this session from any other process's stale locks.
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="a250_preview_"))
        self._seq = 0                   # rotates temp filenames (mod 3)

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

    def _run(self, raw: dict):
        self._busy = True
        try:
            while True:
                self._render_once(raw)
                if self._pending is None:
                    break
                raw, self._pending = self._pending, None
        finally:
            self._busy = False

    def _render_once(self, raw: dict) -> None:
        """Render+convert one request, retrying once on failure.

        A persistent hidden Word instance can die mid-session (crashed, killed,
        or "interface is unknown") and leave its docx/pdf locked. On failure we
        discard the (possibly dead) instance and retry with a rotated filename
        slot, so a stale lock from the dead instance can't block the retry.
        Filenames rotate mod 3 so neither attempt reuses the slot currently held
        open by the on-screen QPdfView.
        """
        if self._render_fn is None:
            from app import render_a250_docx  # lazy — breaks import cycle
            self._render_fn = render_a250_docx

        last_err = None
        for _attempt in range(2):
            self._seq += 1
            slot = self._seq % 3
            docx_path = self._tmp_dir / f"preview_{slot}.docx"
            pdf_path = self._tmp_dir / f"preview_{slot}.pdf"
            try:
                self._render_fn(raw, docx_path)
                self._convert(docx_path, pdf_path)
                self.finished.emit(str(pdf_path))
                return
            except Exception as e:
                last_err = e
                self._discard_word()   # dead/locked → recreate + rotate on retry
        self.failed.emit(str(last_err))

    def _discard_word(self) -> None:
        if self._word is not None:
            try:
                self._word.Quit()
            except Exception:
                pass
            self._word = None

    def _convert(self, docx_path: Path, pdf_path: Path):
        if self._converter is not None:
            self._converter(docx_path, pdf_path)
            return
        if self._word is None:
            self._word = docx_pdf.create_word()
        docx_pdf.docx_to_pdf(self._word, docx_path, pdf_path)

    @pyqtSlot()
    def shutdown(self):
        self._discard_word()
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass
        # Remove the whole private temp dir (docx + ping-pong PDFs).
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
