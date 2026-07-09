# A250 Exact Document Preview — Design

**Date:** 2026-07-09
**Status:** Approved
**Supersedes preview approach in:** `2026-07-08-a250-live-preview-design.md` (form/facsimile preview replaced by exact rendering)

## Problem

The A250 dialog's live preview currently renders a label→value table plus a
"Derived & Composite" section in a `QTextBrowser`. It shows *how entries map to
fields*, but it does not show the **actual document**. The user wants the preview
to show the exact output — the real generated `.docx` as Word renders it.

## Goal

Replace the form-style preview with a live view of the **literal document output**:
render the real `.docx` via the same code path used for generation, convert it to
PDF with Microsoft Word, and display the PDF in the dialog. What the user sees in
the preview is byte-for-byte what the "Generate A250" button produces.

## Decisions (locked)

- **Fidelity:** exact — render the real docx and convert to PDF. No HTML facsimile.
- **Scope:** the full document (all pages, including static Terms & Conditions and
  the Hourly Rates table), because it *is* the real rendered document.
- **Converter:** Microsoft Word via COM automation (`win32com`). Word is confirmed
  installed on the target machines (Office16); `pywin32` is already a dependency.
- **Refresh:** automatic, debounced ~1500ms after the user stops typing/editing.
  Conversion runs on a background thread with an "updating…" indicator.
- **Word dependency:** required. If Word is unavailable, the preview pane shows a
  "MS Word required for preview" message. No facsimile fallback.
- **PDF display:** PyQt6 `QtPdf` / `QPdfView` (confirmed available in the venv) —
  purpose-built, clean reload, no Chromium PDF file-lock workarounds.

## Architecture

```
form fields (raw dict)
        │  build_a250_context  (existing, shared)
        ▼
   template context ── rich fields → docxtpl.RichText
        │  docxtpl.render
        ▼
   temp .docx ── Word COM (ExportAsFixedFormat) ──► temp .pdf ──► QPdfView
```

The preview and the real "Generate A250" action share one docx-building function,
so the preview cannot drift from the generated document.

### Components

#### 1. `utils/docx_pdf.py` (new)

- `word_available() -> bool` — probes `Dispatch("Word.Application")` once, caches
  the result. Used to decide whether to wire the preview at all.
- `docx_to_pdf(word_app, docx_path, pdf_path) -> None` — converts using an
  already-open Word application instance via `ExportAsFixedFormat`
  (`ExportFormat=17`, PDF).
- Word is created with **dynamic `win32com.client.Dispatch`** (NOT
  `EnsureDispatch`) to avoid the `gen_py` makepy cache, which breaks under a
  PyInstaller-frozen executable.
- Word instance configured `Visible=False`, `DisplayAlerts=0` (suppress modal
  dialogs that would hang automation).

#### 2. `render_a250_docx(raw: dict, out_path: Path) -> None` (refactor in app.py)

Extracted from the current `_generate_a250` body. Given a raw field dict:
build context (`build_a250_context`), convert the two rich-text fields
(`project_description`, `detailed_scope`) to `docxtpl.RichText` via
`html_to_richtext`, render `templates/A250.docx`, save to `out_path`.

- `_generate_a250` collects raw with `use_cache=False` (synchronous Quill pull),
  resolves the output filename/location, then calls `render_a250_docx`.
- The preview path collects raw with `use_cache=True` (Quill bridge cache),
  then calls the same `render_a250_docx` into a temp path.

#### 3. `workers/preview_worker.py` (new) — `A250PreviewWorker(QObject)`

Lives on its own `QThread`.

- On thread start: `pythoncom.CoInitialize()`, launch the persistent hidden Word
  instance (lazy — created on first render).
- Slot `request_render(raw: dict)`:
  - **Coalescing:** if a render is in flight, store `raw` as the pending request
    and return. When the current render finishes, if a pending request exists,
    run it (using only the latest). Guarantees the preview always converges to the
    newest input without queueing stale renders.
  - Runs `render_a250_docx(raw, tmp_docx)` then `docx_to_pdf(word, tmp_docx, tmp_pdf)`.
  - **Ping-pong temp paths:** alternate between `preview_a.pdf` / `preview_b.pdf`
    so the file `QPdfView` currently holds open is never the one Word overwrites.
  - Emits `finished(pdf_path: str)` on success, `failed(msg: str)` on error.
- Cleanup slot `shutdown()`: quit Word, `CoUninitialize()`, delete temp files.
- Temp files live under the OS temp dir (a dedicated subfolder), not the project.

#### 4. `A250PreviewPane(QWidget)` (new)

