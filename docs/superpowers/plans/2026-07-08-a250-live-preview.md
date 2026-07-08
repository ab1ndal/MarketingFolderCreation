# A250 Live Preview Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Overleaf-style live preview pane to the A250 form so users see, as they type, where every value lands and how composites/rich-text are formatted before generating the Word document.

**Architecture:** Split the A250 `QDialog` into a `QSplitter` — existing scrollable form on the left, a read-only `QTextBrowser` preview on the right. A single pure function `build_a250_context()` computes the template context (composites, formatted fee, dates); both the preview and the real docx generation call it, so they cannot drift. A debounced (`QTimer`, 300 ms single-shot) refresh recomputes the preview; plain widgets feed it via change signals and Quill editors push `text-change` events through a `QWebChannel` bridge.

**Tech Stack:** Python 3.10+, PyQt6 (QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel), Quill 1.x (offline, in `assets/`), docxtpl, pytest + pytest-qt.

## Global Constraints

- Windows-only (win32com/robocopy elsewhere; `%#d` date format is Windows-specific) — one line.
- PyQt6 only — no PyQt5/PySide imports.
- The docx template consumes exactly 28 variables; generation output must not change — every existing variable must still be populated.
- Users are non-technical — preview labels must be plain English, no stack traces surfaced.
- Rich-text editors are `WebRichTextEditor` (QWebEngineView + Quill), loaded from `assets/editor.html`.
- Preserve the existing sync pull path (`get_html_sync` / `getContent()`) — generation depends on it.
- Frequent commits: one per task.

---

### Task 1: Pure context builder `build_a250_context`

Extract the composite/derived logic from `_generate_a250` into a pure, testable function. No Qt, no filesystem.

**Files:**
- Create: `utils/a250_context.py`
- Test: `tests/test_a250_context.py`

**Interfaces:**
- Consumes: `utils.formatting.format_number`.
- Produces: `build_a250_context(raw: dict, now: datetime | None = None) -> dict`. `raw` maps every field key to a string; rich-text fields hold their HTML string and are passed through untouched. Returns a NEW dict: all raw keys passed through, plus `requested_by`, `client_signed`, `invoice_to` (composites), `fee` (formatted), and `today`, `today_2`, `current_date` (dates).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_a250_context.py
from datetime import datetime
from docxtpl import RichText  # noqa: F401 (import parity check)
from utils.a250_context import build_a250_context

NOW = datetime(2026, 4, 2)

def test_requested_by_short_single_newline():
    ctx = build_a250_context({
        "client_name": "Jane Doe", "client_license": "PE",
        "client_title": "Director", "client": "Acme Corp",
    }, now=NOW)
    rb = ctx["requested_by"]
    assert "Jane Doe" in rb and "PE" in rb and "Director" in rb and "Acme Corp" in rb
    assert "\n\n" not in rb  # short content -> single newline before title

def test_requested_by_long_double_newline():
    ctx = build_a250_context({
        "client_name": "Jonathan Alexander Smithsonian",
        "client_license": "PE, SE, LEED AP BD+C",
        "client_title": "Senior Vice President of Engineering",
        "client": "Big Corporation LLC",
    }, now=NOW)
    assert "\n\n" in ctx["requested_by"]

def test_invoice_to_defaults_to_requested_by():
    ctx = build_a250_context({
        "client_name": "Jane Doe", "client_license": "PE",
        "client_title": "Director", "client": "Acme Corp",
    }, now=NOW)
    assert ctx["invoice_to"] == ctx["requested_by"]

def test_invoice_to_custom_kept():
    ctx = build_a250_context({"invoice_to": "Custom\nSuite 100"}, now=NOW)
    assert ctx["invoice_to"] == "Custom\nSuite 100"

def test_client_signed_short_uses_comma():
    ctx = build_a250_context({"client_name": "Jane", "client_title": "PE"}, now=NOW)
    assert ctx["client_signed"] == "Jane, PE"

