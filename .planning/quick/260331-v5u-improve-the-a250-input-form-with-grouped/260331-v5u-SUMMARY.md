---
phase: quick
plan: 260331-v5u
subsystem: ui
tags: [pyqt6, dialog, ux, a250]
dependency_graph:
  requires: []
  provides: [grouped-a250-form]
  affects: [app.py _open_a250_form]
tech_stack:
  added: []
  patterns: [QGroupBox section grouping, QFormLayout per section]
key_files:
  created: []
  modified:
    - app.py
key_decisions:
  - Used QGroupBox per section with its own QFormLayout — clean encapsulation without changing the flat a250_vars dict contract
metrics:
  duration: ~5min
  completed_date: "2026-03-31"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
---

# Quick Task 260331-v5u: Improve A250 Input Form with Grouped Sections Summary

**One-liner:** Refactored flat 23-field A250 dialog into 5 labeled QGroupBox sections (Project Info, Client Contact, Billing, Scope & Fee, Output) with human-readable field labels.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Refactor _open_a250_form with grouped QGroupBox sections | fe0b366 | app.py |

## What Was Built

The `_open_a250_form` method in `app.py` was refactored from a flat `QFormLayout` listing all 23 raw field-name labels to a grouped layout with 5 `QGroupBox` sections:

- **Project Info** — project_title, project_address, nya_project_code, client_project_code
- **Client Contact** — client, client_address, client_phone, client_mobile, client_email, client_office
- **Billing** — client_invoice, invoice_to, Fname_R, Lname_R, title_R, licenses
- **Scope & Fee** — request_date, work_type, project_description, detailed_scope, fee
- **Output** — save_location, a250_creator

Each field now has a human-readable label (e.g., "Project Title" instead of "project_title"). The `a250_vars` dict structure is unchanged — all 23 keys still map to `QLineEdit` instances — so `_generate_a250` and the docxtpl rendering contract are unaffected.

## Verification

```
5 passed in 0.34s
tests/test_a250_generation.py::TestA250Generation::test_render_called_with_all_fields PASSED
tests/test_a250_generation.py::TestA250Generation::test_output_filename_uses_project_title PASSED
tests/test_a250_generation.py::TestA250Generation::test_save_location_used_when_provided PASSED
tests/test_a250_generation.py::TestA250Generation::test_save_location_blank_falls_back_to_cwd PASSED
tests/test_a250_generation.py::TestA250Generation::test_missing_template_shows_error_dialog PASSED
```

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- app.py modified: FOUND
- Commit fe0b366: FOUND
- All 5 tests pass: CONFIRMED
