# Marketing Folder Creation Tool — v2

## What This Is

A Windows desktop tool used by non-technical staff to set up project folders on network drives (V: BD drive, W: Work drive) and generate A250 Word documents from templates. Users enter a project name, click Run, and the tool handles all file system operations automatically. Distributed as a standalone executable — no Python or installation required.

## Core Value

Non-technical users can set up a project in seconds, from any machine, without touching file paths or knowing anything about the underlying file system.

## Requirements

### Validated

- ✓ Copy marketing template folder to BD target (V: drive) — existing
- ✓ Copy work template folder to Work target (W: drive) — existing
- ✓ Delete "1 Marketing" subfolder from work folder — existing
- ✓ Create shortcut from work folder to BD folder — existing
- ✓ Generate A250 Word document from template with user-filled fields — existing
- ✓ Path validation before workflow execution — existing
- ✓ Log output with info/success/error/warn levels — existing
- ✓ Clipboard copy of work folder path after setup — existing

### Active

- [ ] Startup time under 3 seconds when launched from a network share (fix --onefile → --onedir PyInstaller packaging)
- [ ] UI never freezes during folder operations (move ops to background thread)
- [ ] Cancel/abort running operations mid-workflow
- [ ] Modern PyQt6-based interface replacing Tkinter
- [ ] Progress feedback clear enough for non-technical users (no jargon)
- [ ] Full test suite: file operations, validation, A250 generation, UI/workflow

### Out of Scope

- Browser-based or web UI — requires access to UNC/mapped network paths (V:, W:)
- Installation package (MSI, setup.exe) — distribution via network share only
- macOS/Linux support — Windows-only (win32com shortcuts, mapped drives)
- Multi-user/server backend — standalone desktop app, no shared state

## Context

- Currently a Tkinter app distributed as a `--onefile` PyInstaller exe on a network share
- `--onefile` extracts the full bundle to a temp folder on every launch — painfully slow from a network share
- File operations (shutil copy, delete, win32com shortcut) run on the main UI thread, freezing the window
- Users are non-technical: error messages must be human-readable, no terminal windows, no stack traces
- The A250 form uses `docxtpl` to render a Word template — this dependency must be bundled in the exe

## Constraints

- **Distribution**: Standalone exe, no install requirements — PyInstaller `--onedir` bundle on network share
- **Network access**: Must read/write to UNC paths and mapped drives (V:, W:) — no sandbox or web container
- **Platform**: Windows only — `win32com` is a hard dependency for `.lnk` shortcut creation
- **Users**: Non-technical — UI must be self-explanatory, errors must be plain English

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PyQt6 over CustomTkinter | Richer UI capabilities, better long-term maintainability, more polished widgets | — Pending |
| --onedir over --onefile packaging | Eliminates temp extraction on every launch; near-instant startup from network share | — Pending |
| QThread for background operations | Keeps UI responsive during file copies; enables progress updates and cancellation | — Pending |
| Retain existing operation modules | `copy_ops`, `delete_ops`, `shortcut_ops` have clean interfaces — wrap, don't rewrite | — Pending |

---
*Last updated: 2026-03-31 after initialization*