def test_client_signed_long_uses_newline():
    ctx = build_a250_context({
        "client_name": "Jonathan Alexander Smithsonian",
        "client_title": "Senior Vice President of Engineering",
    }, now=NOW)
    assert "\n" in ctx["client_signed"]

def test_fee_formatted():
    ctx = build_a250_context({"fee": "5000"}, now=NOW)
    assert ctx["fee"] == "5,000.00"

def test_dates_present():
    ctx = build_a250_context({}, now=NOW)
    assert ctx["today"] == "April 2, 2026"
    assert ctx["today_2"] == "04/02/2026"
    assert ctx["current_date"] == ctx["today"]

def test_passthrough_and_rich_untouched():
    ctx = build_a250_context({"project_title": "Tower A", "detailed_scope": "<b>x</b>"}, now=NOW)
    assert ctx["project_title"] == "Tower A"
    assert ctx["detailed_scope"] == "<b>x</b>"  # rich HTML left as-is
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_a250_context.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'utils.a250_context'`

- [ ] **Step 3: Write minimal implementation**

```python
# utils/a250_context.py
"""Pure builder for the A250 docx template context.

Shared by both the live preview panel and the real docx generation so the two
cannot drift. No Qt, no filesystem access.
"""
from __future__ import annotations

from datetime import datetime

from utils.formatting import format_number


def build_a250_context(raw: dict, now: datetime | None = None) -> dict:
    """Return the full template context from raw form values.

    `raw` maps each field key to its string value; rich-text fields hold their
    HTML string and are passed through unchanged (the caller converts them to
    docxtpl.RichText for the document, or renders them as HTML in the preview).
    """
    now = now or datetime.now()
    ctx = dict(raw)

    name    = raw.get("client_name", "").strip()
    licence = raw.get("client_license", "").strip()
    title   = raw.get("client_title", "").strip()
    client  = raw.get("client", "").strip()

    # requested_by: single vs double newline before title based on combined length
    licence_sep = ", " if licence else ""
    title_sep = "\n\n" if len(name) + len(licence) + len(title) > 60 else "\n"
    ctx["requested_by"] = f"{name}{licence_sep}{licence}{title_sep}{title}\n{client}"

    # client_signed: comma vs newline before title based on combined length
    title_sep2 = "\n" if len(name) + len(title) > 40 else ", "
    ctx["client_signed"] = f"{name}{title_sep2}{title}"

    # invoice_to: custom text if provided, else same as requested_by
    invoice_custom = raw.get("invoice_to", "").strip()
    ctx["invoice_to"] = invoice_custom if invoice_custom else ctx["requested_by"]

    ctx["fee"] = format_number(f"{raw.get('fee', '')}")

    ctx["today"] = now.strftime("%B %#d, %Y")
    ctx["today_2"] = now.strftime("%m/%d/%Y")
    ctx["current_date"] = ctx["today"]

    return ctx
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_a250_context.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add utils/a250_context.py tests/test_a250_context.py
git commit -m "feat(a250): pure build_a250_context for preview/generate parity"
```

---

### Task 2: Route `_generate_a250` through `build_a250_context`

Refactor generation to gather raw values, build the context via the shared function, then convert rich-text fields to `RichText`. Existing generation tests must stay green.

**Files:**
- Modify: `app.py` — add import; add `_collect_a250_raw`; rewrite `_generate_a250` (currently `app.py:512-564`).
- Test: `tests/test_a250_generation.py` (existing — must still pass, no edits expected).

**Interfaces:**
- Consumes: `build_a250_context` (Task 1).
- Produces: `FolderSetupApp._collect_a250_raw(self, a250_vars: dict, use_cache: bool = False) -> dict` — returns `{key: str}` for every widget (combo→`currentText`, `WebRichTextEditor`→cached or sync HTML, `QTextEdit`→`toPlainText`, else `text`). Reused by preview in Task 4.

- [ ] **Step 1: Confirm existing generation tests pass first (baseline)**

Run: `python -m pytest tests/test_a250_generation.py -v`
Expected: PASS (all currently-passing tests green — this is the regression baseline)

- [ ] **Step 2: Add the import**

In `app.py`, after line 29 (`from utils.formatting import format_number`):

```python
from utils.a250_context import build_a250_context
```

- [ ] **Step 3: Add `_collect_a250_raw` and rewrite `_generate_a250`**

Replace the whole body of `_generate_a250` (`app.py:512-564`) and add the helper directly above it:

```python
    def _collect_a250_raw(self, a250_vars: dict, use_cache: bool = False) -> dict:
        """Gather raw string values from every A250 widget.

        Rich-text fields return HTML. When use_cache is True, rich-text uses the
        last value pushed by the Quill bridge (cheap, no JS round-trip), falling
        back to a synchronous pull if the cache is empty.
        """
        raw = {}
        for key, w in a250_vars.items():
            if isinstance(w, QComboBox):
                raw[key] = w.currentText()
            elif isinstance(w, WebRichTextEditor):
                if use_cache:
                    html = w.cached_html()
                    raw[key] = html if html else w.get_html_sync()
                else:
                    raw[key] = w.get_html_sync()
            elif isinstance(w, QTextEdit):
                raw[key] = w.toPlainText()
            else:
                raw[key] = w.text()
        return raw

    def _generate_a250(self, a250_vars: dict):
        try:
            raw = self._collect_a250_raw(a250_vars)
            data = build_a250_context(raw)

            # Convert rich-text HTML fields to docxtpl RichText for the document
            for key, w in a250_vars.items():
                if isinstance(w, WebRichTextEditor):
                    data[key] = html_to_richtext(raw[key])

            template_path = _resource_path("templates/A250.docx")
            if data.get("file_name"):
                data["file_name"] = f"{data.get('file_name')}.docx"
            else:
                data["file_name"] = f"A250_{raw.get('project_title', 'output')}.docx"
            save_loc = raw.get("save_location", "").strip()
            output_path = (Path(save_loc) / data["file_name"]) if save_loc else (Path.cwd() / data["file_name"])
            doc = DocxTemplate(template_path)
            doc.render(data)
            doc.save(output_path)
            subprocess.Popen(f'explorer /select,"{output_path}"', shell=True)
            self.write_log(f"A250 generated: {output_path}", "success")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
