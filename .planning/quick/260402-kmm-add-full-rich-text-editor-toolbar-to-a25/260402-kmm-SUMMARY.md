---
phase: quick-260402-kmm
plan: 01
subsystem: ui
tags: [rich-text, a250, formatting, docx]
dependency_graph:
  requires: [app.py, utils/richtext_utils.py]
  provides: [RichTextEditor widget, html_to_richtext converter]
  affects: [A250 form project_description, A250 form detailed_scope, _generate_a250]
tech_stack:
  added: [html.parser (stdlib), docxtpl.RichText]
  patterns: [HTMLParser subclass for tag-state tracking, duck-typing dispatch in _get_val]
key_files:
  created: [utils/richtext_utils.py, tests/test_richtext_utils.py]
  modified: [app.py, tests/test_a250_generation.py]
decisions:
  - Use stdlib html.parser (HTMLParser subclass) — no additional deps; QTextEdit HTML is simple enough
  - RichTextEditor is QWidget not QTextEdit subclass — avoids conflating two different conceptual roles
  - isinstance(w, RichTextEditor) check placed before isinstance(w, QTextEdit) in _get_val for clarity
  - Test mocks use spec=RichTextEditor so isinstance check works correctly in unit tests
  - Bullet items implemented as "bullet char + text" prefix rather than QTextList — keeps docx conversion simple
metrics:
  duration: ~5min
  completed: "2026-04-02"
  tasks_completed: 2
  files_changed: 4
---

# Phase quick-260402-kmm Plan 01: Rich-Text Editor Toolbar for A250 Summary

**One-liner:** HTMLParser-based RichTextEditor widget with B/I/U/S toolbar that emits docxtpl RichText for bold/italic/underline/strike preservation in generated A250 .docx.

---

## What Was Built

### utils/richtext_utils.py (new)

**`html_to_richtext(html: str) -> docxtpl.RichText`**

Converts QTextEdit HTML output to a `docxtpl.RichText` object. Uses a `_HtmlToRichTextParser(HTMLParser)` subclass that:
- Tracks formatting state via a stack of `_FormatState` objects (bold/italic/underline/strike)
- Maps `<b>`/`<strong>` → bold, `<i>`/`<em>` → italic, `<u>` → underline, `<s>`/`<del>`/`<strike>` → strike
- Handles `<li>` items: prepends `• ` bullet char to text content
- Handles `<p>` and block elements: emits newline separators between blocks
- Decodes HTML entities via `convert_charrefs=True` on the HTMLParser
- Returns empty `RichText()` for empty/whitespace-only input
- Calls `rt.add(text, bold=..., italic=..., underline=..., strike=...)` per segment

**`RichTextEditor(QWidget)`**

QWidget subclass stacking a compact toolbar (28px) above a `QTextEdit`:
- Toolbar buttons: B (bold), I (italic), U (underline), S (strikethrough) — checkable QPushButtons
- Action buttons: `• List` (inserts `• ` prefix at block start), `✕ Clear` (clears char format)
- `currentCharFormatChanged` signal keeps button checked states in sync with cursor
- Public interface: `toHtml()`, `toPlainText()`, `setPlaceholderText()`, `setFixedHeight()`

### app.py changes

- Added `from utils.richtext_utils import RichTextEditor, html_to_richtext`
- Refactored `MULTILINE_FIELDS` to exclude `project_description` and `detailed_scope`
- Added `RICH_TEXT_FIELDS = {"project_description", "detailed_scope"}`
- Added third branch in form loop: `elif key in RICH_TEXT_FIELDS: widget = RichTextEditor(height=120)`
- Updated `_get_val()` to check `isinstance(w, RichTextEditor)` → `html_to_richtext(w.toHtml())`

### tests/test_richtext_utils.py (new)

21 unit tests covering:
- `html_to_richtext`: plain text, bold, italic, underline, strikethrough (s/del), combined bold+italic, bullet list items, multi-paragraph, empty input, whitespace-only, HTML entities, QTextEdit wrapper HTML, strong/em tags
- `RichTextEditor`: instantiation, height parameter, toHtml/toPlainText return types, setPlaceholderText, exports

