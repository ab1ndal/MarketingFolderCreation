# Project Research Summary

**Project:** Marketing Folder Creation Tool — v2 (Tkinter → PyQt6 Modernization)
**Domain:** Desktop file operations UI for non-technical Windows users
**Researched:** 2026-03-31
**Confidence:** HIGH

## Executive Summary

The Marketing Folder Creation Tool should undergo a modernization from Tkinter to PyQt6, eliminating the fundamental single-threaded architecture limitation that causes UI freezing during file operations. PyQt6 provides native Windows widgets, proper multithreading via QThreadPool/QRunnable, and thread-safe signal/slot communication — transforming a frustrating user experience into a responsive, professional desktop application. The existing business logic (copy/delete/shortcut operations) is sound and should be preserved; modernization focuses on the GUI framework and threading model, not workflow redesign.

The key risk is proper implementation of Qt's threading patterns. Workers must be stored as instance variables (not garbage collected mid-operation), signals must never be called directly from worker threads, and UI updates must always flow through the presenter layer. Failing to follow these patterns leads to hard-to-debug crashes and data loss. This modernization should be tackled in three phases: (1) PyQt6 infrastructure + worker threading, (2) UI layer migration with full feature parity, and (3) production packaging and validation.

Success hinges on using `--onedir` PyInstaller mode for instant startup from network shares, aggressive testing of UNC/mapped drive paths (which behave differently than local paths), and validation that the bundled exe works on machines without Python installed. The research identifies specific hidden imports and build configuration required for reliable cross-platform deployment.

## Key Findings

### Recommended Stack

PyQt6 is the clear choice over Tkinter or custom alternatives. Qt6 bindings provide native Windows widgets, vastly superior layout management, and built-in multithreading infrastructure. The stack emphasizes reusing existing business logic while modernizing the presentation layer.

**Core technologies:**
- **PyQt6 6.11.0+**: Modern Qt6 bindings with native Windows rendering, QThreadPool for background work, and thread-safe signal/slot communication. Vastly superior to Tkinter's single-threaded architecture.
- **Python 3.13+**: Latest runtime with improved pathlib UNC path handling — critical for mapped drives (V:/W:).
- **QThreadPool + QRunnable**: Built into PyQt6; manages worker threads for all file I/O, keeping the main UI thread responsive.
- **pywin32 (win32com)**: Only reliable way to create Windows .lnk shortcuts programmatically — no alternatives exist.
- **docxtpl 0.20.x**: Jinja2-based Word doc generation. **CRITICAL:** python-docx pinned at 1.1.0 (1.1.1+ breaks docxtpl compatibility).
- **PyInstaller 6.19.0+ with --onedir**: Bundles as a pre-extracted folder for instant startup from network shares. Avoids 15–30 second startup penalty of --onefile mode.

**Critical dependency:** `python-docx==1.1.0` must be pinned; do not upgrade without testing docxtpl compatibility first.

### Expected Features

The modernization must preserve all current functionality while introducing responsive UI patterns. Research identified distinct tiers of importance.