```

Note: the existing test `test_a250_generation.py::test_render_called_with_all_fields` asserts `current_date` is present — `build_a250_context` still sets it, so this stays green. Rich-text mocks in that test expose `get_html_sync` (not `cached_html`); generation uses `use_cache=False`, so it never calls `cached_html` here.

- [ ] **Step 4: Run generation tests to verify still green**

Run: `python -m pytest tests/test_a250_generation.py -v`
Expected: PASS (same set as the baseline in Step 1)

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "refactor(a250): generate via shared build_a250_context + _collect_a250_raw"
```

---

### Task 3: QWebChannel bridge on `WebRichTextEditor`

Add an event-push bridge so Quill `text-change` events reach Python, caching the latest HTML and firing a callback. Keeps the sync pull path intact.

**Files:**
- Modify: `utils/web_editor.py`
- Modify: `assets/editor.html`
- Test: `tests/test_web_editor_bridge.py` (create)

**Interfaces:**
- Produces: `WebRichTextEditor.set_change_callback(self, fn) -> None` and `WebRichTextEditor.cached_html(self) -> str`. The internal `_QuillBridge` has `@pyqtSlot(str) onQuillChanged(html)` that stores HTML and invokes the callback.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_web_editor_bridge.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_web_editor_bridge.py -v`
Expected: FAIL — `AttributeError: 'WebRichTextEditor' object has no attribute '_bridge'` / `set_change_callback`

- [ ] **Step 3: Implement the bridge in `utils/web_editor.py`**

Change the imports block (lines 8-10) to add QObject/pyqtSlot and QWebChannel:

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, QObject, pyqtSlot
```

