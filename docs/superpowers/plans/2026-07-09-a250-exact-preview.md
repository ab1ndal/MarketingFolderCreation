# A250 Exact Document Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the A250 dialog's form-style preview with a live view of the exact rendered document — the real generated `.docx` converted to PDF by Word and shown in a `QPdfView`.

**Architecture:** A shared `render_a250_docx(raw, out_path)` builds the real docx (used by both preview and the Generate button). A background worker (`A250PreviewWorker`, `QObject` moved to a `QThread`) renders the docx and converts it to PDF via Word COM (`win32com`), coalescing rapid requests. The GUI shows the PDF in an `A250PreviewPane` (`QPdfView`), refreshed debounced 1500ms after the user stops typing.

**Tech Stack:** PyQt6 (`QtCore`, `QtPdf`, `QtPdfWidgets`), `docxtpl`, `pywin32` (`win32com.client`, `pythoncom`), Microsoft Word (COM automation), pytest + pytest-qt.

## Global Constraints

- Platform: Windows only; Microsoft Word must be installed for preview (Office16 confirmed on target).
- Word COM must use dynamic `win32com.client.Dispatch` — never `EnsureDispatch`/makepy (gen_py cache breaks the PyInstaller-frozen exe).
- Word instance always configured `Visible=False`, `DisplayAlerts=0`.
- Raw field collection happens only on the main GUI thread; the raw dict (plain strings) crosses to the worker thread via a queued signal.
- `docxtpl` render + Word COM run only on the worker thread; COM initialized on that thread (`pythoncom.CoInitialize`).
- `build_a250_context` (in `utils/a250_context.py`) is unchanged.
- Temp files live under the OS temp dir in a dedicated subfolder, never the project tree.
- Rich-text fields are exactly: `project_description`, `detailed_scope`.
- Resource paths use the existing `_resource_path` helper (handles `sys._MEIPASS`).

---

### Task 1: Word→PDF conversion utility (`utils/docx_pdf.py`)

**Files:**
- Create: `utils/docx_pdf.py`
- Test: `tests/test_docx_pdf.py`

**Interfaces:**
- Produces:
  - `word_available() -> bool` — True if a Word COM instance can be created (result cached after first call).
  - `create_word()` — returns a new hidden Word `Application` COM object (`Visible=False`, `DisplayAlerts=0`); raises on failure.
  - `docx_to_pdf(word_app, docx_path: Path, pdf_path: Path) -> None` — converts using the supplied Word instance via `ExportAsFixedFormat` (PDF, format code 17). Overwrites `pdf_path`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_docx_pdf.py
import pytest
from utils.docx_pdf import word_available


def test_word_available_returns_bool():
    result = word_available()
    assert isinstance(result, bool)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_docx_pdf.py::test_word_available_returns_bool -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'utils.docx_pdf'`

- [ ] **Step 3: Write minimal implementation**

```python
# utils/docx_pdf.py
"""Convert docx to PDF via Microsoft Word COM automation.

Windows + Word only. Uses dynamic Dispatch (never EnsureDispatch) so no
gen_py makepy cache is required — that cache breaks a PyInstaller-frozen exe.
"""
from __future__ import annotations

from pathlib import Path

# wdExportFormatPDF
_WD_EXPORT_FORMAT_PDF = 17

_word_available_cache: bool | None = None


def word_available() -> bool:
    """Return True if Word can be launched via COM. Cached after first probe."""
    global _word_available_cache
    if _word_available_cache is not None:
        return _word_available_cache
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        try:
            app = win32com.client.Dispatch("Word.Application")
            app.Quit()
            _word_available_cache = True
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        _word_available_cache = False
    return _word_available_cache


def create_word():
    """Create and return a hidden Word Application COM object.

    Caller is responsible for CoInitialize on its thread before calling this
    and for calling app.Quit() when done.
    """
    import win32com.client

    app = win32com.client.Dispatch("Word.Application")
    app.Visible = False
    app.DisplayAlerts = 0  # wdAlertsNone
    return app


