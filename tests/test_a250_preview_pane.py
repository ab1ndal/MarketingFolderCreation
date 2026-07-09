import sys
import pytest
from PyQt6.QtWidgets import QApplication
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