Add the bridge class above `WebRichTextEditor`:

```python
class _QuillBridge(QObject):
    """Receives Quill text-change pushes from JS via QWebChannel."""

    def __init__(self):
        super().__init__()
        self._html = ""
        self._callback = None

    @pyqtSlot(str)
    def onQuillChanged(self, html: str):
        self._html = html
        if self._callback:
            self._callback()
```

In `WebRichTextEditor.__init__`, register the channel BEFORE loading the page. Replace the load block (current lines 35-40) with:

```python
        self._view = QWebEngineView()
        self._view.setFixedHeight(height)
        layout.addWidget(self._view)

        # Bridge must be registered before the page loads so qt.webChannelTransport
        # is available to the page's JS. Hold Python refs so neither is GC'd.
        self._bridge = _QuillBridge()
        self._channel = QWebChannel()
        self._channel.registerObject("bridge", self._bridge)
        self._view.page().setWebChannel(self._channel)

        editor_html = _resource_path("assets/editor.html")
        self._view.load(QUrl.fromLocalFile(str(editor_html)))
```

Add the two public methods (e.g. after `set_html`):

```python
    def set_change_callback(self, fn) -> None:
        """Register a zero-arg callable invoked on every Quill text-change."""
        self._bridge._callback = fn

    def cached_html(self) -> str:
        """Latest HTML pushed by the Quill bridge ('' before any change)."""
        return self._bridge._html
```

- [ ] **Step 4: Wire the JS side in `assets/editor.html`**

Immediately after `<script src="quill.js"></script>` (line 71) add:

```html
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
```

Inside the existing inline `<script>`, after the `function setContent(...)` definitions (after line 95), add:

```javascript
    // Push Quill changes to Python via QWebChannel (event-push, not polling).
    if (typeof qt !== 'undefined' && qt.webChannelTransport) {
      new QWebChannel(qt.webChannelTransport, function (channel) {
        window.bridge = channel.objects.bridge;
        quill.on('text-change', function () {
          if (window.bridge) window.bridge.onQuillChanged(quill.root.innerHTML);
        });
      });
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_web_editor_bridge.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add utils/web_editor.py assets/editor.html tests/test_web_editor_bridge.py
git commit -m "feat(a250): QWebChannel bridge pushing Quill text-change to Python"
```

---

### Task 4: Split-pane layout + live preview panel

Add the module-level field-group constant, the `QSplitter` layout with a `QTextBrowser` preview, the debounce timer, signal wiring, and the preview HTML renderer.

**Files:**
- Modify: `app.py` — imports; add `A250_FIELD_GROUPS`, `A250_COMPOSITE_KEYS`, `A250_COMPOSITE_NOTES` module constants; rewrite `_open_a250_form` (`app.py:412-510`); add `_refresh_preview` and `_render_preview_html`.
- Test: `tests/test_a250_preview.py` (create)

**Interfaces:**
- Consumes: `_collect_a250_raw` (Task 2), `build_a250_context` (Task 1), `WebRichTextEditor.set_change_callback`/`cached_html` (Task 3).
- Produces: `FolderSetupApp._refresh_preview(self, a250_vars: dict, preview: QTextBrowser) -> None`; `FolderSetupApp._render_preview_html(self, ctx: dict, rich_keys: set[str]) -> str`.

- [ ] **Step 1: Add imports**

In `app.py` widgets import (lines 8-13) add `QSplitter, QTextBrowser`:

```python
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QDialog, QScrollArea, QFormLayout,
    QDialogButtonBox, QGroupBox, QComboBox, QCheckBox, QSplitter, QTextBrowser
)
```

In the QtCore import (line 14) add `QTimer`:

```python
from PyQt6.QtCore import Qt, pyqtSlot, QEvent, QTimer
```

- [ ] **Step 2: Add module-level constants**

Directly above `class FolderSetupApp` (before line 42), add the field groups (moved out of `_open_a250_form`) plus composite metadata:

