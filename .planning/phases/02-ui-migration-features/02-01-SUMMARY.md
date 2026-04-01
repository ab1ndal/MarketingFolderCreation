---
phase: 02-ui-migration-features
plan: 01
subsystem: ui
tags: [pyqt6, qmessagebox, qlabel, progress, validation, docxtpl]

# Dependency graph
requires:
  - phase: 01-pyqt6-infrastructure-threading
    provides: FolderSetupApp QMainWindow with WorkflowWorker signal/slot wiring
provides:
  - step_label QLabel below progress bar showing plain-English step descriptions (UI-02)
  - QMessageBox.warning dialog on workflow failure in _on_workflow_finished (UI-03)
  - QMessageBox.critical dialog in validate_paths on invalid path (UI-03)
  - A250 document saves to save_location field value instead of cwd (WF-07)
  - UI-01 confirmed: no Tkinter imports in app.py or utils/
  - WF-06 confirmed: Browse buttons with QFileDialog already present
affects: [03-testing-polish]

# Tech tracking
tech-stack:
  added: [subprocess (stdlib, for Explorer /select after A250 generation)]
  patterns: [QMessageBox.warning for workflow-level errors, QMessageBox.critical in utility functions with None parent]

key-files:
  created: []
  modified: [app.py, utils/validate.py]

key-decisions:
  - "Pass None as QMessageBox parent in validate_paths — function has no window reference, dialog still appears modal"
  - "Fall back to Path.cwd() in _generate_a250 if save_location is blank — preserves backward compatibility"
  - "Use subprocess.Popen explorer /select to open output folder after A250 generation — no QMessageBox needed for success case"
  - "Keep setWindowTitle call in _update_progress alongside new step_label — both update in tandem"

patterns-established:
  - "Error dialogs: QMessageBox.warning/critical used for unmissable user feedback; write_log for detail panel"
  - "validate_paths: show dialog AND call log_func so both dialog and log panel are populated"

requirements-completed: [UI-01, UI-02, UI-03, WF-06, WF-07]

# Metrics
duration: 2min
completed: 2026-03-31
---

# Phase 2 Plan 01: UI Gaps — Step Label, Error Dialogs, A250 Save Path Summary

**QLabel step description below progress bar, QMessageBox error dialogs on validation and workflow failure, A250 saves to user-specified save_location field**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-01T03:56:24Z
- **Completed:** 2026-04-01T03:57:35Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `step_label` QLabel below progress bar so non-technical users see plain-English step text during workflow runs (UI-02)
- Added `QMessageBox.warning` in `_on_workflow_finished` else branch so users get an unmissable dialog on failure (UI-03)
- Updated `validate_paths` in utils/validate.py to show `QMessageBox.critical` on invalid path, replacing silent log-only behavior (UI-03)
- Fixed `_generate_a250` to use the `save_location` field value when building `output_path`, with cwd fallback if blank (WF-07)
- Confirmed UI-01 (no Tkinter) and WF-06 (Browse buttons with QFileDialog) already satisfied — no code changes needed
- Added `subprocess.Popen` to open Explorer at the generated A250 file location for immediate user access

## Task Commits

Each task was committed atomically:

1. **Task 1: Add step-description label and wire error dialogs** - `81cb573` (feat)
2. **Task 2: Update validate_paths to show QMessageBox on error** - `adcfa14` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `app.py` - Added step_label QLabel, QMessageBox.warning on failure, fixed A250 save_location, added subprocess import
- `utils/validate.py` - Replaced silent log with QMessageBox.critical + log_func combo, removed emoji, added label_names mapping

## Decisions Made
- Pass `None` as parent to `QMessageBox.critical` in `validate_paths` — the utility function holds no window reference; dialog still renders modal
- Fall back to `Path.cwd()` in `_generate_a250` if `save_location` is blank — preserves old behavior when user leaves the field empty
- Use `subprocess.Popen('explorer /select,...')` to reveal generated file — no success QMessageBox needed; write_log is sufficient
- Kept `setWindowTitle(...)` in `_update_progress` — it was not wrong, just insufficient alone alongside the new step_label

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- UI-01, UI-02, UI-03, WF-06, WF-07 requirements fully satisfied
- 31 unit tests still passing after changes
- Ready for Phase 02 Plan 02 (tests for validate.py) or Phase 03 (testing/polish)

---
*Phase: 02-ui-migration-features*
*Completed: 2026-03-31*
