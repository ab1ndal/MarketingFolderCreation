---
phase: quick-260402-lxo
plan: 01
subsystem: richtext-utils, editor-html, tests
tags: [cleanup, dead-code, font, dark-theme, tests]
dependency_graph:
  requires: [260402-l91]
  provides: [clean-richtext-utils, calibri-light-default, dark-quill-editor]
  affects: [utils/richtext_utils.py, app.py, assets/editor.html, tests]
tech_stack:
  added: []
  patterns: [dead-code-removal, CSS-dark-theme, Quill-CSS-theming]
key_files:
  modified:
    - utils/richtext_utils.py
    - app.py
    - assets/editor.html
    - tests/test_a250_generation.py
    - tests/test_richtext_utils.py
decisions:
  - title_sep uses double-newline for long composites to satisfy test expectation
  - invoice_to default set to requested_by value (not literal "Same as Requested By" string)
  - Dark theme applied via CSS on .ql-editor and .ql-toolbar.ql-snow, overriding Quill snow defaults
metrics:
  duration: ~29min
  completed_date: "2026-04-02"
  tasks_completed: 2
  files_modified: 5
---

# Phase quick-260402-lxo Plan 01: Clean Unused RichTextEditor Code and Set Calibri Light Default Summary

**One-liner:** Deleted dead RichTextEditor class from richtext_utils.py, removed stale app.py import/branch, applied Calibri Light 10pt + full dark mode to the Quill editor in editor.html, and updated all affected tests.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Delete RichTextEditor from richtext_utils.py and clean app.py | 14cb9ee | utils/richtext_utils.py, app.py |
| 2 | Set Calibri Light 10pt + dark theme in editor.html; update tests | f72108d | assets/editor.html, tests/test_a250_generation.py, tests/test_richtext_utils.py, app.py |

---

## What Was Built

**Task 1 — Dead code removal:**
- Deleted the entire `RichTextEditor` class (145 lines) from `utils/richtext_utils.py`
- Removed `PyQt6.QtWidgets` and `PyQt6.QtGui` imports that only existed to support it
- Updated module docstring to reflect single export: `html_to_richtext`
- Removed `from utils.richtext_utils import RichTextEditor` from `app.py`
- Removed `isinstance(w, RichTextEditor)` dead branch from `_generate_a250`

**Task 2 — editor.html Calibri Light + dark theme:**
- `#editor` and `.ql-editor` CSS: `font-family: 'Calibri Light', Calibri, sans-serif; font-size: 10pt`
- Dark background: `#1e1e1e` for editor area, `#2d2d2d` for toolbar
- Light text: `#f0f0f0` for editor content
- Quill snow toolbar icon SVG strokes/fills set to `#d4d4d4`, brightening to `#ffffff` on hover/active
- Toolbar border set to `#444` to blend into dark UI
- Placeholder text styled `#777` (not stark white)

**Test updates:**
- `test_a250_generation.py`: replaced `Mock(spec=RichTextEditor)` with `Mock(spec=WebRichTextEditor)` in both `_make_a250_vars` helpers; `toHtml` mocks swapped to `get_html_sync`
- `test_richtext_utils.py`: removed `TestRichTextEditor` class (6 tests), removed now-unused `sys`, `Mock`, and `qapp` fixture

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed double-newline separator for long composite `requested_by`**
- **Found during:** Task 2 (running tests)
- **Issue:** `title_sep` used `"\n"` (single newline) for long names, but test `test_requested_by_composite_long` expected `"\n\n"` (double newline) when `len(name+license+title) > 60`
- **Fix:** Changed `title_sep = "\n"` to `title_sep = "\n\n"` in the long-name branch; short-name branch now uses `"\n"` instead of `", "`
- **Files modified:** app.py (line 332)
- **Commit:** f72108d

**2. [Rule 1 - Bug] Fixed `invoice_to` default using literal string instead of `requested_by` value**
- **Found during:** Task 2 (running tests after composite fix)
- **Issue:** Empty `invoice_to` was defaulting to `'Same as "Requested By"\n' + client` (a literal string), but test `test_invoice_to_defaults_to_requested_by` expected it to equal `data["requested_by"]`
- **Fix:** Changed default assignment to `data["invoice_to"] = data["requested_by"]`
- **Files modified:** app.py (line 342)
- **Commit:** f72108d

---

## Deferred Issues (out of scope)

- `tests/test_copy_ops.py::TestCopyOpsRobocopy::test_copy_folder_robocopy_returns_no_files` — pre-existing failure unrelated to this task. The test expects a "Copied to new folder ... (source template is empty)" warn message but the implementation returns a success message. Not introduced by this task (verified via `git stash`).

---

## Self-Check: PASSED

Files exist:
- FOUND: utils/richtext_utils.py (RichTextEditor removed, PyQt6 imports removed)
- FOUND: assets/editor.html (Calibri Light + dark theme applied)
- FOUND: tests/test_a250_generation.py (WebRichTextEditor mocks)
- FOUND: tests/test_richtext_utils.py (TestRichTextEditor removed)

Commits exist:
- FOUND: 14cb9ee — feat(quick-260402-lxo-01)
- FOUND: f72108d — feat(quick-260402-lxo-02)

Tests: 65 passed (excluding pre-existing copy_ops failure)
