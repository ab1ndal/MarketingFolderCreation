"""Unit tests for utils.richtext_utils — html_to_richtext and RichTextEditor."""

import sys
import pytest
from unittest.mock import Mock


# --------------------------------------------------------------------------- #
# Module-scoped QApplication for widget tests
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# --------------------------------------------------------------------------- #
# html_to_richtext tests — no QApplication needed
# --------------------------------------------------------------------------- #

class TestHtmlToRichtext:
    """Tests for the html_to_richtext(html) -> docxtpl.RichText converter."""

    def _collect_text(self, rt) -> str:
        """Collect all text from RichText XML output."""
        import re
        xml = rt.xml or ""
        # Extract text content from w:t elements
        parts = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', xml)
        return "".join(parts)

    def _get_xml(self, rt) -> str:
        """Return the full XML string for the RichText."""
        return rt.xml or ""

    def test_plain_text(self):
        """Plain text 'Hello' -> RichText with one segment, no formatting."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("Hello")
        assert rt is not None
        text = self._collect_text(rt)
        assert "Hello" in text

    def test_bold(self):
        """<b>Hello</b> -> RichText segment with bold=True."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("<b>Hello</b>")
        assert "Hello" in self._collect_text(rt)
        xml = self._get_xml(rt)
        assert 'w:b' in xml, f"Expected w:b in XML: {xml}"

    def test_italic(self):
        """<i>Hello</i> -> RichText segment with italic=True."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("<i>Hello</i>")
        assert "Hello" in self._collect_text(rt)
        xml = self._get_xml(rt)
        assert 'w:i' in xml, f"Expected w:i in XML: {xml}"

    def test_underline(self):
        """<u>Hello</u> -> RichText segment with underline=True."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("<u>Hello</u>")
        assert "Hello" in self._collect_text(rt)
        xml = self._get_xml(rt)
        assert 'w:u' in xml, f"Expected w:u in XML: {xml}"

    def test_strikethrough_s_tag(self):
        """<s>Hello</s> -> RichText segment with strike=True."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("<s>Hello</s>")
        assert "Hello" in self._collect_text(rt)
        xml = self._get_xml(rt)
        assert 'w:strike' in xml, f"Expected w:strike in XML: {xml}"

    def test_strikethrough_del_tag(self):
        """<del>Hello</del> -> RichText segment with strike=True."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("<del>Hello</del>")
        assert "Hello" in self._collect_text(rt)
        xml = self._get_xml(rt)
        assert 'w:strike' in xml, f"Expected w:strike in XML: {xml}"

    def test_bold_italic_combined(self):
        """<b><i>Hello</i></b> -> segment with bold=True and italic=True."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("<b><i>Hello</i></b>")
        assert "Hello" in self._collect_text(rt)
        xml = self._get_xml(rt)
        assert 'w:b' in xml and 'w:i' in xml, f"Expected bold+italic in XML: {xml}"

    def test_bullet_list_item(self):
        """<li>Item</li> -> segment text contains bullet char."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("<li>Item</li>")
        xml = self._get_xml(rt)
        assert "\u2022" in xml or "&#8226;" in xml or "•" in xml, \
            f"Expected bullet in XML: {repr(xml)}"
        assert "Item" in xml

    def test_multi_paragraph(self):
        """Two <p> tags -> segments separated by newline."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("<p>First</p><p>Second</p>")
        xml = self._get_xml(rt)
        assert "First" in xml
        assert "Second" in xml
        # Newline is in separate run or encoded
        assert "\n" in xml or "&#10;" in xml

    def test_empty_string(self):
        """Empty string '' -> RichText with no content (empty xml)."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("")
        assert rt.xml == ""

    def test_whitespace_only(self):
        """Whitespace-only input -> RichText with empty or blank xml."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("   \n\t  ")
        text = self._collect_text(rt)
        assert text.strip() == ""

    def test_html_entities_decoded(self):
        """HTML entities like &nbsp; are decoded to plain chars."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("Hello&nbsp;World")
        xml = self._get_xml(rt)
        assert "Hello" in xml
        assert "World" in xml
        assert "&nbsp;" not in xml

    def test_qtextedit_html_wrapper(self):
        """QTextEdit-style wrapper HTML is handled (style= attrs ignored, content extracted)."""
        from utils.richtext_utils import html_to_richtext
        html = (
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" '
            '"http://www.w3.org/TR/REC-html40/strict.dtd">'
            '<html><head></head><body style="font-size:9pt;">'
            '<p style="margin-top:0px;">Hello <b>World</b></p>'
            '</body></html>'
        )
        rt = html_to_richtext(html)
        xml = self._get_xml(rt)
        assert "Hello" in xml
        assert "World" in xml

    def test_strong_tag_treated_as_bold(self):
        """<strong> tag -> same as bold."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("<strong>Hello</strong>")
        assert "Hello" in self._collect_text(rt)
        xml = self._get_xml(rt)
        assert 'w:b' in xml, f"Expected w:b in XML: {xml}"

    def test_em_tag_treated_as_italic(self):
        """<em> tag -> same as italic."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("<em>Hello</em>")
        assert "Hello" in self._collect_text(rt)
        xml = self._get_xml(rt)
        assert 'w:i' in xml, f"Expected w:i in XML: {xml}"


# --------------------------------------------------------------------------- #
# RichTextEditor widget tests — require QApplication
# --------------------------------------------------------------------------- #

class TestRichTextEditor:
    """Tests for RichTextEditor widget instantiation and interface."""

    def test_instantiation(self, qapp):
        """RichTextEditor can be instantiated without error."""
        from utils.richtext_utils import RichTextEditor
        widget = RichTextEditor()
        assert widget is not None

    def test_instantiation_with_height(self, qapp):
        """RichTextEditor accepts height parameter."""
        from utils.richtext_utils import RichTextEditor
        widget = RichTextEditor(height=120)
        assert widget is not None

    def test_to_html_returns_string(self, qapp):
        """toHtml() returns a string."""
        from utils.richtext_utils import RichTextEditor
        widget = RichTextEditor()
        result = widget.toHtml()
        assert isinstance(result, str)

    def test_to_plain_text_returns_string(self, qapp):
        """toPlainText() returns a string."""
        from utils.richtext_utils import RichTextEditor
        widget = RichTextEditor()
        result = widget.toPlainText()
        assert isinstance(result, str)

    def test_set_placeholder_text(self, qapp):
        """setPlaceholderText() does not raise."""
        from utils.richtext_utils import RichTextEditor
        widget = RichTextEditor()
        widget.setPlaceholderText("Enter description...")

    def test_exports(self):
        """utils.richtext_utils exports RichTextEditor and html_to_richtext."""
        from utils.richtext_utils import RichTextEditor, html_to_richtext
        assert callable(html_to_richtext)
        assert RichTextEditor is not None
