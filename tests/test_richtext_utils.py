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

    def _get_segments(self, rt):
        """Return the list of (text, kwargs) from a RichText object."""
        # docxtpl.RichText stores runs in ._r attribute as lxml element;
        # we inspect the internal list instead.
        return rt._r if hasattr(rt, "_r") else []

    def _collect_text(self, rt):
        """Collect all text from RichText segments as a concatenated string."""
        # RichText._r is a list of lxml elements; extract text from each
        import lxml.etree as etree
        parts = []
        for el in rt._r:
            t = el.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
            if t is not None and t.text:
                parts.append(t.text)
        return "".join(parts)

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
        import lxml.etree as etree
        rt = html_to_richtext("<b>Hello</b>")
        # Check that the XML contains a bold run property (w:b)
        xml = etree.tostring(rt._r[0], encoding="unicode") if rt._r else ""
        assert "Hello" in self._collect_text(rt)
        # The XML string for a bold run should contain w:b
        full_xml = etree.tostring(rt._r[0]).decode() if rt._r else ""
        assert 'w:b' in full_xml or 'bold' in full_xml.lower(), f"Expected bold in XML: {full_xml}"

    def test_italic(self):
        """<i>Hello</i> -> RichText segment with italic=True."""
        from utils.richtext_utils import html_to_richtext
        import lxml.etree as etree
        rt = html_to_richtext("<i>Hello</i>")
        assert "Hello" in self._collect_text(rt)
        full_xml = etree.tostring(rt._r[0]).decode() if rt._r else ""
        assert 'w:i' in full_xml or 'italic' in full_xml.lower(), f"Expected italic in XML: {full_xml}"

    def test_underline(self):
        """<u>Hello</u> -> RichText segment with underline=True."""
        from utils.richtext_utils import html_to_richtext
        import lxml.etree as etree
        rt = html_to_richtext("<u>Hello</u>")
        assert "Hello" in self._collect_text(rt)
        full_xml = etree.tostring(rt._r[0]).decode() if rt._r else ""
        assert 'w:u' in full_xml or 'underline' in full_xml.lower(), f"Expected underline in XML: {full_xml}"

    def test_strikethrough_s_tag(self):
        """<s>Hello</s> -> RichText segment with strike=True."""
        from utils.richtext_utils import html_to_richtext
        import lxml.etree as etree
        rt = html_to_richtext("<s>Hello</s>")
        assert "Hello" in self._collect_text(rt)
        full_xml = etree.tostring(rt._r[0]).decode() if rt._r else ""
        assert 'w:strike' in full_xml or 'strike' in full_xml.lower(), f"Expected strike in XML: {full_xml}"

    def test_strikethrough_del_tag(self):
        """<del>Hello</del> -> RichText segment with strike=True."""
        from utils.richtext_utils import html_to_richtext
        import lxml.etree as etree
        rt = html_to_richtext("<del>Hello</del>")
        assert "Hello" in self._collect_text(rt)
        full_xml = etree.tostring(rt._r[0]).decode() if rt._r else ""
        assert 'w:strike' in full_xml or 'strike' in full_xml.lower(), f"Expected strike in XML: {full_xml}"

    def test_bold_italic_combined(self):
        """<b><i>Hello</i></b> -> segment with bold=True and italic=True."""
        from utils.richtext_utils import html_to_richtext
        import lxml.etree as etree
        rt = html_to_richtext("<b><i>Hello</i></b>")
        assert "Hello" in self._collect_text(rt)
        full_xml = etree.tostring(rt._r[0]).decode() if rt._r else ""
        assert 'w:b' in full_xml and 'w:i' in full_xml, f"Expected bold+italic in XML: {full_xml}"

    def test_bullet_list_item(self):
        """<li>Item</li> -> segment text contains bullet char and newline."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("<li>Item</li>")
        text = self._collect_text(rt)
        assert "\u2022" in text or "•" in text, f"Expected bullet in text: {repr(text)}"
        assert "Item" in text

    def test_multi_paragraph(self):
        """Two <p> tags -> segments separated by newline."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("<p>First</p><p>Second</p>")
        text = self._collect_text(rt)
        assert "First" in text
        assert "Second" in text
        assert "\n" in text

    def test_empty_string(self):
        """Empty string '' -> RichText with no segments."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("")
        assert len(rt._r) == 0

    def test_whitespace_only(self):
        """Whitespace-only input -> RichText with no segments."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("   \n\t  ")
        text = self._collect_text(rt)
        assert text.strip() == ""

    def test_html_entities_decoded(self):
        """HTML entities like &amp;nbsp; are decoded to plain chars."""
        from utils.richtext_utils import html_to_richtext
        rt = html_to_richtext("Hello&nbsp;World")
        text = self._collect_text(rt)
        assert "Hello" in text
        assert "World" in text
        assert "&nbsp;" not in text

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
        text = self._collect_text(rt)
        assert "Hello" in text
        assert "World" in text

    def test_strong_tag_treated_as_bold(self):
        """<strong> tag -> same as bold."""
        from utils.richtext_utils import html_to_richtext
        import lxml.etree as etree
        rt = html_to_richtext("<strong>Hello</strong>")
        assert "Hello" in self._collect_text(rt)
        full_xml = etree.tostring(rt._r[0]).decode() if rt._r else ""
        assert 'w:b' in full_xml, f"Expected bold in XML: {full_xml}"

    def test_em_tag_treated_as_italic(self):
        """<em> tag -> same as italic."""
        from utils.richtext_utils import html_to_richtext
        import lxml.etree as etree
        rt = html_to_richtext("<em>Hello</em>")
        assert "Hello" in self._collect_text(rt)
        full_xml = etree.tostring(rt._r[0]).decode() if rt._r else ""
        assert 'w:i' in full_xml, f"Expected italic in XML: {full_xml}"


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
