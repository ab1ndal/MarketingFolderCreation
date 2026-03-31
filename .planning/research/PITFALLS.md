# Pitfalls Research: PyQt6 Migration + PyInstaller Packaging

**Research Date:** 2026-03-31
**Domain:** PyQt6 migration from Tkinter, QThread, PyInstaller --onedir, pytest-qt

---

## Critical Pitfalls (Must Address Before Launch)

### 1. QThread Garbage Collection Crashes
**What goes wrong:** Workers get garbage collected before completing — silent data loss or random crashes mid-operation.
**Why:** QRunnable/QThread stored as local variables go out of scope while still running.
**Prevention:** Store all workers as instance variables on the Presenter; use QThreadPool.globalInstance() to manage lifecycle.
**Detection:** Random crashes on second/third run, not reproducible consistently.
**Phase:** PyQt6 Migration (worker implementation)

---

### 2. PyInstaller --onefile Startup from Network Share
**What goes wrong:** 15–30 second startup because --onefile extracts the entire bundle to a temp folder on every launch; over a network share this is extremely slow.
**Why:** PyInstaller's --onefile mode bundles everything into a single exe that self-extracts to `%TEMP%` at runtime.
**Prevention:** Use `--onedir` exclusively. The folder bundle is pre-extracted — startup is near-instant even from a network share.
**Detection:** Time `app.exe` launch from `\\server\tools\` vs local copy. Should be <3s with --onedir.
**Phase:** Packaging (must verify from actual network share location)

---

### 3. win32com + PyQt6 Plugin Bundling Failures
**What goes wrong:** Exe crashes on first run: "No module named win32com.shell" or "Could not find platform plugin 'windows'".
**Why:** PyInstaller can't detect dynamic imports in win32com or Qt platform plugins without explicit hints.
**Prevention:**
```
--hidden-import win32com.shell
--hidden-import win32com.shell.shell
--hidden-import win32timezone
--add-binary "venv/Lib/site-packages/PyQt6/Qt6/plugins/platforms/qwindows.dll;PyQt6/Qt6/plugins/platforms"
```
**Detection:** Test the bundled exe on a machine with no Python installed.
**Phase:** Packaging

---

### 4. Blocking Main UI Thread
**What goes wrong:** File operations freeze the UI; window shows "Not Responding"; Cancel button does nothing.
**Why:** All shutil.copy / os operations run on the Qt main thread.
**Prevention:** Move ALL file ops to QRunnable workers. Never call shutil/os from any method connected to a widget signal.
**Detection:** Run folder setup — window should remain responsive and draggable throughout.
**Phase:** PyQt6 Migration

---

## Moderate Pitfalls

### 5. Signal/Slot Thread Safety
**What goes wrong:** Crash when worker emits signal that directly updates a widget.
**Why:** Qt widgets can only be touched from the main thread.
**Prevention:** Always connect worker signals to slots on the main thread. Qt's default queued connection handles this automatically when signals cross thread boundaries.
**Phase:** PyQt6 Migration

---

### 6. UNC Path Handling
**What goes wrong:** `copy_folder` fails on V:/W: drives; paths corrupted or not recognized.
**Why:** Mapped drive letters and UNC paths need consistent handling; `os.path` and `pathlib` behave differently for UNC paths.
**Prevention:** Use `pathlib.Path` throughout (Python 3.10+). Test with actual V:/W: drives early — local C: drive testing masks these bugs.
**Detection:** Run full workflow pointing at actual network targets, not local temp dirs.
**Phase:** PyQt6 Migration (test on real paths, not just tmp_path fixtures)

---

### 7. PyQt6 Enum Naming Changes (PyQt5 → PyQt6)
**What goes wrong:** `AttributeError: type object 'Qt' has no attribute 'AlignLeft'` — short-form enum names removed.
**Why:** PyQt6 requires fully-qualified enum access: `Qt.AlignmentFlag.AlignLeft` not `Qt.AlignLeft`.
**Prevention:** Use IDE with PyQt6 stubs; run linter. Never copy-paste PyQt5 snippets without checking enum names.
**Phase:** PyQt6 Migration

---

### 8. docxtpl Data File Missing from Bundle
**What goes wrong:** A250 generation crashes in the exe: "template not found" or "No such file: templates/A250.docx".
**Why:** PyInstaller doesn't bundle non-Python files unless explicitly told to.
**Prevention:**
```python
# In spec file:
datas=[('templates/A250.docx', 'templates')]
```
Then use `sys._MEIPASS` to resolve paths at runtime.
**Phase:** Packaging

---

### 9. pytest-qt Configuration
**What goes wrong:** Tests fail intermittently or hang when run together.
**Why:** Multiple QApplication instances, or tests not using `qtbot` fixture for event loop management.
**Prevention:** Never create `QApplication` manually in tests. Always use `qtbot` fixture from pytest-qt. Add `qt_api = pyqt6` to `pytest.ini`.
**Phase:** Testing

---

## Phase Mapping Summary

| Phase | Critical Actions |
|-------|-----------------|
| **PyQt6 Migration** | QThread workers (pitfalls 1, 4, 5); UNC path testing (6); PyQt6 enum syntax (7) |
| **Packaging** | --onedir (2); hidden imports for win32com + Qt plugins (3); docxtpl data files (8) |
| **Testing** | pytest-qt setup (9); test on real network paths not just tmp_path |

---

## Sources

- [Real Python: PyQt QThread](https://realpython.com/python-pyqt-qthread/)
- [Python GUIs: PyQt6 Multithreading](https://www.pythonguis.com/tutorials/multithreading-pyqt6-applications-qthreadpool/)
- [PyInstaller 6.x Documentation](https://pyinstaller.org/en/stable/)
- [pytest-qt Documentation](https://pytest-qt.readthedocs.io/en/latest/intro.html)
- [Qt Documentation: Threads and QObjects](https://doc.qt.io/qt-6/threads-qobject.html)
- [Python GUIs: PyQt5 vs PyQt6 Migration](https://www.pythonguis.com/faq/pyqt5-vs-pyqt6/)

---
*Research: 2026-03-31*
