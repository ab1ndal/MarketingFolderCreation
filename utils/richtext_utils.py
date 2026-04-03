"""Rich-text utilities for the A250 form.

Exports:
    html_to_richtext - Convert QTextEdit/Quill HTML output to a docxtpl RichText object
"""

from __future__ import annotations

import html as _html_module
import re as _re
from html.parser import HTMLParser
from typing import List, Tuple

from docxtpl import RichText


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
                    font='Calibri Light',
                    size=20,
                )
        return rt


def _extract_body(html: str) -> str:
    """Return content between <body> tags, or original if no body tag."""
    m = _re.search(r'(?is)<body[^>]*>(.*?)</body>', html)
    return m.group(1) if m else html


def html_to_richtext(html: str) -> RichText:
    """Convert QTextEdit HTML output to a docxtpl RichText object.

    Handles bold/italic/underline/strikethrough formatting tags, <li> bullet
    items, paragraph breaks, HTML entities, and QTextEdit wrapper structure.

    Returns an empty RichText for empty or whitespace-only input.
    """
    if not html or not html.strip():
        return RichText()

    # Strip outer html/head/body wrapper tags (QTextEdit and Quill both add these)
    html = _re.sub(r'(?is)<html[^>]*>.*?</html>', lambda m: _extract_body(m.group(0)), html)

    parser = _HtmlToRichTextParser()
    parser.feed(html)
    return parser.build()
