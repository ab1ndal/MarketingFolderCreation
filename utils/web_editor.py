"""Web-based rich text editor using QWebEngineView + Quill (offline)."""

from __future__ import annotations
import sys
import threading
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl


def _resource_path(relative: str) -> Path:
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent))
    return base / relative


class WebRichTextEditor(QWidget):
    """Quill-based rich text editor embedded in QWebEngineView.

    Public interface:
        get_html_sync(timeout_ms=2000) -> str
            Synchronous call that blocks until JS runJavaScript callback fires.
            Uses threading.Event + QTimer poll loop — safe to call from the
            main Qt thread (does NOT block the event loop; uses processEvents).
        set_html(html: str) -> None
    """

    def __init__(self, parent=None, height: int = 150):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._view = QWebEngineView()
        self._view.setFixedHeight(height)
        layout.addWidget(self._view)

        editor_html = _resource_path("assets/editor.html")
        self._view.load(QUrl.fromLocalFile(str(editor_html)))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_html_sync(self, timeout_ms: int = 2000) -> str:
        """Return Quill innerHTML synchronously.

        Runs a QEventLoop-free poll: sets a threading.Event from the JS
        callback, then processEvents in a tight loop until the event fires
        or timeout elapses.
        """
        from PyQt6.QtWidgets import QApplication

        result: list[str] = []
        done = threading.Event()

        def _cb(value):
            result.append(value if value else "")
            done.set()

        self._view.page().runJavaScript("getContent();", _cb)

        # Poll processEvents until callback fires (stays on main thread)
        interval_ms = 10
        elapsed = 0
        while not done.is_set() and elapsed < timeout_ms:
            QApplication.processEvents()
            done.wait(interval_ms / 1000)
            elapsed += interval_ms

        return result[0] if result else ""

    def set_html(self, html: str) -> None:
        escaped = html.replace("\\", "\\\\").replace("`", "\\`")
        self._view.page().runJavaScript(f"setContent(`{escaped}`);")

    # Compatibility shims so isinstance checks in app.py remain simple
    def toHtml(self) -> str:
        """Synchronous alias for get_html_sync (for compatibility)."""
        return self.get_html_sync()

    def toPlainText(self) -> str:
        """Strip tags from HTML content — used for plain-text fallback."""
        import re
        return re.sub(r'<[^>]+>', '', self.get_html_sync()).strip()