def docx_to_pdf(word_app, docx_path: Path, pdf_path: Path) -> None:
    """Convert docx_path to pdf_path using an already-open Word instance."""
    doc = word_app.Documents.Open(
        str(Path(docx_path).resolve()),
        ReadOnly=True,
        AddToRecentFiles=False,
    )
    try:
        doc.ExportAsFixedFormat(
            OutputFileName=str(Path(pdf_path).resolve()),
            ExportFormat=_WD_EXPORT_FORMAT_PDF,
        )
    finally:
        doc.Close(False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_docx_pdf.py::test_word_available_returns_bool -v`
Expected: PASS

- [ ] **Step 5: Add a Word-gated conversion test**

```python
# append to tests/test_docx_pdf.py
from pathlib import Path
from utils.docx_pdf import word_available, create_word, docx_to_pdf


@pytest.mark.skipif(not word_available(), reason="MS Word not available")
def test_docx_to_pdf_produces_pdf(tmp_path):
    import pythoncom
    from docxtpl import DocxTemplate
    from app import _resource_path

    # Render the real A250 template with a minimal context to a temp docx.
    docx_path = tmp_path / "in.docx"
    doc = DocxTemplate(_resource_path("templates/A250.docx"))
    doc.render({})
    doc.save(docx_path)

    pdf_path = tmp_path / "out.pdf"
    pythoncom.CoInitialize()
    try:
        word = create_word()
        try:
            docx_to_pdf(word, docx_path, pdf_path)
        finally:
            word.Quit()
    finally:
        pythoncom.CoUninitialize()

    assert pdf_path.exists()
    assert pdf_path.read_bytes()[:4] == b"%PDF"
```

- [ ] **Step 6: Run the full test file**

Run: `.venv/Scripts/python.exe -m pytest tests/test_docx_pdf.py -v`
Expected: `test_word_available_returns_bool` PASS; `test_docx_to_pdf_produces_pdf` PASS (on a Word machine) or SKIPPED (no Word).

- [ ] **Step 7: Commit**

```bash
git add utils/docx_pdf.py tests/test_docx_pdf.py
git commit -m "feat(a250): docx→PDF conversion via Word COM"
```

---

### Task 2: Shared `render_a250_docx` refactor (app.py)

Extract the docx-building logic from `_generate_a250` into a module-level function so preview and generation share one render path and cannot drift.

**Files:**
- Modify: `app.py` — add `render_a250_docx`; rewire `_generate_a250` (currently `app.py:637-660`).
- Test: `tests/test_a250_generation.py` (add one test).

**Interfaces:**
- Consumes: `build_a250_context` (existing), `html_to_richtext` (existing), `DocxTemplate` (existing), `_resource_path` (existing).
- Produces: module-level `render_a250_docx(raw: dict, out_path: Path) -> None` — builds context, converts `project_description`/`detailed_scope` HTML to `RichText`, renders `templates/A250.docx`, saves to `out_path`. Does NOT resolve filename/save-location or open Explorer (that stays in `_generate_a250`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_a250_generation.py — add
def test_render_a250_docx_substitutes_fields(tmp_path):
    from app import render_a250_docx
    from docxtpl import DocxTemplate
    out = tmp_path / "out.docx"
    render_a250_docx(
        {"project_title": "Acme Tower", "fee": "5000", "client": "Acme Corp"},
        out,
    )
    assert out.exists()
    # Reopen and confirm the substituted text is present in the document.
    import zipfile
    xml = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
    assert "Acme Tower" in xml
    assert "5,000.00" in xml   # fee formatted by build_a250_context
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_a250_generation.py::test_render_a250_docx_substitutes_fields -v`
Expected: FAIL with `ImportError: cannot import name 'render_a250_docx'`

- [ ] **Step 3: Add `render_a250_docx` at module level in app.py**

Add after the `_resource_path` helper (near `app.py:35-41`):

```python
def render_a250_docx(raw: dict, out_path) -> None:
    """Render the real A250 docx from raw field values into out_path.

    Shared by the live preview and the Generate button so the preview shows
    exactly what generation produces. Does not resolve output filename or
    save location — the caller handles that.
    """
    from pathlib import Path

    data = build_a250_context(raw)
    for key in ("project_description", "detailed_scope"):
        data[key] = html_to_richtext(raw.get(key, ""))
    template_path = _resource_path("templates/A250.docx")
    doc = DocxTemplate(template_path)
    doc.render(data)
    doc.save(Path(out_path))
```

- [ ] **Step 4: Rewire `_generate_a250` to use it**

Replace the body of `_generate_a250` (`app.py:637-660`) that builds context/RichText/renders with a call to `render_a250_docx`, keeping filename/save-location/Explorer logic:

```python
    def _generate_a250(self, a250_vars: dict):
        try:
            raw = self._collect_a250_raw(a250_vars)  # use_cache=False (sync Quill pull)
            file_stem = raw.get("file_name") or f"A250_{raw.get('project_title', 'output')}"
            file_name = f"{file_stem}.docx"
            save_loc = raw.get("save_location", "").strip()
            output_path = (Path(save_loc) / file_name) if save_loc else (Path.cwd() / file_name)
            render_a250_docx(raw, output_path)
            subprocess.Popen(f'explorer /select,"{output_path}"', shell=True)
            self.write_log(f"A250 generated: {output_path}", "success")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_a250_generation.py -v`
Expected: PASS (new test + existing generation tests).

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_a250_generation.py
git commit -m "refactor(a250): extract shared render_a250_docx"
```

---

### Task 3: Preview worker (`workers/preview_worker.py`)

**Files:**
- Create: `workers/preview_worker.py`
- Modify: `workers/__init__.py` (export `A250PreviewWorker`)
- Test: `tests/test_preview_worker.py`

**Interfaces:**
- Consumes: `render_a250_docx` (Task 2), `utils.docx_pdf.create_word`/`docx_to_pdf` (Task 1).
- Produces: `A250PreviewWorker(QObject)`
  - Signals: `finished(str)` (pdf path), `failed(str)` (message).
  - Slot `setup()` — connect to `QThread.started`; runs `pythoncom.CoInitialize()` (Word created lazily on first render).
  - Slot `request_render(raw: dict)` — coalescing render entry point (runs in worker thread).
  - Slot `shutdown()` — quit Word, `CoUninitialize`, delete temp files.
  - Constructor arg `render_fn=render_a250_docx`, `converter=None` — injectable for tests (converter defaults to real Word path).

- [ ] **Step 1: Write the failing test (coalescing, no Word)**

```python
# tests/test_preview_worker.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_preview_worker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'workers.preview_worker'`

- [ ] **Step 3: Write the worker**

```python
# workers/preview_worker.py
"""Background worker that renders the A250 docx and converts it to PDF.

Lives on its own QThread (moveToThread pattern). COM is initialized on this
thread; a single hidden Word instance is reused across renders. Rapid requests
coalesce to the latest input.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from utils import docx_pdf

# NOTE: render_a250_docx lives in app.py, which imports this module — importing
# it at module top would create a cycle. It is resolved lazily in _run().


class A250PreviewWorker(QObject):
    finished = pyqtSignal(str)   # pdf path
    failed = pyqtSignal(str)     # error message

    def __init__(self, render_fn=None, converter=None, parent=None):
        super().__init__(parent)
        # render_fn defaults to app.render_a250_docx, resolved lazily to avoid
        # an import cycle. Tests inject a fake render_fn directly.
        self._render_fn = render_fn
        # converter(docx_path, pdf_path) -> None; None means use the real Word path.
        self._converter = converter
        self._word = None
        self._busy = False
        self._pending = None            # latest raw dict awaiting render, or None
        self._tmp_dir = Path(tempfile.gettempdir()) / "a250_preview"
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        self._toggle = False            # ping-pong between two pdf paths

    @pyqtSlot()
    def setup(self):
        """Runs in the worker thread (connected to QThread.started)."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

    @pyqtSlot(dict)
    def request_render(self, raw: dict):
        if self._busy:
            self._pending = raw          # keep only the latest
            return
        self._run(raw)

    def _drain_pending(self):
        if self._pending is not None and not self._busy:
            raw, self._pending = self._pending, None
            self._run(raw)

    def _run(self, raw: dict):
        self._busy = True
        try:
            if self._render_fn is None:
                from app import render_a250_docx  # lazy — breaks import cycle
                self._render_fn = render_a250_docx
            docx_path = self._tmp_dir / "preview.docx"
            self._toggle = not self._toggle
            pdf_path = self._tmp_dir / ("preview_a.pdf" if self._toggle else "preview_b.pdf")
            self._render_fn(raw, docx_path)
            self._convert(docx_path, pdf_path)
            self.finished.emit(str(pdf_path))
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            self._busy = False
            self._drain_pending()

    def _convert(self, docx_path: Path, pdf_path: Path):
        if self._converter is not None:
            self._converter(docx_path, pdf_path)
            return
        if self._word is None:
            self._word = docx_pdf.create_word()
        docx_pdf.docx_to_pdf(self._word, docx_path, pdf_path)

    @pyqtSlot()
    def shutdown(self):
        if self._word is not None:
            try:
                self._word.Quit()
            except Exception:
                pass
            self._word = None
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass
        for p in self._tmp_dir.glob("preview*.*"):
            try:
                p.unlink()
            except Exception:
                pass
```

- [ ] **Step 4: Export from `workers/__init__.py`**

```python
from workers.workflow_worker import WorkflowWorker
from workers.preview_worker import A250PreviewWorker

__all__ = ["WorkflowWorker", "A250PreviewWorker"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_preview_worker.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add workers/preview_worker.py workers/__init__.py tests/test_preview_worker.py
git commit -m "feat(a250): preview worker with Word COM + request coalescing"
```

---

### Task 4: Preview pane widget (`utils/a250_preview_pane.py`)

**Files:**
- Create: `utils/a250_preview_pane.py`
- Test: `tests/test_a250_preview_pane.py`

**Interfaces:**
- Produces: `A250PreviewPane(QWidget)`
  - `show_pdf(path: str) -> None` — load the PDF into the `QPdfView`, preserving the current scroll position across the reload; clears any message/error overlay.
  - `set_updating(on: bool) -> None` — show/hide the "updating…" badge.
  - `show_unavailable(msg: str) -> None` — centered full-pane message; hide the PDF view (Word missing).
  - `show_rendering() -> None` — centered "Rendering preview…" message shown before the first PDF exists (covers Word cold-start).
  - `show_error(msg: str) -> None` — surface a render failure. If a prior PDF exists, show a bottom banner over it (so the user knows the shown doc is stale); if none exists yet, show it as a full-pane message. Always clears "updating…".

UX rationale (from review): first render has a distinct rendering state (no blank-white stare), scroll survives the 1.5s refresh reloads, and failures are visible in the pane rather than only in the log.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_a250_preview_pane.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_a250_preview_pane.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'utils.a250_preview_pane'`

- [ ] **Step 3: Write the widget**

```python
# utils/a250_preview_pane.py
"""PDF preview pane for the A250 dialog — shows the exact rendered document.

States (StackAll overlay):
  - _view    : the QPdfView (base layer)
  - _message : full-pane centered text (rendering / Word-missing / first-error)
  - _updating: top-right opaque badge shown during a refresh
  - _error   : bottom opaque banner shown over a stale PDF after a failure
Scroll position is preserved across reloads so the 1.5s refresh doesn't yank
the user back to page 1 while they read Exhibit A / Terms.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QStackedLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView


class A250PreviewPane(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._has_pdf = False
        self._pending_scroll = 0

        self._layout = QStackedLayout(self)
        self._layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self._doc = QPdfDocument(self)
        self._view = QPdfView(self)
        self._view.setDocument(self._doc)
        self._view.setPageMode(QPdfView.PageMode.MultiPage)
        self._view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self._layout.addWidget(self._view)
        # Restore scroll once the (async) load finishes.
        self._doc.statusChanged.connect(self._on_status)

        self._message = QLabel("", self)
        self._message.setWordWrap(True)
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message.setStyleSheet("color:#555; background:#f4f4f4; font-size:14px; padding:24px;")
        self._message.hide()
        self._layout.addWidget(self._message)

        # Opaque pill so it reads over any page content (review: contrast fix).
        self._updating = QLabel("updating…", self)
        self._updating.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self._updating.setStyleSheet(
            "color:#ffffff; background:#2d7d46; font-size:12px;"
            "font-weight:bold; padding:4px 10px; border-radius:3px;"
        )
        self._updating.setFixedHeight(24)
        self._updating.hide()
        self._layout.addWidget(self._updating)

        self._error = QLabel("", self)
        self._error.setWordWrap(True)
        self._error.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self._error.setStyleSheet(
            "color:#ffffff; background:#c0392b; font-size:12px; padding:8px 12px;"
        )
        self._error.hide()
        self._layout.addWidget(self._error)

        self._layout.setCurrentWidget(self._view)

    def _on_status(self, status) -> None:
        if status == QPdfDocument.Status.Ready:
            self._view.verticalScrollBar().setValue(self._pending_scroll)

    def show_pdf(self, path: str) -> None:
        self._pending_scroll = self._view.verticalScrollBar().value()
        self._message.hide()
        self._error.hide()
        self._view.show()
        self._doc.load(path)
        self._has_pdf = True

    def set_updating(self, on: bool) -> None:
        self._updating.setVisible(on)
        if on:
            self._updating.raise_()

    def show_rendering(self) -> None:
        self._show_message("Rendering preview…")

    def show_unavailable(self, msg: str) -> None:
        self._show_message(msg)

    def show_error(self, msg: str) -> None:
        self.set_updating(False)
        if self._has_pdf:
            # Keep the (stale) PDF visible; banner tells the user it's outdated.
            self._error.setText(f"{msg}\nShowing last successful render.")
            self._error.show()
            self._error.raise_()
        else:
            self._show_message(f"Preview failed:\n{msg}")

    def _show_message(self, text: str) -> None:
        self._message.setText(text)
        self._error.hide()
        self._updating.hide()
        self._view.hide()
        self._message.show()
        self._message.raise_()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_a250_preview_pane.py -v`
Expected: PASS (all three tests)

- [ ] **Step 5: Commit**

```bash
git add utils/a250_preview_pane.py tests/test_a250_preview_pane.py
git commit -m "feat(a250): QPdfView preview pane widget"
```

---

### Task 5: Wire preview into the A250 dialog (app.py)

Replace the `QTextBrowser` preview and its HTML builder with the PDF pane + worker thread.

**Files:**
- Modify: `app.py` — imports; `_open_a250_form` (`app.py:465-555`); delete `_render_preview_html` (`app.py:570-613`); adjust `_refresh_preview` (`app.py:557-568`).
- Modify: `tests/test_a250_preview.py` — replace obsolete HTML-table tests.

**Interfaces:**
- Consumes: `A250PreviewPane` (Task 4), `A250PreviewWorker` (Task 3), `word_available` (Task 1).
- Produces: no new public API; `_open_a250_form` now owns a `QThread` + worker and emits a `pyqtSignal(dict)` to `worker.request_render`.

- [ ] **Step 1: Update imports at the top of app.py**

Remove `QTextBrowser` from the `QtWidgets` import (`app.py:8-13`). Add:

```python
from PyQt6.QtCore import Qt, pyqtSlot, QEvent, QTimer, QThread, pyqtSignal, QObject
from utils.a250_preview_pane import A250PreviewPane
from workers import A250PreviewWorker
from utils.docx_pdf import word_available
```

- [ ] **Step 2: Replace the preview panel construction in `_open_a250_form`**

Replace the `# ---- Right: live preview ----` block (`app.py:482-490`) with:

```python
        # ---- Right: live document preview (exact rendered PDF) ----
        preview_panel = QWidget()
        pv_layout = QVBoxLayout(preview_panel)
        pv_layout.addWidget(QLabel("Preview — exact document output"))
        preview = A250PreviewPane()
        pv_layout.addWidget(preview)
        splitter.addWidget(preview_panel)
        # 50/50 — the rendered document is now the focus of the dialog (review).
        splitter.setStretchFactor(0, 50)
        splitter.setStretchFactor(1, 50)
```

- [ ] **Step 3: Replace the debounce/refresh wiring in `_open_a250_form`**

Replace the `# ---- Debounced live preview refresh ----` block through the initial-render call (`app.py:524-544`) with:

```python
        # ---- Live preview: worker thread + debounced refresh ----
        self._preview_thread = None
        self._preview_worker = None
        if not word_available():
            preview.show_unavailable("MS Word required for preview")
        else:
            # Signal used to hand a raw dict to the worker thread (queued).
            class _Emitter(QObject):
                request = pyqtSignal(dict)
            emitter = _Emitter(dialog)

            thread = QThread(dialog)
            worker = A250PreviewWorker()
            worker.moveToThread(thread)
            thread.started.connect(worker.setup)
            emitter.request.connect(worker.request_render)      # queued (cross-thread)

            # Watchdog: if neither finished nor failed arrives (Word hung/stalled),
            # surface a timeout instead of an "updating…" badge that spins forever.
            watchdog = QTimer(dialog)
            watchdog.setSingleShot(True)
            watchdog.setInterval(20000)
            watchdog.timeout.connect(
                lambda: preview.show_error("Preview timed out — Word not responding.")
            )

            def _on_finished(p):
                watchdog.stop()
                preview.show_pdf(p)          # hides message/error, preserves scroll
                preview.set_updating(False)

            def _on_failed(m):
                watchdog.stop()
                preview.show_error(m)        # visible in the pane, not just the log
                self.write_log(f"A250 preview failed: {m}", "error")

            worker.finished.connect(_on_finished)
            worker.failed.connect(_on_failed)
            thread.start()
            self._preview_thread = thread
            self._preview_worker = worker

            preview_timer = QTimer(dialog)
            preview_timer.setSingleShot(True)
            preview_timer.setInterval(1500)

            def _fire():
                raw = self._collect_a250_raw(a250_vars, use_cache=True)
                preview.set_updating(True)
                watchdog.start()
                emitter.request.emit(raw)

            preview_timer.timeout.connect(_fire)

            def schedule(*_):
                preview_timer.start()

            for key, widget in a250_vars.items():
                if isinstance(widget, QComboBox):
                    widget.currentTextChanged.connect(schedule)
                elif isinstance(widget, WebRichTextEditor):
                    widget.set_change_callback(schedule)
                elif isinstance(widget, QTextEdit):
                    widget.textChanged.connect(schedule)
                else:
                    widget.textChanged.connect(schedule)

            # Initial render on open: show a rendering state (covers Word cold-start,
            # ~2-3s) so the pane is never a blank white void, then fire.
            preview.show_rendering()
            _fire()

            # Clean up the worker + thread when the dialog closes.
            def _cleanup():
                worker.shutdown()
                thread.quit()
                thread.wait(5000)
            dialog.finished.connect(lambda _=None: _cleanup())
```

Note: the old `schedule`/signal-connect loop (`app.py:530-541`) is now inside the `else` branch above — delete the standalone copy.

- [ ] **Step 4: Simplify `_refresh_preview` and delete `_render_preview_html`**

`_refresh_preview` (`app.py:557-568`) is no longer used by the dialog. Delete both `_refresh_preview` and `_render_preview_html` (`app.py:557-613`). Keep `_collect_a250_raw` unchanged.

- [ ] **Step 5: Replace obsolete tests in `tests/test_a250_preview.py`**

Delete `test_preview_shows_composites_and_formatted_fee`, `test_preview_renders_rich_text_formatting`, and `test_preview_never_raises_on_bad_widget` (they assert on the removed `_render_preview_html`/`QTextBrowser`). Keep `test_collect_raw_never_syncs_on_preview` (still valid). Remove the now-unused `QTextBrowser` import. Add:

```python
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
```

- [ ] **Step 6: Run the A250 test suite**

Run: `.venv/Scripts/python.exe -m pytest tests/test_a250_preview.py tests/test_a250_generation.py tests/test_a250_context.py -v`
Expected: PASS (obsolete tests removed, new tests pass).

- [ ] **Step 7: Manual smoke check**

Run: `.venv/Scripts/python.exe app.py`
- Open Create A250. Confirm the pane shows "Rendering preview…" during Word cold-start, then the rendered A250 PDF (blank template).
- Type a project title, pause ~1.5s → opaque "updating…" badge appears, then the PDF refreshes showing the value in position.
- Scroll to Exhibit A / Terms (page 2–3), edit a field, pause → confirm the pane refreshes **without** jumping back to page 1 (scroll preserved).
- Close Word (or kill `WINWORD.EXE`) mid-session, edit a field → confirm a red error banner appears over the last render (not a silent failure), within ~20s at most.
- Close the dialog → confirm no lingering `WINWORD.EXE` in Task Manager.

- [ ] **Step 8: Commit**

```bash
git add app.py tests/test_a250_preview.py
git commit -m "feat(a250): live exact-document PDF preview in dialog"
```

---

### Task 6: PyInstaller packaging (`ClickFolder_v2.spec`)

**Files:**
- Modify: `ClickFolder_v2.spec`  ← the REAL/current build spec (confirmed by user + git). NOT `app.spec` (that is a stub with `datas=[]`; the prior A250 commit `7dcf259` mistakenly added `PyQt6.QtWebChannel` to `app.spec` instead of here, so this spec is currently missing QtWebChannel too).

**Interfaces:** none (build config only).

- [ ] **Step 1: Add the missing hiddenimports to `ClickFolder_v2.spec`**

The current `hiddenimports` in `ClickFolder_v2.spec` is:
```python
    hiddenimports=[
        'win32com.shell',
        'win32com.shell.shell',
        'win32timezone',
    ],
```
Add `PyQt6.QtWebChannel` (Quill editor bridge — currently missing from the real build), `PyQt6.QtPdf`, `PyQt6.QtPdfWidgets` (new PDF preview), and `pythoncom` (used by docx_pdf/preview worker). Result:
```python
    hiddenimports=[
        'win32com.shell',
        'win32com.shell.shell',
        'win32timezone',
        'pythoncom',
        'PyQt6.QtWebChannel',
        'PyQt6.QtPdf',
        'PyQt6.QtPdfWidgets',
    ],
```
Leave `datas` (templates/A250.docx + assets) and everything else unchanged.

- [ ] **Step 2: Rebuild the frozen app**

Run: `.venv/Scripts/python.exe -m PyInstaller ClickFolder_v2.spec --noconfirm`
Expected: build completes without errors; output at `dist/ClickFolder_v2/ClickFolder_v2.exe`.

- [ ] **Step 3: Smoke-test the frozen build (MANUAL — controller/user)**

Run: `dist/ClickFolder_v2/ClickFolder_v2.exe`
- Open Create A250 → confirm the rich-text editor loads (QtWebChannel bundled) and the PDF preview renders (QtPdf plugin bundled; Word COM works via dynamic Dispatch).
This step needs a live display + Word + interaction — defer to manual verification.

- [ ] **Step 4: Commit**

```bash
git add ClickFolder_v2.spec
git commit -m "build(a250): bundle QtWebChannel + QtPdf + pythoncom in ClickFolder_v2.spec"
```

---

## Self-Review

**Spec coverage:**
- Exact pipeline (docx→PDF via Word) → Task 1 + Task 3. ✓
- Shared `render_a250_docx` (no drift) → Task 2. ✓
- Worker + coalescing + ping-pong temps + cleanup → Task 3. ✓
- `A250PreviewPane` (QPdfView, updating, unavailable, rendering, error, scroll-preserve) → Task 4. ✓
- Dialog wiring: 1500ms debounce, main-thread raw collection, queued signal, word_available gate, close cleanup → Task 5. ✓
- Removed `_render_preview_html`/`QTextBrowser`/composite tables → Task 5. ✓
- Tests (docx render, Word-gated convert, coalescing, pane interface + error states, shared path) → Tasks 1,3,4,5. ✓
- Packaging (QtPdf + pywin32) → Task 6. ✓

**UX review findings folded in (ui-ux-pro-max universal rules):**
- First-render state (`empty-states`): `show_rendering()` shown on open before first PDF → Task 4 + Task 5 Step 3. ✓
- Scroll preservation (`state-preservation`/`content-jumping`): saved/restored across reloads via `statusChanged` → Task 4. ✓
- Error visible in pane (`error-clarity`/`error-recovery`): `show_error()` banner over stale PDF / full message if none → Task 4 + Task 5 `_on_failed`. ✓
- Timeout watchdog (`timeout-feedback`): 20s `QTimer` → `show_error` → Task 5 Step 3. ✓
- Opaque "updating…" badge (`contrast-readability`): solid green pill, white text → Task 4. ✓
- 50/50 split (`visual-hierarchy`) → Task 5 Step 2. ✓

**Placeholder scan:** No TBD/TODO; all code steps show full code; commands have expected output. ✓

**Type consistency:** `render_a250_docx(raw, out_path)`, `A250PreviewWorker(render_fn, converter)` with `request_render(dict)`/`finished(str)`/`failed(str)`/`setup()`/`shutdown()`, `A250PreviewPane.show_pdf/set_updating/show_unavailable/show_rendering/show_error`, `word_available()`/`create_word()`/`docx_to_pdf(word, docx, pdf)` — names consistent across Tasks 1–5. ✓

**Note on import cycle:** `app` imports `A250PreviewWorker` from `workers` (line 28, before `render_a250_docx` is defined), and the worker needs `render_a250_docx` from `app`. A top-level `from app import render_a250_docx` in the worker would therefore fail. Resolved in the Task 3 code: the worker's `render_fn` defaults to `None` and is resolved lazily inside `_run` (`from app import render_a250_docx`), which runs only at render time, long after both modules finish importing. Tests inject a fake `render_fn`, so they never trigger the lazy import.