- Wraps `QPdfView` + `QPdfDocument`. Continuous multipage scroll
  (`PageMode.MultiPage`, zoom fit-width).
- `show_pdf(path)`: `document.load(path)` (reload replaces prior document cleanly).
- `set_updating(bool)`: shows/hides an "updating…" overlay label.
- `show_unavailable(msg)`: shows a centered message (e.g. Word missing).

### `_open_a250_form` wiring changes

- Replace the `QTextBrowser` preview with `A250PreviewPane` in the right splitter pane.
- If `word_available()` is False: `pane.show_unavailable("MS Word required for preview")`
  and skip all worker wiring. The form still works for generation.
- Otherwise: create the `QThread` + `A250PreviewWorker`, move worker to thread, start.
- Debounce `preview_timer` interval → **1500ms**. On timeout:
  1. Collect raw on the main thread (`use_cache=True`).
  2. `pane.set_updating(True)`.
  3. Emit a signal delivering `raw` to `worker.request_render` (queued connection —
     crosses into the worker thread safely).
- `worker.finished(path)` → `pane.show_pdf(path)`, `pane.set_updating(False)`.
- `worker.failed(msg)` → `pane.set_updating(False)`, show the message (log + inline).
- Initial render fires once on open (empty fields → shows the blank template).
- On dialog close (`finished`/`reject`): call `worker.shutdown()`, quit + wait the
  thread, so no zombie Word process or leaked temp files remain.

### Removed

- `_render_preview_html` (label→value + composite-note table builder).
- The `QTextBrowser` instance for this panel and its HTML string assembly.
- `A250_COMPOSITE_KEYS` / `A250_COMPOSITE_NOTES` usage in the preview (composite
  values now appear in position within the rendered document). The constants may
  remain if referenced elsewhere; otherwise remove.

`build_a250_context` is unchanged.

## Data flow / threading

- Raw collection always happens on the **main (GUI) thread** — Quill bridge cache
  reads and widget reads must not cross threads.
- The raw dict (plain, picklable strings) is passed to the worker thread via a
  queued signal.
- `docxtpl` render and Word COM both run **on the worker thread**; COM is
  initialized on that thread.
- PDF display (`QPdfView`) happens back on the main thread via `finished` signal.

## Error handling

- `word_available()` false → preview disabled with a message; generation unaffected.
- Render/convert exception in worker → `failed(msg)`; pane clears "updating…", shows
  the error; the previous PDF (if any) stays visible. Never crashes the dialog.
- Word modal dialogs suppressed (`DisplayAlerts=0`). Conversion wrapped so a hung
  or failed Word call surfaces as `failed` rather than blocking.
- Cleanup (`shutdown`) guarded in `finally` — Word quit and temp deletion always
  attempted even after errors.

## Testing

- `tests/test_docx_pdf.py`
  - `render_a250_docx` produces a valid `.docx` (openable via docxtpl/zipfile) that
    contains expected substituted text (e.g. a known project title, formatted fee).
    No Word required — pure docx assertion.
  - `docx_to_pdf` conversion test: **skipped** when `word_available()` is False
    (keeps CI/non-Word machines green); on a Word machine, asserts a non-empty PDF
    with a `%PDF` header is produced.
- `tests/test_a250_preview.py` (update)
  - Remove HTML-table / composite-note assertions.
  - Assert `render_a250_docx` is the shared path used by both preview and generation
    (e.g. both produce identical docx bytes for identical raw input, modulo the
    output filename).
- Worker coalescing unit test: inject a fake converter (no Word), fire several
  `request_render` calls rapidly, assert only the latest raw is rendered after the
  in-flight one completes.

## Packaging (PyInstaller)

- Add `QtPdf` and `QtPdfWidgets` (and their Qt PDF plugin/runtime) to `app.spec`
  hiddenimports / datas so the frozen build can display PDFs.
- `win32com` / `pywin32` already bundled — keep dynamic `Dispatch` so no gen_py
  cache is needed at runtime.

## Risks & mitigations

- **Word cold start (~2–3s first render):** persistent Word instance kept alive
  across refreshes so only the first is slow.
- **Zombie Word processes:** `shutdown()` on dialog close + `finally` guards; Word
  `Quit()` called explicitly.
- **Frozen-exe COM (gen_py):** use dynamic `Dispatch`, never `EnsureDispatch`.
- **File-lock on PDF overwrite:** ping-pong A/B temp filenames.
- **Fast typing thrash:** 1500ms debounce + coalescing means at most one render per
  settle, always the newest input.

## Out of scope

- Non-Word (LibreOffice) conversion path.
- Exporting/saving the preview PDF (generation already writes the docx).
- Any change to the A250 template itself or `build_a250_context` logic.
