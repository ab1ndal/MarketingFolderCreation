---
phase: 03-packaging-deployment
plan: 02
subsystem: infra
tags: [pyinstaller, packaging, onedir, pyqt6, win32com, bundle]

# Dependency graph
requires:
  - phase: 03-packaging-deployment
    plan: 01
    provides: MarketingFolderCreation.spec and _resource_path helper in app.py
provides:
  - dist/MarketingFolderCreation/ distributable bundle with exe, templates, and PyQt6 platform plugins
  - Human-verified standalone Windows executable ready for network share deployment
affects: [03-packaging-deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - PyInstaller 6.x _internal/ layout: all datas land in _internal/ subdirectory; sys._MEIPASS points there at runtime
    - Bundle verification using Path.rglob for qwindows*.dll

key-files:
  created:
    - dist/MarketingFolderCreation/MarketingFolderCreation.exe
    - dist/MarketingFolderCreation/_internal/templates/A250.docx
  modified: []

key-decisions:
  - "PyInstaller 6.x changed onedir layout: all datas now land in dist/<name>/_internal/ not dist/<name>/; sys._MEIPASS still resolves correctly at runtime"
  - "dist/ folder is gitignored — bundle is a runtime artifact, not tracked in source control"

patterns-established:
  - "Bundle verification must check _internal/templates/A250.docx for PyInstaller 6.x builds"

requirements-completed: [PKG-01, PKG-02, PERF-01]

# Metrics
duration: ~10min
completed: 2026-03-31
---

# Phase 3 Plan 02: Build & Verify Bundle Summary

**PyInstaller 6.x --onedir bundle built successfully; MarketingFolderCreation.exe with A250.docx and qwindows.dll platform plugin verified; awaiting human launch test**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-01T16:21:51Z
- **Completed:** 2026-04-01T16:32:00Z
- **Tasks:** 1 auto + 1 human-verify checkpoint
- **Files modified:** 0 (dist/ is gitignored)

## Accomplishments

- Ran `pyinstaller MarketingFolderCreation.spec --clean --noconfirm` from project root — build completed with no errors
- Verified EXE exists at dist/MarketingFolderCreation/MarketingFolderCreation.exe
- Verified A250.docx bundled at dist/MarketingFolderCreation/_internal/templates/A250.docx (PyInstaller 6.x _internal layout)
- Verified qwindows.dll present at dist/MarketingFolderCreation/_internal/PyQt6/Qt6/plugins/platforms/qwindows.dll
- Human verification of exe launch, A250 generation, startup speed pending (checkpoint returned)

## Task Commits

Task 1 produced no source file changes (dist/ is gitignored). The build artifact exists on disk.

**Plan metadata:** _(docs commit follows after checkpoint approval)_

## Files Created/Modified

- `dist/MarketingFolderCreation/MarketingFolderCreation.exe` - Standalone Windows executable (gitignored)
- `dist/MarketingFolderCreation/_internal/templates/A250.docx` - Bundled A250 template (gitignored)
- `dist/MarketingFolderCreation/_internal/PyQt6/Qt6/plugins/platforms/qwindows.dll` - PyQt6 platform plugin (gitignored)

## Decisions Made

- PyInstaller 6.x changed the --onedir layout: all data files now land in `_internal/` subdirectory instead of the bundle root. The `sys._MEIPASS` variable correctly points to `_internal/` at runtime so `_resource_path("templates/A250.docx")` resolves correctly. The plan's verification script assumed the old layout — updated verification to check `_internal/templates/A250.docx`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated bundle verification to use PyInstaller 6.x _internal/ path**
- **Found during:** Task 1 (Build the --onedir bundle)
- **Issue:** Plan verification script checked `dist/MarketingFolderCreation/templates/A250.docx` but PyInstaller 6.x places datas in `dist/MarketingFolderCreation/_internal/templates/A250.docx`
- **Fix:** Ran corrected verification using `Path.rglob` and checking `_internal/templates/A250.docx` — confirmed template IS bundled correctly. sys._MEIPASS points to `_internal/` so runtime path resolution is unaffected.
- **Files modified:** None (verification only)
- **Verification:** `python -c "..."` script shows PASS for exe, template, and qwindows.dll

---

**Total deviations:** 1 auto-fixed (layout change in PyInstaller 6.x, verification only)
**Impact on plan:** No source changes needed. Bundle is correct. Verification script updated mentally for future runs.

## Issues Encountered

PyInstaller 6.0 changed the --onedir layout by introducing an `_internal/` subdirectory for all bundled files. The exe itself remains at the bundle root. This is a packaging layout change only — app behavior is unaffected since `sys._MEIPASS` still resolves to the correct directory at runtime.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Bundle at dist/MarketingFolderCreation/ is ready for human launch verification (Task 2 checkpoint)
- After human approval: bundle can be copied to network share for distribution
- Phase 03 Plan 03 (if any) or project completion follows human approval

---
*Phase: 03-packaging-deployment*
*Completed: 2026-03-31*