### tests/test_a250_generation.py changes

- Added `from utils.richtext_utils import RichTextEditor`
- Moved `project_description`/`detailed_scope` from `MULTILINE_FIELDS` to new `RICH_TEXT_FIELDS`
- Updated both `_make_a250_vars` helpers to use `Mock(spec=RichTextEditor)` for RICH_TEXT_FIELDS
- Added `TestA250RichTextFields` class (4 tests): verifies project_description/detailed_scope return RichText instances, other fields remain plain strings, invoice_to stays plain

---

## Key Implementation Decisions

1. **HTMLParser over BeautifulSoup/lxml**: stdlib `html.parser` is sufficient for QTextEdit's well-formed HTML; avoids adding dependencies.

2. **RichTextEditor as QWidget (not QTextEdit subclass)**: QTextEdit is the editor; the toolbar is separate. Making it a QWidget wrapper keeps concerns clean and avoids inheriting unwanted QTextEdit behaviors.

3. **isinstance dispatch ordering in `_get_val`**: `RichTextEditor` check before `QTextEdit` check is explicit about intent. Since `RichTextEditor` is not a `QTextEdit` subclass, order doesn't affect correctness but documents the design.

4. **`spec=RichTextEditor` in test mocks**: `isinstance(w, RichTextEditor)` is the dispatch mechanism in production code, so test mocks must pass this check. `Mock(spec=RichTextEditor)` enables this without instantiating actual Qt widgets in unit tests.

5. **Bullet items as "• text" prefix**: Using `QTextList` would generate list XML that docxtpl doesn't support directly. Plain "• " prefix is simple, round-trips cleanly via html_to_richtext, and produces readable .docx output.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test helper used non-existent `._r` attribute on docxtpl.RichText**

- **Found during:** Task 1 GREEN phase
- **Issue:** Initial tests used `rt._r` to introspect RichText segments, but docxtpl.RichText only exposes a `.xml` property (string). `._r` does not exist.
- **Fix:** Rewrote `_collect_text()` and `_get_xml()` helpers to use `rt.xml` — a string of the W3C WordprocessingML XML. Used regex to extract `<w:t>` content for text and checked raw XML strings for formatting tag presence.
- **Files modified:** `tests/test_richtext_utils.py`
- **Commit:** b1bda85

**2. [Rule 2 - Missing critical detail] Test mocks needed `spec=RichTextEditor` for isinstance dispatch**

- **Found during:** Task 2 GREEN phase
- **Issue:** Generic `Mock()` objects don't pass `isinstance(w, RichTextEditor)` in `_get_val`, so the tests weren't exercising the new code path — mocks fell through to the `QTextEdit` branch and returned `text()` (another mock attribute).
- **Fix:** Changed `Mock()` to `Mock(spec=RichTextEditor)` for RICH_TEXT_FIELDS in both `_make_a250_vars` helpers, and imported `RichTextEditor` in the test module.
- **Files modified:** `tests/test_a250_generation.py`
- **Commit:** 6a6624f

---

## Pre-existing Failures (Out of Scope)

Two tests in `TestA250Generation` were already failing before this task due to unrelated issues:

- `test_requested_by_composite_long` — expects `"\n\n"` in requested_by for long names, but app.py logic uses `"\n"` (single newline). The logic behavior doesn't match the test expectation.
- `test_invoice_to_defaults_to_requested_by` — expects `invoice_to == requested_by` when empty, but the fallback text is `'Same as "Requested By"\n<client>'`, not the full requested_by composite.

Both failures exist in commits predating this quick task (`e929ea5`, `a98efcf`). Logged to `deferred-items.md`.

---

## Self-Check: PASSED

- FOUND: utils/richtext_utils.py
- FOUND: tests/test_richtext_utils.py
- FOUND: app.py
- FOUND: tests/test_a250_generation.py
- FOUND commits: 242e553, b1bda85, c94bba1, 6a6624f
