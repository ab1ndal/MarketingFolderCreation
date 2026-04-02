"""Rich-text utilities for the A250 form.

Exports:
    RichTextEditor  - QWidget subclass with formatting toolbar above a QTextEdit
    html_to_richtext - Convert QTextEdit HTML output to a docxtpl RichText object
"""

from __future__ import annotations

import html as _html_module
from html.parser import HTMLParser
from typing import List, Tuple

from docxtpl import RichText

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QTextEdit, QPushButton,
)
from PyQt6.QtGui import QTextCharFormat, QTextCursor


# --------------------------------------------------------------------------- #
# html_to_richtext
# --------------------------------------------------------------------------- #

# Tags that toggle formatting flags
_BOLD_TAGS = {"b", "strong"}
_ITALIC_TAGS = {"i", "em"}
_UNDERLINE_TAGS = {"u"}
_STRIKE_TAGS = {"s", "del", "strike"}

# Tags whose close triggers a newline separator
_BLOCK_TAGS = {"p", "div", "li", "br"}


class _FormatState:
    """Mutable formatting state pushed/popped on the stack."""

    __slots__ = ("bold", "italic", "underline", "strike")

    def __init__(self, bold=False, italic=False, underline=False, strike=False):
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.strike = strike

    def copy(self) -> "_FormatState":
        return _FormatState(self.bold, self.italic, self.underline, self.strike)