```python
A250_FIELD_GROUPS = [
    ("Project Info", [
        ("project_title", "Project Title"),
        ("project_address", "Project Address"),
        ("client", "Company Name"),
        ("nya_project_code", "NYA Project Code"),
        ("client_project_code", "Client Project Code"),
    ]),
    ("Client Contact", [
        ("client_name", "Client Name"),
        ("client_title", "Title"),
        ("client_license", "Licenses"),
        ("client_phone", "Phone Number"),
        ("client_mobile", "Mobile Number"),
        ("client_email", "Email Address"),
    ]),
    ("Billing", [
        ("invoice_to", "Invoice To"),
        ("client_office_no", "Office Number"),
        ("client_invoice_email", "Invoice Email"),
        ("client_address", "Client Address"),
    ]),
    ("Scope & Fee", [
        ("request_date", "Request Date"),
        ("received_date", "Received Date"),
        ("project_description", "Project Description"),
        ("detailed_scope", "Detailed Scope"),
        ("fee_type", "Fee Type"),
        ("fee", "Fee"),
    ]),
    ("Additional Info", [
        ("principal_name", "Principal Name"),
        ("project_manager", "Project Manager"),
    ]),
    ("Output", [
        ("save_location", "Save Location"),
        ("file_name", "File Name"),
        ("a250_creator", "Created By"),
    ]),
]

# Derived/composite values shown in their own preview section with a note.
A250_COMPOSITE_KEYS = ["requested_by", "invoice_to", "client_signed", "fee", "today"]
A250_COMPOSITE_NOTES = {
    "requested_by": "auto-built from Name / License / Title / Company",
    "invoice_to": "your custom text, else same as Requested By",
    "client_signed": "auto-built from Name / Title",
    "fee": "formatted with thousands separators and 2 decimals",
    "today": "today's date, inserted automatically",
}
```

- [ ] **Step 3: Rewrite `_open_a250_form` to use the splitter + constants + timer**

Replace `_open_a250_form` (`app.py:412-510`) with:

```python
    def _open_a250_form(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create A250")
        dialog.resize(1150, 820)

        outer_layout = QVBoxLayout(dialog)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        outer_layout.addWidget(splitter)

        # ---- Left: scrollable form ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        scroll.setWidget(container)
        splitter.addWidget(scroll)

        # ---- Right: live preview ----
        preview_panel = QWidget()
        pv_layout = QVBoxLayout(preview_panel)
        pv_layout.addWidget(QLabel("Preview — how your entries map to the document"))
        preview = QTextBrowser()
        pv_layout.addWidget(preview)
        splitter.addWidget(preview_panel)
        splitter.setStretchFactor(0, 55)
        splitter.setStretchFactor(1, 45)

        a250_vars = {}
        COMBO_FIELDS = {
            "principal_name": PRINCIPAL_OPTIONS,
            "project_manager": PROJECT_MANAGER_OPTIONS,
            "fee_type": FEE_TYPE_OPTIONS,
        }
        MULTILINE_FIELDS = {"project_address", "client_address", "invoice_to"}
        RICH_TEXT_FIELDS = {"project_description", "detailed_scope"}

        for section_title, field_pairs in A250_FIELD_GROUPS:
            group_box = QGroupBox(section_title)
            form = QFormLayout(group_box)
            for key, label in field_pairs:
                if key in COMBO_FIELDS:
                    widget = QComboBox()
                    widget.addItems(COMBO_FIELDS[key])
                    form.addRow(label, widget)
                elif key in RICH_TEXT_FIELDS:
                    widget = WebRichTextEditor(height=150)
                    form.addRow(label, widget)
                elif key in MULTILINE_FIELDS:
                    widget = QTextEdit()
                    widget.setFixedHeight(80)
                    form.addRow(label, widget)
                else:
                    widget = QLineEdit()
                    form.addRow(label, widget)
                a250_vars[key] = widget
            container_layout.addWidget(group_box)

        container_layout.addStretch()

        # ---- Debounced live preview refresh ----
        preview_timer = QTimer(dialog)
        preview_timer.setSingleShot(True)
        preview_timer.setInterval(300)
        preview_timer.timeout.connect(lambda: self._refresh_preview(a250_vars, preview))

        def schedule(*_):
            preview_timer.start()  # restart cancels the prior pending fire

        for key, widget in a250_vars.items():
            if isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(schedule)
            elif isinstance(widget, WebRichTextEditor):
                widget.set_change_callback(schedule)
            elif isinstance(widget, QTextEdit):
                widget.textChanged.connect(schedule)
            else:
                widget.textChanged.connect(schedule)

        # Initial render (fields empty)
        self._refresh_preview(a250_vars, preview)

        # ---- Buttons ----
        btn_box = QDialogButtonBox()
        generate_btn = btn_box.addButton("Generate A250", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = btn_box.addButton("Close", QDialogButtonBox.ButtonRole.RejectRole)
        outer_layout.addWidget(btn_box)

        generate_btn.clicked.connect(lambda: self._generate_a250(a250_vars))
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec()
```

