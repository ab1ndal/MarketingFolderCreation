import sys
import pytest
from PyQt6.QtWidgets import QApplication
from utils.web_editor import WebRichTextEditor


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_bridge_caches_html_and_fires_callback(qapp):
    ed = WebRichTextEditor(height=100)
    fired = []
    ed.set_change_callback(lambda: fired.append(True))
    # Simulate the JS bridge pushing a change:
    ed._bridge.onQuillChanged("<p>hello</p>")
    assert ed.cached_html() == "<p>hello</p>"
    assert fired == [True]


def test_cached_html_empty_before_any_change(qapp):
    ed = WebRichTextEditor(height=100)
    assert ed.cached_html() == ""