class _HtmlToRichTextParser(HTMLParser):
    """HTMLParser subclass that accumulates (text, fmt) tuples.

    After parsing, call .build() to get a docxtpl.RichText.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        # Stack of _FormatState objects; bottom is default (no formatting)
        self._stack: List[_FormatState] = [_FormatState()]
        # Accumulated segments: list of (text, _FormatState)
        self._segments: List[Tuple[str, _FormatState]] = []
        # Whether we are inside a <li> element (to prepend bullet)
        self._in_li: bool = False
        self._li_first_char: bool = False
        # Track pending newline between block elements to avoid double-newlines
        self._pending_newline: bool = False

    @property
    def _current(self) -> _FormatState:
        return self._stack[-1]

    def _push(self, tag: str):
        """Push a new formatting state derived from the current one."""
        new = self._current.copy()
        if tag in _BOLD_TAGS:
            new.bold = True
        elif tag in _ITALIC_TAGS:
            new.italic = True
        elif tag in _UNDERLINE_TAGS:
            new.underline = True
        elif tag in _STRIKE_TAGS:
            new.strike = True
        self._stack.append(new)

    def _pop(self):
        if len(self._stack) > 1:
            self._stack.pop()

    def _flush_newline(self):
        """Emit a pending newline segment if one is queued."""
        if self._pending_newline:
            self._segments.append(("\n", _FormatState()))
            self._pending_newline = False

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag in _BOLD_TAGS | _ITALIC_TAGS | _UNDERLINE_TAGS | _STRIKE_TAGS:
            self._push(tag)
        elif tag == "li":
            self._push(tag)  # li itself doesn't add formatting; push copy
            self._in_li = True
            self._li_first_char = True
            self._flush_newline()
        elif tag in _BLOCK_TAGS:
            self._push(tag)
            if tag == "br":
                # <br> is self-closing in practice; emit newline immediately
                self._flush_newline()
                self._pending_newline = True
        # else: unknown/ignored tag (html, head, body, span, etc.) — push copy to balance
        else:
            self._stack.append(self._current.copy())

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        self._pop()
        if tag == "li":
            self._in_li = False
            self._pending_newline = True
        elif tag in _BLOCK_TAGS:
            self._pending_newline = True

    def handle_data(self, data: str):
        # html entities already decoded via convert_charrefs=True
        if not data:
            return

        # Strip leading/trailing newlines inserted by the HTML serialiser (not user content)
        # but preserve interior whitespace
        stripped = data.strip("\n\r")
        if not stripped and not self._in_li:
            return

        self._flush_newline()

        if self._in_li and self._li_first_char:
            stripped = "\u2022 " + stripped  # bullet + space
            self._li_first_char = False

        if stripped:
            self._segments.append((stripped, self._current.copy()))

    def build(self) -> RichText:
        """Construct a docxtpl.RichText from accumulated segments."""
        rt = RichText()
        for text, fmt in self._segments:
            if text:
                rt.add(
                    text,
                    bold=fmt.bold or None,
                    italic=fmt.italic or None,
                    underline=fmt.underline or None,
                    strike=fmt.strike or None,
                )
        return rt


def html_to_richtext(html: str) -> RichText:
    """Convert QTextEdit HTML output to a docxtpl RichText object.

    Handles bold/italic/underline/strikethrough formatting tags, <li> bullet
    items, paragraph breaks, HTML entities, and QTextEdit wrapper structure.

    Returns an empty RichText for empty or whitespace-only input.
    """
    if not html or not html.strip():
        return RichText()

    parser = _HtmlToRichTextParser()
    parser.feed(html)
    return parser.build()


# --------------------------------------------------------------------------- #
# RichTextEditor widget
# --------------------------------------------------------------------------- #

class RichTextEditor(QWidget):
    """A compact rich-text editor with a formatting toolbar.

    Provides a QToolBar (Bold, Italic, Underline, Strikethrough, Bullet List,
    Clear Formatting) stacked above a QTextEdit.

    Public interface (mirrors QTextEdit for drop-in use in a250_vars dict):
        toHtml()             -> str
        toPlainText()        -> str
        setPlaceholderText() -> None
        setFixedHeight(h)    -> None  (overridden to split between toolbar+editor)
    """

    def __init__(self, parent=None, height: int = 80):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        self._toolbar = QHBoxLayout()
        self._toolbar.setContentsMargins(2, 2, 2, 2)
        self._toolbar.setSpacing(2)

        # Formatting buttons (checkable)
        self._btn_bold = self._make_fmt_btn("B")
        self._btn_italic = self._make_fmt_btn("I")
        self._btn_underline = self._make_fmt_btn("U")
        self._btn_strike = self._make_fmt_btn("S")

        # Non-checkable action buttons
        self._btn_bullet = QPushButton("• List")
        self._btn_bullet.setFixedHeight(22)
        self._btn_clear = QPushButton("✕ Clear")
        self._btn_clear.setFixedHeight(22)

        for btn in (self._btn_bold, self._btn_italic, self._btn_underline,
                    self._btn_strike, self._btn_bullet, self._btn_clear):
            self._toolbar.addWidget(btn)
        self._toolbar.addStretch()

        toolbar_widget = QWidget()
        toolbar_widget.setLayout(self._toolbar)
        toolbar_widget.setFixedHeight(28)

        # Text editor
        self._editor = QTextEdit()
        editor_height = max(40, height - 28)
        self._editor.setFixedHeight(editor_height)

        layout.addWidget(toolbar_widget)
        layout.addWidget(self._editor)

        # Connect toolbar actions
        self._btn_bold.clicked.connect(self._toggle_bold)
        self._btn_italic.clicked.connect(self._toggle_italic)
        self._btn_underline.clicked.connect(self._toggle_underline)
        self._btn_strike.clicked.connect(self._toggle_strike)
        self._btn_bullet.clicked.connect(self._insert_bullet)
        self._btn_clear.clicked.connect(self._clear_format)

        # Keep button checked states in sync with cursor position
        self._editor.currentCharFormatChanged.connect(self._on_char_format_changed)

    # ------------------------------------------------------------------
    # Button factory
    # ------------------------------------------------------------------

    @staticmethod
    def _make_fmt_btn(label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setFixedHeight(22)
        btn.setFixedWidth(28)
        return btn

    # ------------------------------------------------------------------
    # Format toggle slots
    # ------------------------------------------------------------------

    def _toggle_bold(self):
        fmt = QTextCharFormat()
        weight = 400 if self._editor.fontWeight() > 400 else 700
        from PyQt6.QtGui import QFont
        fmt.setFontWeight(weight)
        self._editor.textCursor().mergeCharFormat(fmt)

    def _toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self._editor.fontItalic())
        self._editor.textCursor().mergeCharFormat(fmt)

    def _toggle_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self._editor.fontUnderline())
        self._editor.textCursor().mergeCharFormat(fmt)

    def _toggle_strike(self):
        fmt = QTextCharFormat()
        current = self._editor.currentCharFormat()
        fmt.setFontStrikeOut(not current.fontStrikeOut())
        self._editor.textCursor().mergeCharFormat(fmt)

    def _insert_bullet(self):
        """Prefix the current block with a bullet character."""
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.insertText("\u2022 ")

    def _clear_format(self):
        """Remove all character-level formatting from the selection."""
        self._editor.textCursor().mergeCharFormat(QTextCharFormat())

    # ------------------------------------------------------------------
    # Sync button states with cursor format
    # ------------------------------------------------------------------

    def _on_char_format_changed(self, fmt: QTextCharFormat):
        from PyQt6.QtGui import QFont
        self._btn_bold.setChecked(fmt.fontWeight() > 400)
        self._btn_italic.setChecked(fmt.fontItalic())
        self._btn_underline.setChecked(fmt.fontUnderline())
        self._btn_strike.setChecked(fmt.fontStrikeOut())

    # ------------------------------------------------------------------
    # Public interface (mirrors QTextEdit)
    # ------------------------------------------------------------------

    def toHtml(self) -> str:
        return self._editor.toHtml()

    def toPlainText(self) -> str:
        return self._editor.toPlainText()

    def setPlaceholderText(self, text: str):
        self._editor.setPlaceholderText(text)

    def setFixedHeight(self, h: int):
        super().setFixedHeight(h)
        editor_height = max(40, h - 28)
        self._editor.setFixedHeight(editor_height)
