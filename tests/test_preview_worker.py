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


def test_transient_failure_retries_and_succeeds(qapp):
    """A single failure (e.g. a Word instance that just died) must NOT surface
    to the user: the worker discards the instance and retries once with a
    rotated filename slot, and only that retry's result is emitted."""
    failures, finished = [], []
    docx_paths = []
    calls = {"n": 0}

    def rec_render(raw, out_path):
        docx_paths.append(out_path.name)

    def flaky_convert(docx_path, pdf_path):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("interface is unknown")   # first attempt dies

    w = A250PreviewWorker(render_fn=rec_render, converter=flaky_convert)
    w.failed.connect(lambda m: failures.append(m))
    w.finished.connect(lambda p: finished.append(p))
    w._run({"project_title": "x"})

    assert failures == []                       # user never sees the transient error
    assert len(finished) == 1                   # retry succeeded and emitted
    assert docx_paths[0] != docx_paths[1]       # retry used a different slot
    assert w._busy is False


def test_both_attempts_fail_reports_once(qapp):
    """If both attempts fail, exactly one `failed` is emitted with the last
    error, and the loop still resets `_busy` and drains any pending request."""
    failures = []
    convert_calls = {"n": 0}

    def rec_render(raw, out_path):
        pass

    def always_fail(docx_path, pdf_path):
        convert_calls["n"] += 1
        raise RuntimeError("boom")

    w = A250PreviewWorker(render_fn=rec_render, converter=always_fail)
    w.failed.connect(lambda m: failures.append(m))
    w._run({"project_title": "x"})

    assert failures == ["boom"]                 # one report, not per-attempt
    assert convert_calls["n"] == 2              # tried twice before giving up
    assert w._pending is None
    assert w._busy is False


def test_consecutive_renders_use_different_pdf_slots(qapp):
    """Successive successful renders must emit different PDF paths so a new
    render never overwrites the file the on-screen QPdfView still holds open."""
    finished = []
    w = A250PreviewWorker(render_fn=lambda r, o: None, converter=lambda d, p: None)
    w.finished.connect(lambda p: finished.append(p))
    w._run({"project_title": "a"})
    w._run({"project_title": "b"})
    assert finished[0] != finished[1]