**Must have (table stakes):**
- Non-blocking UI during file operations (users expect responsiveness after Tkinter's freezing)
- Progress feedback (progress bar or spinner showing work is happening)
- Cancellation support (user can stop running operations mid-workflow)
- Plain-English error messages (no stack traces; users expect clarity)
- Windows-native file dialogs (QFileDialog matching OS conventions users recognize)

**Should have (competitive differentiators):**
- Dark/light mode toggle (QApplication palette — modern UX expectation)
- Keyboard shortcuts (Enter to run, Escape to cancel — power user productivity)
- Clipboard copy after success (convenient for downstream use)
- Tooltips on inputs (helps non-technical users understand fields)

**Defer to v2+ (nice-to-have):**
- Searchable operation log (auditing feature)
- Path memory via QSettings (convenience, not critical)
- Settings dialog (advanced users can edit config files initially)

### Architecture Approach

Recommended pattern: **Model-View-Presenter (MVP)** with **QThreadPool workers**. This cleanly separates business logic from UI, enables testing without a window, and properly handles threading boundaries.

**Major components:**
1. **Operations layer** (`operations/` — preserve existing) — File system operations (copy, delete, shortcut creation) with logging callback support
2. **Workers** (`workers/` — new QRunnable subclasses) — Background tasks wrapping operations; emit progress/completion signals
3. **Model** (`model.py` — new) — Business state and decision logic; issues commands to workers
4. **Presenter** (`presenter.py` — new) — Orchestrates workers, wires UI signals to model, updates view from signals
5. **View** (`ui/` — new PyQt6 widgets) — Pure widgets with no logic; all user actions emit signals

**Data flow:** User action → View signal → Presenter → Model/Worker (QThreadPool) → Progress signal → Presenter → View update. All cross-thread communication uses Qt queued connections, which are thread-safe by default.

### Critical Pitfalls

**1. QThread Garbage Collection Crashes** — Workers stored as local variables get garbage collected while still running, causing silent data loss or random crashes. **Prevention:** Store all workers as instance variables on the Presenter; use `QThreadPool.globalInstance()` to manage lifecycle.

**2. PyInstaller --onefile Startup Penalty** — --onefile extracts the entire bundle to %TEMP% on every launch, causing 15–30 second startup from network shares. **Prevention:** Use `--onedir` exclusively; pre-extracted folder enables near-instant startup.

**3. win32com + PyQt6 Plugin Bundling Failures** — Exe crashes on first run with "No module named win32com.shell" or "Could not find platform plugin" because PyInstaller can't detect dynamic imports. **Prevention:** Explicitly add hidden imports (`--hidden-import win32com.shell --hidden-import win32com.shell.shell`) and platform plugin dll to bundle.

**4. Blocking Main UI Thread** — All file operations running on main thread freezes the window and makes Cancel button unresponsive. **Prevention:** Move ALL file ops to QRunnable workers; never call shutil/os from any method connected to a widget signal.

**5. Signal/Slot Thread Safety** — Crashing when worker emits signal that directly updates a widget (can only be touched from main thread). **Prevention:** Always connect worker signals to slots on main thread; Qt's default queued connection handles thread safety automatically.

## Implications for Roadmap

Research reveals clear phase dependencies: threading infrastructure must come first (it unblocks UI work), followed by UI migration, then production packaging. This ordering avoids rework and limits blast radius of threading complexity.

### Phase 1: PyQt6 Infrastructure + Worker Threading
**Rationale:** Threading is the fundamental problem with Tkinter. Building worker/signal infrastructure first unblocks UI development and proves the architecture works before investing in full UI migration.

**Delivers:**
- QThreadPool + QRunnable worker pattern
- WorkerSignals (progress, finished, error)
- Presenter layer wiring workers to model
- Unit tests for worker behavior

**Addresses features:**
- Non-blocking UI (table stakes)
- Progress feedback structure
- Cancellation support mechanism

**Avoids pitfalls:**
- QThread garbage collection (store workers as instance vars)
- Blocking main thread (all I/O in workers)
- Signal/slot thread safety (queued connections by default)

**Stack elements:**
- PyQt6 6.11.0+
- Python 3.13+
- QThreadPool (bundled)
- pyqtSignal (bundled)

**Testing:** pytest + pytest-qt with headless qtbot fixtures; integration tests with QCoreApplication (no window needed).

**Validation criteria:** Worker can copy a large folder, emit progress signals every 50MB, be cancelled mid-operation, and complete without crashing on second/third run.

---

### Phase 2: PyQt6 UI Migration + Features
**Rationale:** With threading proven, migrate the actual UI from Tkinter to PyQt6. This phase delivers visible user improvements and implements all table-stakes features.

**Delivers:**
- Modern PyQt6 widget layout (replacing Tkinter widgets)
- Progress bar + spinner during operations
- Plain-English error dialogs
- Windows-native file dialogs
- Cancellation button that actually works
- Keyboard shortcuts (Enter to run, Escape to cancel)

**Addresses features:**
- All "must have" table stakes
- Dark/light mode toggle (should have)
- Tooltips on inputs
- Clipboard copy on success

**Avoids pitfalls:**
- PyQt6 enum naming (use fully-qualified: `Qt.AlignmentFlag.AlignLeft`, not `Qt.AlignLeft`)
- UNC path handling (test with actual V:/W: drives, not just tmp_path fixtures)

**Stack elements:**
- PyQt6 widgets
- QFileDialog (native Windows dialogs)
- QApplication palette (dark/light mode)

**Implements architecture:**
- View layer (pure widgets)
- Presenter layer (event wiring)
- Model layer (business state)

**Testing:** pytest-qt with qtbot fixture; widget interaction tests; test on real UNC paths, not just local temp dirs.

**Validation criteria:** App opens/closes cleanly, folder setup remains responsive while copying, progress bar updates smoothly, cancel button stops operation immediately, no UI freezing observed.

---

### Phase 3: Packaging + Production Validation
**Rationale:** Final phase ensures the exe works for end users: reliable startup from network shares, works on machines without Python, and handles all deployment edge cases.

**Delivers:**
- `--onedir` PyInstaller bundle
- exe startup verified <3s from network share
- Hidden import + plugin dll bundling
- A250 Word template bundled and resolved at runtime
- pytest-qt configuration for CI/CD

**Addresses pitfalls:**
- PyInstaller --onefile startup penalty (use --onedir exclusively)
- win32com + Qt plugin bundling (explicit hidden imports + dll copy)
- docxtpl data file missing from bundle (datas parameter in spec)
- pytest-qt intermittent failures (qtbot fixture, qt_api=pyqt6 in pytest.ini)

**Stack elements:**
- PyInstaller 6.19.0+
- Hidden imports: `win32com.shell`, `win32com.shell.shell`, `win32timezone`
- Platform plugin dll: `PyQt6/Qt6/plugins/platforms/qwindows.dll`
- Data files: `templates/A250.docx`

**Testing:** Test bundled exe on machine without Python installed; time startup from `\\server\tools\` (should be <3s); verify A250 generation works; run full pytest suite.

**Validation criteria:** exe launches in <3s from network share, A250 generation works, all operations complete without errors, cancel button responsive, no "Not Responding" observed.

---

### Phase Ordering Rationale

1. **Phase 1 → Phase 2 → Phase 3** (strict dependency order)
   - Phase 1 proves threading works; Phase 2 builds UI on that foundation; Phase 3 packages for production.
   - Reverse order would mean discovering threading bugs after UI is complete, requiring major rework.

2. **Why this grouping mirrors architecture**
   - Phase 1 = Worker + Model layers
   - Phase 2 = View + Presenter layers + Feature integration
   - Phase 3 = Packaging + deployment validation

3. **Avoids pitfall blast radius**
   - If threading is broken, discover during Phase 1 (small scope) not Phase 2 (full UI)
   - Network path handling tested in Phase 2 (UI context) before packaging
   - Bundling issues isolated to Phase 3 (safe to iterate)

### Research Flags

**Phases likely needing deeper research during planning:**

- **Phase 3 (Packaging):** PyInstaller bundling is environment-dependent; needs hands-on testing with actual network share paths and test machines without Python. Hidden imports + plugin dll resolution can be finicky; recommend spike to verify bundle process before full development.

**Phases with standard patterns (skip dedicated research phase):**

- **Phase 1 (Threading):** QThreadPool + QRunnable is well-documented in Qt and community sources; patterns are established and proven.
- **Phase 2 (UI):** PyQt6 widgets and MVP architecture are standard patterns; IDE support + stubs provide immediate guidance.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | PyQt6 6.11.0+, Python 3.13+, QThreadPool, pywin32, docxtpl choices verified against official docs and community consensus. python-docx pinning requirement confirmed. |
| **Features** | HIGH | Research identified all table-stakes features; MVP prioritization clear from domain understanding (non-technical users, file operations). Feature dependencies mapped. |
| **Architecture** | HIGH | MVP + QThreadPool pattern is standard for PyQt apps; component boundaries well-defined; data flow clearly documented. Build order dependencies logical. |
| **Pitfalls** | HIGH | All 9 pitfalls mapped to specific phases; prevention strategies concrete and actionable. Sources include official Qt/PyInstaller docs and Real Python tutorials. |

**Overall confidence:** HIGH

All research questions answered with high-confidence sources. No contradictions between researchers. Stack, features, and architecture align cleanly.

### Gaps to Address

1. **UNC Path Edge Cases** — Research identifies that mapped drives (V:/W:) behave differently than local paths, but exact failure modes depend on target environment. **Handling:** In Phase 2, test folder setup against actual network targets (not just `tmp_path` fixtures). Add regression tests for any failures discovered.

2. **PyInstaller Bundling Environment Variance** — Hidden imports and dll locations can vary across development environments. **Handling:** In Phase 3, perform hands-on packaging spike before full development; document exact build process (Python version, venv setup, spec file parameters) so others can replicate.

3. **Performance Validation** — Research recommends <3s startup from network share, but actual time depends on network/hardware. **Handling:** In Phase 3, establish baseline times on target network; define acceptable thresholds before launch.

## Sources

### Primary (HIGH confidence)

- **PyQt6 Multithreading Guide (pythonguis.com)** — QThreadPool + QRunnable patterns, worker implementation, thread safety rules
- **Qt 6 Official Documentation** — QThreadPool, QRunnable, Qt signals/slots, thread safety guarantees
- **Real Python: PyQt QThread** — Practical threading pitfalls and solutions
- **PyInstaller 6.x Official Documentation** — --onedir vs --onefile, hidden imports, data bundling, spec files
- **pytest-qt Documentation** — qtbot fixture, headless testing, Qt event loop integration

### Secondary (MEDIUM confidence)

- **Python GUIs: PyQt5 vs PyQt6 Migration** — Enum naming changes, api compatibility notes
- **docxtpl 0.20.x + python-docx 1.1.0 Compatibility** — Version pinning requirement identified through integration testing guidance

### Tertiary (dependencies requiring validation)

- **win32com bundling with PyInstaller** — Requires hands-on testing during Phase 3 packaging spike
- **Network share startup performance** — Real-world timing validation needed in production environment

---

*Research completed: 2026-03-31*
*Ready for roadmap: yes*
