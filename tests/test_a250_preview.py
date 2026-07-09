import sys
import threading
import pytest
from unittest.mock import Mock
from PyQt6.QtCore import Qt, QMetaObject, QThread
from PyQt6.QtWidgets import QApplication, QLineEdit, QComboBox, QTextEdit
from utils.web_editor import WebRichTextEditor
from workers.preview_worker import A250PreviewWorker


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


def test_collect_raw_never_syncs_on_preview(qapp):
    """Preview (use_cache=True) must NOT call get_html_sync — the editor page may
    not be loaded yet, which throws 'getContent is not defined' in JS."""
    from app import FolderSetupApp
    window = FolderSetupApp()
    ed = Mock(spec=WebRichTextEditor)
    ed.cached_html = Mock(return_value="")  # nothing typed / page not ready
    ed.get_html_sync = Mock(side_effect=AssertionError("get_html_sync must not run during preview"))
    raw = window._collect_a250_raw({"detailed_scope": ed}, use_cache=True)
    assert raw["detailed_scope"] == ""
    ed.get_html_sync.assert_not_called()


def test_render_a250_docx_matches_generation_path(tmp_path):
    """Preview and Generate share render_a250_docx — same raw yields same doc text."""
    from app import render_a250_docx
    import zipfile
    raw = {"project_title": "Shared Path", "fee": "1200"}
    a = tmp_path / "a.docx"
    b = tmp_path / "b.docx"
    render_a250_docx(raw, a)
    render_a250_docx(raw, b)
    xa = zipfile.ZipFile(a).read("word/document.xml").decode("utf-8")
    xb = zipfile.ZipFile(b).read("word/document.xml").decode("utf-8")
    assert "Shared Path" in xa
    assert "1,200.00" in xa
    assert xa == xb


def test_shutdown_marshaled_runs_on_worker_thread(qapp):
    """Cleanup must invoke shutdown() ON the worker thread (BlockingQueuedConnection),
    not directly from the GUI thread — a direct call would hit the Word COM object
    from the wrong apartment and raise (swallowed by shutdown's bare except),
    leaving WINWORD.EXE running. This mirrors app.py's _cleanup wiring."""
    worker = A250PreviewWorker(render_fn=lambda raw, path: None, converter=lambda a, b: None)
    thread = QThread()
    worker.moveToThread(thread)
    thread.start()

    # Fake Word object recording which thread .Quit() actually executed on.
    quit_thread_ident = {}
    fake_word = Mock()
    fake_word.Quit = Mock(side_effect=lambda: quit_thread_ident.setdefault("id", threading.get_ident()))
    worker._word = fake_word

    main_thread_ident = threading.get_ident()
    try:
        QMetaObject.invokeMethod(worker, "shutdown", Qt.ConnectionType.BlockingQueuedConnection)
        assert quit_thread_ident.get("id") is not None, "shutdown() never ran"
        assert quit_thread_ident["id"] != main_thread_ident, (
            "shutdown() ran on the GUI thread, not the worker thread"
        )
        assert worker._word is None  # shutdown cleared it after Quit()
    finally:
        thread.quit()
        thread.wait(5000)