- [ ] **Step 4: Add `_refresh_preview` and `_render_preview_html`**

Add these methods directly below `_open_a250_form`:

```python
    def _refresh_preview(self, a250_vars: dict, preview: QTextBrowser) -> None:
        """Recompute the resolved-values preview from current field values."""
        try:
            raw = self._collect_a250_raw(a250_vars, use_cache=True)
            ctx = build_a250_context(raw)
            rich_keys = {k for k, w in a250_vars.items() if isinstance(w, WebRichTextEditor)}
            preview.setHtml(self._render_preview_html(ctx, rich_keys))
        except Exception as e:  # never let the preview crash the form
            preview.setHtml(
                f"<p style='color:#c0392b'>Preview unavailable: "
                f"{__import__('html').escape(str(e))}</p>"
            )

    def _render_preview_html(self, ctx: dict, rich_keys: set) -> str:
        """Render the template context as grouped HTML for the QTextBrowser."""
        import html as _h

        def cell(key: str) -> str:
            v = ctx.get(key, "")
            if key in rich_keys:
                return v if (v and v.strip() and v.strip() != "<p></p>") \
                    else "<span style='color:#999'>&mdash;</span>"
            v = "" if v is None else str(v)
            if not v.strip():
                return "<span style='color:#999'>&mdash;</span>"
            return _h.escape(v).replace("\n", "<br>")

        parts = [
            "<style>"
            "body{font-family:'Segoe UI',sans-serif;font-size:13px;}"
            "h3{margin:12px 0 4px;font-size:13px;border-bottom:1px solid #ccc;}"
            "h3.comp{color:#2d7d46;}"
            "table{width:100%;border-collapse:collapse;}"
            "td{padding:2px 6px;vertical-align:top;}"
            "td.lbl{color:#555;width:40%;}"
            "td.comp{color:#2d7d46;font-weight:bold;}"
            ".note{color:#999;font-weight:normal;font-size:11px;}"
            "</style>"
        ]
        for section_title, field_pairs in A250_FIELD_GROUPS:
            parts.append(f"<h3>{_h.escape(section_title)}</h3><table>")
            for key, label in field_pairs:
                parts.append(
                    f"<tr><td class='lbl'>{_h.escape(label)}</td><td>{cell(key)}</td></tr>"
                )
            parts.append("</table>")

        parts.append("<h3 class='comp'>Derived &amp; Composite</h3><table>")
        for key in A250_COMPOSITE_KEYS:
            note = A250_COMPOSITE_NOTES.get(key, "")
            parts.append(
                f"<tr><td class='lbl comp'>{_h.escape(key)}"
                f"<br><span class='note'>{_h.escape(note)}</span></td>"
                f"<td>{cell(key)}</td></tr>"
            )
        parts.append("</table>")
        return "".join(parts)
```

