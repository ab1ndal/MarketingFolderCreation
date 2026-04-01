---
phase: 02-ui-migration-features
plan: 02
subsystem: testing
tags: [pytest, pytest-mock, pyqt6, docxtpl, unit-tests]

# Dependency graph
requires:
  - phase: 02-ui-migration-features/02-01
    provides: validate_paths with QMessageBox and label_names dict; _generate_a250 with save_location routing
provides:
  - Unit tests for validate_paths covering all validation cases (TEST-04)
  - Unit tests for _generate_a250 covering success, save_location routing, and error handling (TEST-05)
affects: [02-03-integration-tests, future test suites]

# Tech tracking
tech-stack:
  added: []
  patterns: [pytest parametrize for key/label mapping, QApplication module fixture for widget testing, MagicMock for DocxTemplate, patch subprocess.Popen to avoid Explorer side effects]

key-files:
  created:
    - tests/test_validate_paths.py
    - tests/test_a250_generation.py
  modified:
    - utils/validate.py

key-decisions:
  - "Treat empty string path as invalid: added 'not path' guard in validate_paths because Path('').exists() returns True on Windows (resolves to cwd)"
  - "Patch subprocess.Popen in A250 tests to prevent Windows Explorer side effects during test runs"
  - "Use module-scoped qapp fixture for A250 tests to avoid creating QApplication per test"

patterns-established:
  - "Patch utils.validate.QMessageBox.critical for validate_paths tests (not PyQt6.QtWidgets.QMessageBox.critical)"
  - "Use tmp_path built-in fixture for real temporary paths in path validation tests"
  - "Mock QLineEdit.text() returns via Mock(text=Mock(return_value=v)) pattern"

requirements-completed: [TEST-04, TEST-05]

# Metrics
duration: 10min
completed: 2026-03-31
---

# Phase 02 Plan 02: Unit Tests for validate_paths and _generate_a250 Summary

**Unit tests for path validation (9 cases) and A250 document generation (5 cases) using pytest-mock to avoid real filesystem, Qt dialogs, and Word installation**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-01T03:57:36Z
- **Completed:** 2026-04-01T04:07:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- 9 test cases for validate_paths including parametrized key/label mapping and empty-string edge case
- 5 test cases for _generate_a250 covering render fields, save_location routing, cwd fallback, and FileNotFoundError dialog
- Auto-fixed Windows-specific bug: `Path("").exists()` returns True on Windows, needed explicit empty-string guard
- Total test suite grows from 31 to 45 tests, all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Write test_validate_paths.py (TEST-04)** - `14fcb03` (test)
2. **Task 2: Write test_a250_generation.py (TEST-05)** - `7810cd1` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `tests/test_validate_paths.py` - 9 test cases for validate_paths: all-exist, missing path, log_func, empty string, 4x parametrized key/label, stops at first failure
- `tests/test_a250_generation.py` - 5 test cases for _generate_a250: render fields, filename, save_location, cwd fallback, FileNotFoundError dialog
- `utils/validate.py` - Added empty-string guard (`not path`) before `Path(path).exists()` check

## Decisions Made
- Added `not path` guard in `validate_paths` before the `Path(path).exists()` check. On Windows, `Path("").exists()` resolves to the current directory and returns `True`, silently allowing blank paths through. The fix treats empty string as an invalid path consistently across platforms.
- Module-scoped `qapp` fixture used for A250 tests to avoid spawning a new QApplication per test while keeping widget instantiation valid.
- `subprocess.Popen` patched in A250 tests to prevent Windows Explorer from opening during test runs (side effect of the `explorer /select` call in `_generate_a250`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed empty string path treated as valid on Windows**
- **Found during:** Task 1 (test_validate_paths.py — test_empty_string_path_returns_false)
- **Issue:** `Path("").exists()` returns `True` on Windows because it resolves to `Path.cwd()`. The test expected `False` but got `True`.
- **Fix:** Added `not path` check before `Path(path).exists()` in `utils/validate.py` so empty strings immediately fail validation.
- **Files modified:** utils/validate.py
- **Verification:** `python -m pytest tests/test_validate_paths.py -v` — all 9 tests pass
- **Committed in:** 14fcb03 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — Windows platform edge case)
**Impact on plan:** Required fix for correct cross-platform behavior. No scope creep.

## Issues Encountered
- Plan's `<interfaces>` section described `validate.py` and `app.py` as updated by Plan 02-01, but 02-01 had not been executed. Both files already contained the 02-01 changes (likely from a prior session), so no blocking issue occurred and tests could be written directly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- TEST-04 and TEST-05 satisfied; 45 total tests passing with 0 failures
- Phase 02 Plan 03 (integration tests) can proceed; conftest.py fixtures are in place
- No blockers

## Self-Check: PASSED

- tests/test_validate_paths.py: FOUND
- tests/test_a250_generation.py: FOUND
- .planning/phases/02-ui-migration-features/02-02-SUMMARY.md: FOUND
- Commit 14fcb03: FOUND
- Commit 7810cd1: FOUND

---
*Phase: 02-ui-migration-features*
*Completed: 2026-03-31*
