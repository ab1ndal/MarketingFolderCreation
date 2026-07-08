import sys
import pytest
from unittest.mock import Mock
from PyQt6.QtWidgets import QApplication, QLineEdit, QComboBox, QTextEdit, QTextBrowser
from utils.web_editor import WebRichTextEditor


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _vars(overrides=None):
    """Minimal a250_vars with mocked widgets (mirrors test_a250_generation)."""
    overrides = overrides or {}
    line = ["project_title", "client", "client_name", "client_title",
            "client_license", "fee", "save_location", "file_name", "a250_creator",
            "project_address", "nya_project_code", "client_project_code",
            "client_phone", "client_mobile", "client_email", "client_office_no",
            "client_invoice_email", "request_date", "received_date"]
    combo = ["principal_name", "project_manager", "fee_type"]
    multi = ["client_address", "invoice_to"]
    rich = ["project_description", "detailed_scope"]
    v = {}
    for f in line:
        m = Mock(spec=QLineEdit); m.text = Mock(return_value=overrides.get(f, "")); v[f] = m
    for f in combo:
        m = Mock(spec=QComboBox); m.currentText = Mock(return_value=overrides.get(f, "")); v[f] = m
    for f in multi:
        m = Mock(spec=QTextEdit); m.toPlainText = Mock(return_value=overrides.get(f, "")); v[f] = m
    for f in rich:
        m = Mock(spec=WebRichTextEditor)
        m.cached_html = Mock(return_value=overrides.get(f, ""))
        m.get_html_sync = Mock(return_value=overrides.get(f, ""))
        v[f] = m
    return v


def test_preview_shows_composites_and_formatted_fee(qapp):
    from app import FolderSetupApp
    window = FolderSetupApp()
    a250_vars = _vars({
        "client_name": "Jane Doe", "client_title": "Director",
        "client_license": "PE", "client": "Acme Corp", "fee": "5000",
    })
    preview = QTextBrowser()
    window._refresh_preview(a250_vars, preview)
    text = preview.toPlainText()
    assert "requested_by" in text
    assert "client_signed" in text
    assert "5,000.00" in text          # formatted fee visible
    assert "Jane Doe" in text          # composite resolved and shown


def test_preview_renders_rich_text_formatting(qapp):
    from app import FolderSetupApp
    window = FolderSetupApp()
    a250_vars = _vars({"detailed_scope": "<p><strong>Bold scope</strong></p>"})
    preview = QTextBrowser()
    window._refresh_preview(a250_vars, preview)
    # QTextBrowser converts <strong> to bold; the text content survives
    assert "Bold scope" in preview.toPlainText()


def test_preview_never_raises_on_bad_widget(qapp):
    from app import FolderSetupApp
    window = FolderSetupApp()
    preview = QTextBrowser()
    window._refresh_preview({}, preview)  # empty -> still renders section headers
    assert "Derived" in preview.toPlainText()