- [ ] **Step 5: Write the preview test**

```python
# tests/test_a250_preview.py
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
```

- [ ] **Step 6: Run the preview tests**

Run: `python -m pytest tests/test_a250_preview.py -v`
Expected: PASS (3 passed)

- [ ] **Step 7: Commit**

```bash
git add app.py tests/test_a250_preview.py
git commit -m "feat(a250): Overleaf-style live preview pane with debounced refresh"
```

---

### Task 5: Full regression + docs

Confirm the whole suite is green and document the feature.

**Files:**
- Modify: `README.md` — A250 section note about the preview pane.
- Modify: `MarketingFolderCreation.spec` — ensure `PyQt6.QtWebChannel` is collected (only if a hidden-import/module list exists).

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ --ignore=tests/test_integration.py -v`
Expected: PASS — all tests green, including the pre-existing `test_a250_generation.py` and `test_richtext_utils.py`.

- [ ] **Step 2: Check the PyInstaller spec for QtWebChannel**

Read `MarketingFolderCreation.spec`. If it lists `hiddenimports` or explicit PyQt6 submodules, add `'PyQt6.QtWebChannel'` there. If it relies on PyInstaller's PyQt6 hook (which auto-collects Qt modules), no change is needed — note that in the commit message.

- [ ] **Step 3: Update README**

In `README.md`, under the A250 form description (near the extension-points table, `README.md:214`), add a line:

```markdown
| A250 live preview pane | `app.py` → `_render_preview_html()` / `_refresh_preview()`; context via `utils/a250_context.py` |
```

And under "Adding a new A250 field", append:

```markdown
4. The field appears in the live preview automatically because the preview reads
   `A250_FIELD_GROUPS` — the same list that builds the form.
```

- [ ] **Step 4: Commit**

```bash
git add README.md MarketingFolderCreation.spec
git commit -m "docs(a250): document live preview pane; bundle QtWebChannel"
```

- [ ] **Step 5: Manual smoke check (human)**

Run `python app.py`, click **Create A250**. Verify: typing in Client Name / Title / License updates the `requested_by` composite in the right pane within ~0.3 s; typing a number in Fee shows it formatted (`5,000.00`); bold/italic in Project Description renders bold/italic in the preview; leaving Invoice To empty shows it mirroring Requested By.

---

## Self-Review

**Spec coverage:**
- Split-pane layout (spec §1) → Task 4.
- Shared context builder (spec §2) → Task 1 + Task 2 refactor.
- Live debounced refresh + Quill bridge (spec §3) → Task 3 (bridge) + Task 4 (timer/wiring).
- Grouped panel, composites highlighted, rich-text rendered (spec §4) → Task 4 `_render_preview_html`.
- Error handling (spec) → `_refresh_preview` try/except (Task 4), bridge `None` guard (Task 3).
- Testing (spec) → Tasks 1, 3, 4 tests; Task 5 full regression.
- Risks: bridge GC (Task 3 holds refs), PyInstaller QtWebChannel (Task 5 Step 2), Quill class-format caveat (documented; QTextBrowser subset matches docx).
- Deviation from spec: spec said drop `current_date`; plan KEEPS it because `test_a250_generation.py:78` asserts its presence. Harmless.

**Placeholder scan:** No TBD/TODO/"handle edge cases"/"similar to Task N". All steps carry real code and exact commands.

**Type consistency:** `build_a250_context(raw, now=None)` used identically in Tasks 1/2/4. `_collect_a250_raw(a250_vars, use_cache)` defined Task 2, used Task 4. `set_change_callback`/`cached_html` defined Task 3, used Tasks 2 (`cached_html`) and 4 (`set_change_callback`). `_refresh_preview`/`_render_preview_html` signatures consistent Task 4 ↔ tests. `A250_FIELD_GROUPS`/`A250_COMPOSITE_KEYS`/`A250_COMPOSITE_NOTES` defined once (Task 4 Step 2), consumed in Step 4.
