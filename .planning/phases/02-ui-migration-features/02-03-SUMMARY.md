---
phase: 02-ui-migration-features
plan: 03
subsystem: testing
tags: [pytest-qt, pyqt6, integration-test, robocopy, qtbot]

requires:
  - phase: 02-01
    provides: FolderSetupApp QMainWindow with project_name_field, path_fields dict, run_btn, cancel_btn, worker attribute
  - phase: 02-02
    provides: WorkflowWorker QThread with progress/log_message/finished signals, cancel() method

provides:
  - pytest-qt integration test suite covering full fill->run->filesystem workflow
  - test_happy_path_creates_correct_folder_structure: verifies BD dir, Work dir, deletion of "1 Marketing", shortcut creation
  - test_cancel_during_run_does_not_crash: verifies no crash and button states reset correctly after cancel
  - pytest-qt in tests/requirements.txt

affects: [03-testing-polish, future-integration-tests]

tech-stack:
  added: [pytest-qt==4.5.0]
  patterns: [qtbot.addWidget for widget lifecycle, qtbot.mouseClick for UI interaction, qtbot.waitSignal for signal-based wait, qtbot.waitUntil for condition-based wait, patch pyperclip.copy to avoid clipboard side effects in tests]

key-files:
  created: [tests/test_integration.py]
  modified: [tests/requirements.txt]

key-decisions:
  - "Use qtbot.waitUntil(run_btn.isEnabled) for cancel test instead of waitSignal to avoid race condition where fast robocopy on tiny temp dir completes before waitSignal is registered"
  - "Patch app.pyperclip.copy in happy path test — clipboard contention (PyperclipWindowsException) in headless test environment"
  - "Patch app.QMessageBox.warning in cancel test — finished(False) triggers warning dialog that blocks event loop in tests"
  - "No mocks on copy_folder, delete_folder, create_shortcut — true integration test uses real robocopy and pywin32"

patterns-established:
  - "Integration tests patch only UI side-effects (clipboard, dialogs), not business logic"
  - "Cancel test uses qtbot.waitUntil on button state rather than waitSignal to prevent race conditions with fast-completing workers"

requirements-completed: [TEST-06]

duration: 8min
completed: 2026-03-31
---

# Phase 2 Plan 3: Integration Test — fill->run->filesystem Workflow Summary

**pytest-qt integration test exercising full PyQt6 + WorkflowWorker + robocopy pipeline against real temp directories, verifying BD/Work folder creation, "1 Marketing" deletion, and shortcut creation**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-31T00:00:00Z
- **Completed:** 2026-03-31T00:08:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Installed pytest-qt 4.5.0 and registered it in tests/requirements.txt
- Happy path test fills all 4 path fields programmatically, clicks Run, waits for finished(True), and asserts all three filesystem outcomes (BD dir exists, Work dir exists, "1 Marketing" deleted, shortcut present)
- Cancel test clicks Run then Cancel immediately, waits for run_btn to be re-enabled, confirms no crash and button states are correct
- All 47 tests pass (31 prior unit tests + new validate/a250 tests + 2 new integration tests)

## Task Commits

1. **Task 1: Install pytest-qt and add to test requirements** - `443f819` (chore)
2. **Task 2: Write test_integration.py — fill->run->filesystem workflow test** - `ca85883` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `tests/test_integration.py` - pytest-qt integration test with TestWorkflowIntegration class (happy path + cancel)
- `tests/requirements.txt` - Added pytest-qt dependency (unpinned)

## Decisions Made
- Used `qtbot.waitUntil(lambda: window.run_btn.isEnabled())` in cancel test instead of `qtbot.waitSignal` — temp dir robocopy completes so fast that `finished` signal fires before `waitSignal` context is entered, causing 30s false timeout
- Patched `app.pyperclip.copy` in happy path — `_on_workflow_finished` calls `pyperclip.copy()` on success, but this raises `PyperclipWindowsException` in headless test environment due to clipboard contention
- Patched `app.QMessageBox.warning` in cancel test — `_on_workflow_finished(False)` calls `QMessageBox.warning(...)` which blocks the Qt event loop in a test context

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Race condition in cancel test: waitSignal missed already-fired signal**
- **Found during:** Task 2 (writing integration test)
- **Issue:** `qtbot.waitSignal(window.worker.finished)` registered AFTER `mouseClick(run_btn)` and `mouseClick(cancel_btn)`. On a tiny temp dir, robocopy completes in < 100ms and fires `finished` before `waitSignal` is entered, causing 30s timeout.
- **Fix:** Replaced `qtbot.waitSignal(worker.finished)` with `qtbot.waitUntil(lambda: window.run_btn.isEnabled())` which polls a condition already set before the call
- **Files modified:** tests/test_integration.py
- **Verification:** Cancel test passes in 0.56s without timeout
- **Committed in:** ca85883

**2. [Rule 2 - Missing Critical] Patch pyperclip.copy to prevent clipboard exception in test**
- **Found during:** Task 2 (running happy path test)
- **Issue:** `app._on_workflow_finished(True)` calls `pyperclip.copy()`, raising `PyperclipWindowsException: Error calling OpenClipboard` in headless test environment
- **Fix:** Added `with patch("app.pyperclip.copy"):` around Run click and waitSignal in happy path test
- **Files modified:** tests/test_integration.py
- **Verification:** Happy path test passes; clipboard not accessed during test
- **Committed in:** ca85883

**3. [Rule 2 - Missing Critical] Patch QMessageBox.warning to prevent blocking dialog in cancel test**
- **Found during:** Task 2 (designing cancel test)
- **Issue:** `_on_workflow_finished(False)` calls `QMessageBox.warning(...)` which would block event loop in test context
- **Fix:** Added `with patch("app.QMessageBox.warning"):` wrapping the Run/Cancel clicks and waitUntil
- **Files modified:** tests/test_integration.py
- **Verification:** Cancel test runs without blocking; passes in < 1s
- **Committed in:** ca85883

---

**Total deviations:** 3 auto-fixed (1 race condition bug, 2 missing test environment guards)
**Impact on plan:** All auto-fixes required for test correctness in a headless/automated environment. No scope creep — business logic untouched, only UI side-effects patched.

## Issues Encountered
- pytest `--timeout=60` flag requires `pytest-timeout` package which is not installed; ran tests without `--timeout` flag (no impact on results)

## Next Phase Readiness
- Integration tests are complete — TEST-06 satisfied
- All 47 tests pass; test suite is comprehensive
- Phase 02 complete: app UI migrated to PyQt6, WorkflowWorker threaded, integration verified end-to-end

---
*Phase: 02-ui-migration-features*
*Completed: 2026-03-31*
