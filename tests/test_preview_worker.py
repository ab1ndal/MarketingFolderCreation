import sys
import pytest
from PyQt6.QtWidgets import QApplication
from workers.preview_worker import A250PreviewWorker


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


def test_coalesces_to_latest_request(qapp):
    """While a render is in flight, only the latest queued request runs next."""
    rendered = []

    def fake_render(raw, out_path):
        rendered.append(raw["project_title"])

    def fake_convert(docx_path, pdf_path):
        # simulate work; no Word
        return None

    w = A250PreviewWorker(render_fn=fake_render, converter=fake_convert)
    w._busy = True                     # pretend a render is in flight
    w.request_render({"project_title": "A"})
    w.request_render({"project_title": "B"})
    w.request_render({"project_title": "C"})
    assert w._pending == {"project_title": "C"}   # only latest kept
    assert rendered == []                          # nothing ran while busy

    w._busy = False
    w._drain_pending()                             # simulate finish → run pending
    assert rendered == ["C"]                       # only the latest was rendered
    assert w._pending is None
