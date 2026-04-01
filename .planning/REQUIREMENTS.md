# Requirements: Marketing Folder Creation Tool — v2

**Defined:** 2026-03-31
**Core Value:** Non-technical users can set up a project in seconds, from any machine, without touching file paths or knowing anything about the underlying file system.

## v1 Requirements

### Performance

- [ ] **PERF-01**: App starts in under 3 seconds when launched from a network share (switch from PyInstaller --onefile to --onedir)
- [x] **PERF-02**: UI remains responsive and interactive during all file operations (folder copy, delete, shortcut creation run in background thread via QThreadPool)
- [x] **PERF-03**: BD template copy and Work template copy run in parallel (simultaneous, not sequential) to reduce total setup time
- [ ] **PERF-04**: Folder copy uses optimized I/O (buffered shutil or robocopy subprocess) for faster transfer over network drives

### UI Modernization

- [x] **UI-01**: Application is fully migrated from Tkinter to PyQt6 with a clean, professional layout
- [x] **UI-02**: Progress bar displays plain-English step descriptions during workflow (e.g. "Copying BD template...", "Creating shortcut...")
- [x] **UI-03**: All error conditions display human-readable dialog messages — no stack traces, no technical jargon visible to users

### Core Workflow (Existing — must continue working)

- [x] **WF-01**: User can enter a project name and run folder setup to copy BD template to V: drive target
- [x] **WF-02**: User can run folder setup to copy work template to W: drive target
- [x] **WF-03**: Folder setup deletes the "1 Marketing" subfolder from the work folder
- [x] **WF-04**: Folder setup creates a Windows shortcut (.lnk) from the work folder to the BD folder
- [x] **WF-05**: Work folder path is copied to clipboard after successful setup
- [x] **WF-06**: User can browse and select custom template and target paths via native Windows file dialogs
- [x] **WF-07**: User can open the A250 form, fill all fields, and generate a Word document from the template

### Testing

- [ ] **TEST-01**: Unit tests cover copy_folder with mock filesystem (success, source missing, destination exists)
- [ ] **TEST-02**: Unit tests cover delete_folder with mock filesystem (success, read-only files, folder missing)
- [ ] **TEST-03**: Unit tests cover create_shortcut with mocked win32com (success, invalid paths)
- [x] **TEST-04**: Unit tests cover validate_paths for all validation cases (missing paths, empty project name)
- [x] **TEST-05**: Unit tests cover A250 generation: correct fields rendered, output file created, template missing error
- [ ] **TEST-06**: UI/workflow integration tests via pytest-qt: user fills project name, clicks Run, correct folder structure created on filesystem

### Packaging

- [ ] **PKG-01**: Application distributed as a PyInstaller --onedir bundle (folder with exe + DLLs, no extraction on launch)
- [ ] **PKG-02**: Bundle includes all dependencies (PyQt6, win32com, docxtpl, A250 template) — no Python install required on target machine

## v2 Requirements

### UX Polish

- **UX-01**: Dark/light mode toggle or system theme detection
- **UX-02**: Cancel running operation mid-workflow
- **UX-03**: Remember last-used paths across sessions (QSettings)
- **UX-04**: Keyboard shortcut to run workflow (Enter key)

### Advanced Features

- **ADV-01**: Searchable/filterable log output
- **ADV-02**: Settings dialog to adjust default paths without editing config file
- **ADV-03**: Toast notification on successful completion

## Out of Scope

| Feature | Reason |
|---------|--------|
| Browser-based UI | App requires access to UNC/mapped network paths (V:, W:) |
| Installation package (MSI) | Distribution via network share as folder bundle only |
| macOS/Linux support | Windows-only — win32com shortcuts, mapped drive letters |
| Undo/rollback | High complexity, low value for this linear workflow |
| Real-time folder monitoring | Out of scope |
| Multi-language support | Not needed for current audience |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PERF-01 | Phase 3: Packaging | Pending |
| PERF-02 | Phase 1: Threading | Complete |
| PERF-03 | Phase 1: Threading | Complete |
| PERF-04 | Phase 1: Threading | Pending |
| UI-01 | Phase 2: UI Migration | Complete |
| UI-02 | Phase 2: UI Migration | Complete |
| UI-03 | Phase 2: UI Migration | Complete |
| WF-01 | Phase 1: Threading | Complete |
| WF-02 | Phase 1: Threading | Complete |
| WF-03 | Phase 1: Threading | Complete |
| WF-04 | Phase 1: Threading | Complete |
| WF-05 | Phase 2: UI Migration | Complete |
| WF-06 | Phase 2: UI Migration | Complete |
| WF-07 | Phase 2: UI Migration | Complete |
| TEST-01 | Phase 4: Testing | Pending |
| TEST-02 | Phase 4: Testing | Pending |
| TEST-03 | Phase 4: Testing | Pending |
| TEST-04 | Phase 2: Testing | Complete |
| TEST-05 | Phase 2: Testing | Complete |
| TEST-06 | Phase 4: Testing | Pending |
| PKG-01 | Phase 3: Packaging | Pending |
| PKG-02 | Phase 3: Packaging | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-04-01 — TEST-04 and TEST-05 complete (Phase 2 Plan 02)*
