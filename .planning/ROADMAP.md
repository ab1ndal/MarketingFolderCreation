# Roadmap: Marketing Folder Creation Tool — v2

**Project:** Marketing Folder Creation Tool v2 (Tkinter → PyQt6 Modernization)
**Status:** In planning
**Created:** 2026-03-31
**Granularity:** Coarse (3 phases)
**Coverage:** 22/22 v1 requirements mapped

---

## Phases

- [ ] **Phase 1: PyQt6 Infrastructure & Threading** - Build worker/signal threading foundation, keep workflow working, eliminate UI freezing
- [ ] **Phase 2: UI Migration & Features** - Modernize UI from Tkinter to PyQt6, implement file dialogs, deliver user-facing improvements
- [ ] **Phase 3: Packaging & Deployment** - Production-ready exe, network share startup optimization, bundling validation

---

## Phase Details

### Phase 1: PyQt6 Infrastructure & Threading

**Goal:** Establish responsive application foundation with background worker threads, eliminate UI freezing during file operations, prove threading architecture before UI investment.

**Depends on:** None (foundation phase)

**Requirements:**
- PERF-02, PERF-03, PERF-04
- WF-01, WF-02, WF-03, WF-04, WF-05
- TEST-01, TEST-02, TEST-03

**Success Criteria** (what must be TRUE when this phase completes):
1. User can run folder setup workflow and UI remains responsive (no freezing) during copy/delete/shortcut operations
2. Folder copy and work copy operations run in parallel to each other, not sequentially
3. Folder copy uses buffered I/O or robocopy for faster transfer over network paths
4. All unit tests for copy_folder, delete_folder, and create_shortcut pass with mock filesystem, covering success and error cases
5. Worker can be cancelled mid-operation and application continues running without crash on subsequent operations

**Plans:** 2/3 plans executed

Plans:
- [ ] 01-PLAN-01.md — Fix operation modules (copy_ops, delete_ops, shortcut_ops) to pass all 32 unit tests
- [ ] 01-PLAN-02.md — Create WorkflowWorker QThread with parallel copy and cancellation support
- [ ] 01-PLAN-03.md — Rewrite app.py as PyQt6 main window wired to WorkflowWorker

---

### Phase 2: UI Migration & Features

**Goal:** Deliver modern, responsive user experience with PyQt6 widgets, user-friendly file dialogs, and clear progress feedback that non-technical users can follow.

**Depends on:** Phase 1 (requires worker/threading infrastructure)

**Requirements:**
- UI-01, UI-02, UI-03
- WF-06, WF-07
- TEST-04, TEST-05, TEST-06

**Success Criteria** (what must be TRUE when this phase completes):
1. Application is fully migrated from Tkinter to PyQt6; old Tkinter imports removed, no legacy widgets visible
2. Progress bar displays plain-English step descriptions (e.g., "Copying BD template...", "Creating shortcut...") during workflow execution
3. All error conditions show human-readable dialog messages with no stack traces, technical jargon, or terminal output visible to users
4. User can browse and select custom template and target paths using native Windows file dialogs (QFileDialog)
5. User can open A250 form, fill all fields, and generate a Word document from template successfully
6. UI/workflow integration tests pass, confirming user can fill project name, click Run, and correct folder structure is created on filesystem

**Plans:** 1/3 plans executed

Plans:
- [ ] 02-01-PLAN.md — UI polish: progress step label, error dialogs, A250 save_location fix (UI-01, UI-02, UI-03, WF-06, WF-07)
- [ ] 02-02-PLAN.md — Unit tests for validate_paths and A250 generation (TEST-04, TEST-05)
- [ ] 02-03-PLAN.md — pytest-qt integration tests: fill→run→filesystem workflow (TEST-06)

---

### Phase 3: Packaging & Deployment

**Goal:** Ship production-ready executable with instant startup from network shares and all dependencies bundled, no Python installation required on user machines.

**Depends on:** Phase 1 (threading), Phase 2 (UI stability)

**Requirements:**
- PERF-01
- PKG-01, PKG-02

**Success Criteria** (what must be TRUE when this phase completes):
1. Application starts in under 3 seconds when launched from network share (V: drive) measured from exe invocation to UI fully rendered
2. PyInstaller --onedir bundle is created with all dependencies (PyQt6, win32com, docxtpl, A250 template) included; no Python installation required on target machine
3. Bundled exe runs successfully on clean test machine without Python, handling UNC paths (V:, W:) and network drive access correctly
4. Hidden imports (win32com.shell, win32com.shell.shell, win32timezone) and platform plugin dlls are correctly bundled for reliable startup
5. A250 template is bundled in exe and resolved at runtime; Word document generation works from bundled template

**Plans:** TBD

---

## Progress Tracking

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. PyQt6 Infrastructure & Threading | 2/3 | In Progress|  |
| 2. UI Migration & Features | 1/3 | In Progress|  |
| 3. Packaging & Deployment | 0/? | Not started | — |

---

## Requirement Traceability

| Requirement | Phase | Type |
|-------------|-------|------|
| PERF-01 | Phase 3 | Performance |
| PERF-02 | Phase 1 | Performance |
| PERF-03 | Phase 1 | Performance |
| PERF-04 | Phase 1 | Performance |
| UI-01 | Phase 2 | UI |
| UI-02 | Phase 2 | UI |
| UI-03 | Phase 2 | UI |
| WF-01 | Phase 1 | Workflow |
| WF-02 | Phase 1 | Workflow |
| WF-03 | Phase 1 | Workflow |
| WF-04 | Phase 1 | Workflow |
| WF-05 | Phase 1 | Workflow |
| WF-06 | Phase 2 | Workflow |
| WF-07 | Phase 2 | Workflow |
| TEST-01 | Phase 1 | Testing |
| TEST-02 | Phase 1 | Testing |
| TEST-03 | Phase 1 | Testing |
| TEST-04 | Phase 2 | Testing |
| TEST-05 | Phase 2 | Testing |
| TEST-06 | Phase 2 | Testing |
| PKG-01 | Phase 3 | Packaging |
| PKG-02 | Phase 3 | Packaging |

**Coverage:** 22/22 v1 requirements mapped, 0 orphaned

---

*Roadmap created: 2026-03-31*
*Last updated: 2026-03-31 — Phase 2 plans defined (3 plans)*
