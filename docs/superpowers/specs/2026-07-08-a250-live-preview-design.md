# A250 Live Preview Panel — Design

**Date:** 2026-07-08
**Status:** Approved (design), pending spec review
**Author:** Abhinav Bindal (with Claude)

## Problem

The A250 form (`app.py` → `_open_a250_form`) is a scrollable dialog of grouped input
fields. Users only see the result *after* clicking **Generate A250**, which renders
`templates/A250.docx` and opens it in Word. Several fields are transformed before they
reach the document and those transformations are invisible during editing:

- **Composites** — `requested_by`, `invoice_to`, `client_signed` are built from multiple
  inputs (`client_name`, `client_title`, `client_license`, `client`) with *conditional*
  line-break logic based on combined length.
- **Formatted** — `fee` is run through `format_number` (`1,234.56`).
- **Rich text** — `project_description`, `detailed_scope` go through `html_to_richtext`,
  which only preserves bold/italic/underline/strike + bullet lists; other Quill formatting
  (alignment, indent, color) is silently dropped.

The user cannot tell where each value lands or how it will be formatted until the Word file
opens. This design adds a **live resolved-values preview** so edits are visible as they type.

## Goal

Give the user real-time visibility into where every form value goes and how it will be
formatted, so they are confident in the output before generating the document.

## Non-Goals

- Faithful pixel-level `.docx`/PDF rendering (rejected: needs Word/LibreOffice dependency,
  seconds-per-render, bundling risk).
- Changing the A250 template, field set, or generation output.
- Editing values *in* the preview — it is strictly read-only.

## Design Decisions (locked with user)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Preview type | Resolved-values panel (not doc mockup, not true docx render) | No docx-sync burden; shows exactly where inputs land |
| Scope | **All** template fields, composites highlighted | Full picture of the document's data |
| Refresh | **Live, debounced 300ms** | Feels like Overleaf; coalesces edits into one render |
| Preview widget | `QTextBrowser` | Native, instant, zero extra process; renders the SAME HTML subset the docx gets |

## Architecture

Four parts. Sections 1–4 map to the approved design sections.

### 1. Layout — split pane

Replace the A250 dialog's single scroll area with a horizontal `QSplitter`:

- **Left pane** — the existing scrollable form, unchanged (`QScrollArea` → grouped
  `QGroupBox`/`QFormLayout`).
- **Right pane** — a read-only `QTextBrowser` preview.

Dialog resizes ~700 → ~1150 wide. Splitter is draggable; give the form a sensible initial
stretch (e.g. 55/45). Preview pane has a header label ("Preview — how this maps to the
document").

### 2. Shared context builder — the key refactor

Extract the composite/derived logic currently inline in `_generate_a250` into ONE pure
function so the preview and the real generation cannot drift:

```python
# utils/a250_context.py
def build_a250_context(raw: dict) -> dict:
    """Take raw form values (all strings / RichText-source HTML) and return the
    full context dict the docx template consumes: direct fields passed through,
    plus composites (requested_by, invoice_to, client_signed), formatted fee,
    and date fields (today, today_2)."""
```

- `raw` holds plain string values for every field, and for rich-text fields the **HTML**
  string (not yet converted to `RichText`).
- `build_a250_context` performs: `requested_by` / `client_signed` / `invoice_to`
  composition (with the length-based `\n` rules), `fee` via `format_number`, and date
  derivation. It does **not** touch the filesystem, docx, or Qt widgets.
- `_generate_a250` is refactored to: gather raw values → `build_a250_context(raw)` →
  convert rich-text HTML fields to `RichText` via `html_to_richtext` → render docx.
- The preview calls the same `build_a250_context(raw)` and renders the result as HTML.
- **Rich text in preview**: the preview shows the field's Quill HTML directly (so bold/
  italic/lists render in `QTextBrowser`); generation converts the same HTML to `RichText`.
  Because `QTextBrowser` and `html_to_richtext` support the same subset, the preview is an
  honest picture of the docx output.
- Drop the unused `current_date` assignment (no template variable consumes it).

Date handling note: `build_a250_context` needs "today". Pass it in (`build_a250_context(raw,
now=...)`) or call `datetime.now()` inside — pick pass-in so it stays pure and testable.

### 3. Live refresh — debounce + Quill bridge

**One reusable single-shot timer** on the dialog:

```python
self._preview_timer = QTimer(dialog)
self._preview_timer.setSingleShot(True)
self._preview_timer.setInterval(300)
self._preview_timer.timeout.connect(self._refresh_preview)   # restart cancels prior fire
```

