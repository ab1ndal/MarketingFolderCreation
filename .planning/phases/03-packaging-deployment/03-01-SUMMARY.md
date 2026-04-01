---
phase: 03-packaging-deployment
plan: 01
subsystem: infra
tags: [pyinstaller, packaging, win32com, sys._MEIPASS, onedir]

# Dependency graph
requires:
  - phase: 02-ui-migration-features
    provides: app.py with A250 generation feature using templates/A250.docx
provides:
  - MarketingFolderCreation.spec production --onedir PyInstaller spec
  - app.py _resource_path helper for bundle-aware template resolution
affects: [03-packaging-deployment, build-process]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - PyInstaller --onedir layout using COLLECT block with exclude_binaries=True
    - sys._MEIPASS resource path resolution with dev fallback to __file__.parent

key-files:
  created:
    - MarketingFolderCreation.spec
  modified:
    - app.py

key-decisions:
  - "--onedir chosen over --onefile: COLLECT block with exclude_binaries=True; consistent with plan requirement PKG-02"
  - "_resource_path helper uses getattr(sys, '_MEIPASS', Path(__file__).parent) for transparent dev/bundle switching"
  - "win32com.shell, win32com.shell.shell, win32timezone added as hiddenimports — COM dispatch loads these at runtime, not caught by static analysis"

patterns-established:
  - "_resource_path pattern: all bundled resource accesses should use _resource_path() not bare Path()"

requirements-completed: [PKG-01, PKG-02, PERF-01]

# Metrics
duration: 5min
completed: 2026-03-31
---

# Phase 3 Plan 01: PyInstaller Spec & _MEIPASS Patch Summary

**Production --onedir PyInstaller spec with win32com hiddenimports and A250.docx bundled; app.py patched with sys._MEIPASS-aware _resource_path helper**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-31T16:18:22Z
- **Completed:** 2026-03-31T16:23:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created MarketingFolderCreation.spec from scratch as a correct --onedir spec with COLLECT block, all required hiddenimports, and A250.docx datas entry
- Added `_resource_path()` module-level helper to app.py that resolves resources via sys._MEIPASS in frozen bundles, falling back to __file__.parent in dev
- Replaced bare `Path("templates/A250.docx")` in `_generate_a250` with `_resource_path("templates/A250.docx")` — all 47 tests still pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Write MarketingFolderCreation.spec for --onedir bundle** - `daea255` (feat)
2. **Task 2: Patch app.py for sys._MEIPASS template path resolution** - `a2e689d` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `MarketingFolderCreation.spec` - Production --onedir PyInstaller spec; COLLECT layout, A250.docx datas, win32com hiddenimports, console=False, FolderCreatorTool.ico
- `app.py` - Added `_resource_path()` helper (lines 27-34); updated `_generate_a250` to call `_resource_path("templates/A250.docx")`

## Decisions Made

- Used `getattr(sys, '_MEIPASS', Path(__file__).parent)` rather than `if hasattr(sys, '_MEIPASS')` block — more concise and idiomatic for this pattern
- No additional hiddenimports beyond the three win32com entries — PyQt6, docxtpl, and pyperclip all bundle cleanly via PyInstaller's standard hooks

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- spec and app.py patch are complete; ready for Phase 03 Plan 02 (build verification / CI)
- PyInstaller build can now be run with: `pyinstaller MarketingFolderCreation.spec`
- Output will be in `dist/MarketingFolderCreation/` directory

---
*Phase: 03-packaging-deployment*
*Completed: 2026-03-31*
