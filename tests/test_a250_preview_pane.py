import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtPdf import QPdfDocument
from utils.a250_preview_pane import A250PreviewPane


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


def test_pane_exposes_interface(qapp):
    pane = A250PreviewPane()
    for m in ("show_pdf", "set_updating", "show_unavailable", "show_rendering", "show_error"):
        assert hasattr(pane, m)
    # State toggles must not raise.
    pane.set_updating(True)
    pane.set_updating(False)
    pane.show_rendering()
    assert "Rendering" in pane._message.text()
    pane.show_unavailable("MS Word required for preview")
    assert pane._message.text() == "MS Word required for preview"


def test_error_before_any_pdf_shows_full_message(qapp):
    pane = A250PreviewPane()
    pane.show_error("boom")
    assert "boom" in pane._message.text()
    assert not pane._updating.isVisible()


def test_error_after_pdf_shows_banner(qapp):
    pane = A250PreviewPane()
    pane._has_pdf = True                      # simulate a prior successful render
    pane.show_error("boom")
    assert "boom" in pane._error.text()
    assert not pane._message.isVisible()      # PDF stays; banner over it


def test_has_pdf_not_set_until_document_ready(qapp):
    pane = A250PreviewPane()
    pane.show_pdf("whatever.pdf")
    # load() is async; must not optimistically flag success before Ready fires.
    assert pane._has_pdf is False


def test_failed_load_keeps_has_pdf_false_and_shows_full_message(qapp):
    pane = A250PreviewPane()
    pane.show_pdf("whatever.pdf")
    pane._on_status(QPdfDocument.Status.Error)
    assert pane._has_pdf is False

    pane.show_error("render failed")
    assert "render failed" in pane._message.text()
    assert not pane._error.isVisible()


def test_successful_load_sets_has_pdf_and_later_error_shows_banner(qapp):
    pane = A250PreviewPane()
    pane.show_pdf("whatever.pdf")
    pane._on_status(QPdfDocument.Status.Ready)
    assert pane._has_pdf is True

    pane.show_error("stale")
    assert not pane._error.isHidden()
    assert "stale" not in pane._message.text()
