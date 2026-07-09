"""PDF preview pane for the A250 dialog — shows the exact rendered document.

States (StackAll overlay):
  - _view    : the QPdfView (base layer)
  - _message : full-pane centered text (rendering / Word-missing / first-error)
  - _updating: top-right opaque badge shown during a refresh
  - _error   : bottom opaque banner shown over a stale PDF after a failure
Scroll position is preserved across reloads so the 1.5s refresh doesn't yank
the user back to page 1 while they read Exhibit A / Terms.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QStackedLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView


class A250PreviewPane(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._has_pdf = False
        self._pending_scroll = 0

        self._layout = QStackedLayout(self)
        self._layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self._doc = QPdfDocument(self)
        self._view = QPdfView(self)
        self._view.setDocument(self._doc)
        self._view.setPageMode(QPdfView.PageMode.MultiPage)
        self._view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self._layout.addWidget(self._view)
        # Restore scroll once the (async) load finishes.
        self._doc.statusChanged.connect(self._on_status)

        self._message = QLabel("", self)
        self._message.setWordWrap(True)
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message.setStyleSheet("color:#555; background:#f4f4f4; font-size:14px; padding:24px;")
        self._message.hide()
        self._layout.addWidget(self._message)

        # Opaque pill so it reads over any page content (review: contrast fix).
        self._updating = QLabel("updating…", self)
        self._updating.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self._updating.setStyleSheet(
            "color:#ffffff; background:#2d7d46; font-size:12px;"
            "font-weight:bold; padding:4px 10px; border-radius:3px;"
        )
        self._updating.setFixedHeight(24)
        self._updating.hide()
        self._layout.addWidget(self._updating)

        self._error = QLabel("", self)
        self._error.setWordWrap(True)
        self._error.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self._error.setStyleSheet(
            "color:#ffffff; background:#c0392b; font-size:12px; padding:8px 12px;"
        )
        self._error.hide()
        self._layout.addWidget(self._error)

        self._layout.setCurrentWidget(self._view)

    def _on_status(self, status) -> None:
        if status == QPdfDocument.Status.Ready:
            self._has_pdf = True
            self._view.verticalScrollBar().setValue(self._pending_scroll)
        elif status == QPdfDocument.Status.Error:
            self._has_pdf = False

    def show_pdf(self, path: str) -> None:
        self._pending_scroll = self._view.verticalScrollBar().value()
        self._message.hide()
        self._error.hide()
        self._view.show()
        self._doc.load(path)

    def set_updating(self, on: bool) -> None:
        self._updating.setVisible(on)
        if on:
            self._updating.raise_()

    def show_rendering(self) -> None:
        self._show_message("Rendering preview…")

    def show_unavailable(self, msg: str) -> None:
        self._show_message(msg)

    def show_error(self, msg: str) -> None:
        self.set_updating(False)
        if self._has_pdf:
            # Keep the (stale) PDF visible; banner tells the user it's outdated.
            self._error.setText(f"{msg}\nShowing last successful render.")
            self._error.show()
            self._error.raise_()
        else:
            self._show_message(f"Preview failed:\n{msg}")

    def _show_message(self, text: str) -> None:
        self._message.setText(text)
        self._error.hide()
        self._updating.hide()
        self._view.hide()
        self._message.show()
        self._message.raise_()
