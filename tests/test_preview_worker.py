import sys
import tempfile
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication
from workers.preview_worker import A250PreviewWorker


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


def test_each_worker_gets_a_unique_temp_dir(qapp):
    """Each worker must render into its own private temp dir so a stale Word
    lock from a prior session (on a fixed path like %TEMP%/a250_preview/
    preview.docx) can never block this session's renders (Errno 13)."""
    w1 = A250PreviewWorker(render_fn=lambda r, o: None, converter=lambda d, p: None)
    w2 = A250PreviewWorker(render_fn=lambda r, o: None, converter=lambda d, p: None)
    assert w1._tmp_dir != w2._tmp_dir
    assert w1._tmp_dir.exists() and w2._tmp_dir.exists()
    # Lives under the OS temp root, not the project tree.
    assert str(w1._tmp_dir).startswith(tempfile.gettempdir())


def test_shutdown_removes_temp_dir(qapp):
    """shutdown() must delete the worker's private temp dir (with its rendered
    docx/pdf) so preview files don't accumulate across sessions."""
    w = A250PreviewWorker(render_fn=lambda r, o: None, converter=lambda d, p: None)
    tmp = w._tmp_dir
    (tmp / "preview.docx").write_bytes(b"x")   # simulate a rendered artifact
    assert tmp.exists()
    w.shutdown()
    assert not tmp.exists()


def test_coalesces_to_latest_request(qapp):
    """While a render is in flight, only the latest queued request runs next.

    Drives the render loop directly: the fake render_fn stashes two more
    requests into `_pending` on its first call (simulating rapid typing while
    the first render is in flight), and we assert the loop drains iteratively
    down to only the latest — without recursing back into `_run`.
    """
    rendered = []
    first_call = True

    def fake_render(raw, out_path):
        nonlocal first_call
        rendered.append(raw["project_title"])
        if first_call:
            first_call = False
            # Simulate two more requests queued while this render was busy;
            # only the latest ("C") should survive to be rendered next.
            w._pending = {"project_title": "B"}
            w._pending = {"project_title": "C"}

    def fake_convert(docx_path, pdf_path):
        # simulate work; no Word
        return None

    w = A250PreviewWorker(render_fn=fake_render, converter=fake_convert)
    w._run({"project_title": "A"})

    assert rendered == ["A", "C"]      # A ran, then only the latest pending (C)
    assert w._pending is None          # queue fully drained
    assert w._busy is False            # loop resets busy in the finally block


def test_request_render_queues_while_busy(qapp):
    """request_render stashes into _pending (latest wins) instead of running
    a nested render when the worker is already busy."""
    rendered = []

    def fake_render(raw, out_path):
        rendered.append(raw["project_title"])

    def fake_convert(docx_path, pdf_path):
        return None

    w = A250PreviewWorker(render_fn=fake_render, converter=fake_convert)
    w._busy = True                     # pretend a render is in flight
    w.request_render({"project_title": "A"})
    w.request_render({"project_title": "B"})
    w.request_render({"project_title": "C"})
    assert w._pending == {"project_title": "C"}   # only latest kept
    assert rendered == []                          # nothing ran while busy


def test_failed_render_resets_busy_and_drains_pending(qapp):
    """A raising render_fn should still emit `failed`, reset `_busy`, and go
    on to drain any request that got queued in the meantime (real-Word path
    is a no-op here since `_word` is never set when render_fn is injected)."""
    failures = []
    rendered = []
    first_call = True

    def flaky_render(raw, out_path):
        nonlocal first_call
        if first_call:
            first_call = False
            w._pending = {"project_title": "retry"}
            raise RuntimeError("boom")
        rendered.append(raw["project_title"])

    def fake_convert(docx_path, pdf_path):
        return None

    w = A250PreviewWorker(render_fn=flaky_render, converter=fake_convert)
    w.failed.connect(lambda msg: failures.append(msg))
    w._run({"project_title": "first"})

    assert failures == ["boom"]
    assert rendered == ["retry"]       # drained the queued request after the failure
    assert w._pending is None
    assert w._busy is False
    assert w._word is None             # never set on the injected-converter path
