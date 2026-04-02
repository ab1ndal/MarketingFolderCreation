---
phase: quick-260402-jpl
plan: 01
subsystem: templates, tests
tags: [bugfix, docxtpl, jinja2, a250, regression-test]
dependency_graph:
  requires: [templates/A250.docx]
  provides: [valid-jinja2-a250-template, a250-regression-tests]
  affects: [app.py _generate_a250, tests/test_a250_generation.py]
tech_stack:
  added: []
  patterns: [python-docx for template editing, docxtpl for validation, pytest tmp_path for output files]
key_files:
  created: []
  modified:
    - templates/A250.docx
    - tests/test_a250_generation.py
decisions:
  - "Used python-docx (not docxtpl) to open and save the template — docxtpl is read-only for rendering"
  - "Added regression tests to tests/test_a250_generation.py (existing file) rather than creating tests/test_a250.py — the plan named a non-existent file; collocating with related tests is cleaner"
  - "Pre-existing test_invoice_to_defaults_to_requested_by failure logged as deferred — caused by 260402-itx behavior change, out of scope for this task"
metrics:
  duration: ~5min
  completed: "2026-04-02"
  tasks_completed: 2
  files_changed: 2
---

# Phase quick-260402-jpl Plan 01: Fix Unexpected Error When Generating A250 Summary

**One-liner:** Repaired single-brace `{` → double-brace `}}` in A250.docx Table 0/Row 4/Col 5 to eliminate TemplateSyntaxError on Generate A250, plus four regression tests.

---

## Root Cause Found

`templates/A250.docx` Table 0, Row 4, Col 5 contained a three-run paragraph for the `{{nya_project_code}}` tag. The third run held only one closing brace (`}`) instead of two (`}}`). docxtpl's Jinja2 parser encountered the unbalanced brace and raised `TemplateSyntaxError: unexpected '}'` before any document could be rendered.

---

## Fix Applied

**Task 1 — Commit `46aa823`**

Opened `templates/A250.docx` with `python-docx`, navigated to `doc.tables[0].rows[4].cells[5].paragraphs[0].runs[2]`, changed `.text` from `'}'` to `'}}'`, and saved. Verified with:

```
DocxTemplate('templates/A250.docx').get_undeclared_template_variables()
# → {'nya_project_code', 'project_title', ...} — no exception raised
```

---

## Tests Added/Updated

**Task 2 — Commit `a98efcf`**

Added class `TestA250TemplateRegression` to `tests/test_a250_generation.py` with four tests:

| Test | What it checks |
|------|----------------|
| `test_template_parses_cleanly` | `get_undeclared_template_variables()` runs without TemplateSyntaxError; `nya_project_code` in result |
| `test_expected_vars_present_in_template` | All 9 core variable names present in parsed template variables |
| `test_render_produces_file` | `render()` + `save()` with full data dict produces a non-empty .docx on disk |
| `test_render_contains_nya_code` | Rendered document table cells contain the `NYA-2026-001` value |

All 4 new tests pass. All 8 previously-passing tests continue to pass.

---

## Deviations from Plan

### Auto-adjusted: Test file location

**Found during:** Task 2
**Issue:** Plan referenced `tests/test_a250.py` which does not exist. The existing A250 test file is `tests/test_a250_generation.py`.
**Fix:** Added the three regression tests (expanded to four to cover `test_expected_vars_present_in_template`) to the existing file rather than creating a new one.
**Files modified:** `tests/test_a250_generation.py`

---

## Deferred Items

- `test_invoice_to_defaults_to_requested_by` (pre-existing failure, not caused by this task): The 260402-itx quick task changed `invoice_to` default behavior to `'Same as "Requested By"\n' + client` instead of copying `requested_by` verbatim. The test expectation was not updated at that time. Out of scope for this task.

---

## Self-Check

**templates/A250.docx exists and was modified:**
FOUND

**tests/test_a250_generation.py exists with new tests:**
FOUND

**Commits exist:**
- `46aa823` — fix(quick-260402-jpl): repair malformed Jinja2 tag in A250.docx
- `a98efcf` — test(quick-260402-jpl): add regression tests for A250 template validity

## Self-Check: PASSED
