---
phase: quick
plan: 260401-ghb
subsystem: packaging
tags: [pyinstaller, build, windows, dll, fix]
dependency_graph:
  requires: []
  provides: [dist/ClickFolder_v2/ClickFolder_v2.exe]
  affects: [MarketingFolderCreation.spec]
tech_stack:
  added: []
  patterns: [PyInstaller onedir, underscore-safe exe name]
key_files:
  created: []
  modified:
    - MarketingFolderCreation.spec
decisions:
  - "Renamed exe from 'ClickFolder v2' to 'ClickFolder_v2' — space in Windows PyInstaller exe name causes bootloader DLL path resolution failure"
  - "Used --clean flag on pyinstaller run to purge stale bytecode cache from old name variants"
metrics:
  duration: ~1min
  completed_date: "2026-04-01"
  tasks_completed: 2
  files_modified: 1
---

# Quick Task 260401-ghb: Fix Failed-to-Load-Python-DLL Error in PyInstaller Build

**One-liner:** Renamed PyInstaller exe from `ClickFolder v2` to `ClickFolder_v2` (space to underscore) and wiped stale build cache — fixes Windows bootloader python311.dll load failure.

## What Was Done

### Task 1: Fix spec name and wipe stale build artifacts
- Changed `name='ClickFolder v2'` to `name='ClickFolder_v2'` in both the `EXE` and `COLLECT` blocks of `MarketingFolderCreation.spec`
- Deleted stale build/ and dist/ entries from prior name variants (`build/MarketingFolderCreation`, `build/ClickFolder`, `build/ClickFolder v2`, `dist/ClickFolder v2`, etc.)
- Commit: `c70c44d`

### Task 2: Run clean PyInstaller build
- Ran `pyinstaller MarketingFolderCreation.spec --clean`
- Build completed successfully: `Building COLLECT COLLECT-00.toc completed successfully.`
- Confirmed `dist/ClickFolder_v2/ClickFolder_v2.exe` exists
- Confirmed `dist/ClickFolder_v2/_internal/python311.dll` exists
- Build artifacts are gitignored; no separate commit needed

## Root Cause

Two compounding issues caused the "Failed to load python DLL" error:
1. **Space in exe name** — The PyInstaller bootloader computes `_MEIPASS` using `GetModuleFileName`, then strips the exe name. A space in the name causes Windows API path parsing to mis-resolve the `_internal/` directory, so `python311.dll` is not found.
2. **Stale build cache** — Old `.toc`/`.pkg` files from `build/MarketingFolderCreation/` could leak incorrect internal paths into new builds.

## Deviations from Plan

None — plan executed exactly as written.

## Awaiting Human Verification

`dist/ClickFolder_v2/ClickFolder_v2.exe` has been built and is awaiting manual launch test to confirm the DLL error is resolved and the application window opens correctly.

## Self-Check

- [x] `MarketingFolderCreation.spec` modified: both `name=` lines show `ClickFolder_v2`
- [x] `dist/ClickFolder_v2/ClickFolder_v2.exe` exists
- [x] `dist/ClickFolder_v2/_internal/python311.dll` exists
- [x] Commit `c70c44d` exists

## Self-Check: PASSED
