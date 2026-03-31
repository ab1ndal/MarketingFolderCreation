# Architecture Research: PyQt6 Migration

**Research Date:** 2026-03-31
**Domain:** PyQt6 desktop app with background threading + testable architecture

---

## Recommended Pattern: MVP + QThreadPool Workers

**Model-View-Presenter** layering separates business logic from UI. QThreadPool with QRunnable workers handles background file operations. Qt signals/slots provide thread-safe inter-component communication.

---

## Component Boundaries (6 Layers)

| Layer | Location | Responsibility |
|-------|----------|---------------|
| **View** | `ui/` | PyQt6 widgets only — no logic |
| **Presenter** | `presenter.py` | Workflow orchestration, signal connections |
| **Model** | `model.py` | Business logic, state management, signals |
| **Operations** | `operations/` | File system operations (existing modules — reuse) |
| **Workers** | `workers/` | QRunnable subclasses with WorkerSignals |
| **Configuration** | `config.py` | Constants, defaults (existing — reuse) |

---

## Data Flow

```
User action
  → View signal
    → Presenter
      → Model / Worker (QThreadPool)
        → Worker progress signal
          → Presenter (queued connection, thread-safe)
            → View update (progress bar, log)
        → Completion / error signal
          → Presenter → Model → View
```

All signals cross the thread boundary via Qt's **queued connections** — thread-safe by default.

---

## Worker Pattern

```python
class WorkerSignals(QObject):
    progress = pyqtSignal(int, str)   # (percent, message)
    finished = pyqtSignal()
    error = pyqtSignal(str)

class FolderSetupWorker(QRunnable):
    def __init__(self, params):
        super().__init__()
        self.signals = WorkerSignals()
        self.params = params
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            copy_folder(..., log_func=lambda msg, lvl: self.signals.progress.emit(pct, msg))
            if self._cancelled:
                return
            ...
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))
```

---

## Build Order (Phase Dependencies)

1. **Operations layer** — Ensure `copy_ops`, `delete_ops`, `shortcut_ops` accept a logging callback (already done ✓)
2. **Worker infrastructure** — QRunnable subclasses wrapping existing operations, WorkerSignals
3. **PyQt6 UI layer** — Pure widgets, no logic, all events emit signals
4. **Presenter** — Wires workers to UI signals/slots, handles cancellation
5. **Application entry point** — QApplication bootstrap, PyInstaller `--onedir` packaging

---

## Testing Architecture

- **Unit tests**: Operations modules tested with `tmp_path` fixtures (no UI needed)
- **Integration tests**: Workers tested with `QCoreApplication` (no window needed)
- **UI tests**: `pytest-qt` with `qtbot` fixture for widget interaction
- **A250 tests**: `docxtpl` rendering tested against known fixture data

---

## Critical Anti-Patterns

| Anti-Pattern | Consequence | Prevention |
|--------------|-------------|------------|
| Blocking main thread during I/O | UI freezes | Move ALL file ops to QRunnable workers |
| Direct GUI calls from worker thread | Crash / undefined behavior | Use signals only — never call widget methods from workers |
| Monolithic GUI class (Tkinter style) | Untestable, hard to maintain | Strict layer separation (MVP) |
| Shared mutable state between threads | Race conditions | Pass params at construction time, communicate via signals only |

---

## Sources

- [PyQt6 Multithreading with QThreadPool](https://www.pythonguis.com/tutorials/multithreading-pyqt6-applications-qthreadpool/)
- [MVP Pattern for PyQt GUI](https://medium.com/@mark_huber/a-clean-architecture-for-a-pyqt-gui-using-the-mvp-pattern-78ecbc8321c0)
- [Use PyQt's QThread to Prevent Freezing GUIs — Real Python](https://realpython.com/python-pyqt-qthread/)
- [Qt 6 QThreadPool Documentation](https://doc.qt.io/qt-6/qthreadpool.html)
- [pytest-qt Documentation](https://pytest-qt.readthedocs.io/en/latest/intro.html)

---
*Research: 2026-03-31*