Wire every input's change signal to `self._preview_timer.start()`:

- `QLineEdit.textChanged`, `QComboBox.currentTextChanged`, `QTextEdit.textChanged`.
- Rich-text editors push via **QWebChannel** (event-push, not polling):

**Python — `WebRichTextEditor` gains a bridge (`utils/web_editor.py`):**

```python
class _QuillBridge(QObject):
    def __init__(self, on_change):
        super().__init__(); self._on_change = on_change
    @pyqtSlot(str)
    def onQuillChanged(self, html: str):
        self._cached_html = html      # store latest for cheap sync reads too
        self._on_change()             # -> dialog schedules the debounce timer
```

- In `WebRichTextEditor.__init__`: create the bridge + `QWebChannel`, `registerObject`,
  and `page().setWebChannel(channel)` **before** `self._view.load(...)`. Hold Python refs
  to both (instance attributes) so they aren't GC'd.
- Expose `set_change_callback(fn)` so the dialog registers its
  `self._preview_timer.start` after constructing the editor.

**JS — `assets/editor.html`:**

```html
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
  new QWebChannel(qt.webChannelTransport, function (channel) {
      window.bridge = channel.objects.bridge;
      quill.on('text-change', function (delta, old, source) {
          if (window.bridge) window.bridge.onQuillChanged(quill.root.innerHTML);
      });
  });
</script>
```

The existing pull path (`getContent()` / `get_html_sync`) stays for the generate flow.

### 4. Panel content

`_refresh_preview()`:

1. Gather raw values from all widgets (rich-text via the bridge's cached HTML, avoiding a
   synchronous JS round-trip; fall back to `get_html_sync` if cache empty).
2. `ctx = build_a250_context(raw)`.
3. Build an HTML string grouped by the SAME sections as the form (Project Info, Client
   Contact, Billing, Scope & Fee, Additional Info, Output). Each row: label → resolved value.
4. Composite/derived rows (`requested_by`, `invoice_to`, `client_signed`, `fee`) flagged
   with an accent color and a short note (e.g. "auto-built from Name / Title / License").
5. Rich-text field values injected as their HTML so formatting renders.
6. `self._preview.setHtml(html)`.

Empty fields shown muted (e.g. grey "—") so the user sees the full field list at all times.

## Components & boundaries

| Unit | Responsibility | Depends on |
|------|----------------|------------|
| `utils/a250_context.build_a250_context` | Pure: raw dict → template context (composites, fee, dates). No Qt, no IO. | `utils.formatting.format_number` |
| `WebRichTextEditor` (extended) | Quill editor + QWebChannel bridge pushing `text-change` HTML; still supports sync pull. | PyQt6 WebEngine/WebChannel |
| `assets/editor.html` (extended) | Wires Quill `text-change` → bridge. | qwebchannel.js (qrc) |
| A250 dialog (`_open_a250_form`) | Split layout, debounce timer, `_refresh_preview` HTML assembly. | above units |
| `_generate_a250` (refactored) | Uses `build_a250_context`, then docx render. | `build_a250_context`, `html_to_richtext` |

## Error handling

- `_refresh_preview` wraps context build + HTML assembly in try/except; on error it shows a
  short "preview unavailable" note in the panel rather than crashing the dialog. Generation
  is unaffected.
- Bridge callback guards against `None` dialog/timer (editor may emit before wiring).
- If a rich-text field's cached HTML is empty, fall back to `get_html_sync()`.

## Testing

- `tests/test_a250_context.py` (new): unit tests for `build_a250_context` — the composite
  length-branch rules (`requested_by` single vs double `\n`; `client_signed` comma vs `\n`),
  `invoice_to` fallback vs custom, `fee` formatting, empty inputs. Pure function → no Qt.
- `tests/test_a250_generation.py` (existing): update to assert generation still produces the
  same context (now routed through `build_a250_context`); confirm all 28 template vars present.
- `pytest-qt`: a light test that editing a `QLineEdit` schedules the timer and
  `_refresh_preview` populates the `QTextBrowser` (can call `_refresh_preview` directly to
  avoid timing flake).

## Risks

- **Quill class-based formats** (alignment/indent) render in neither `QTextBrowser` nor the
  docx. Acceptable — the preview honestly reflects the docx. Note it in the panel if needed.
- **Bridge GC** — must hold Python refs; covered in design.
- **PyInstaller** — `qrc:///qtwebchannel/qwebchannel.js` ships with Qt WebEngine; QWebChannel
  module must be collected. Verify `PyQt6.QtWebChannel` is bundled in the `.spec`.
