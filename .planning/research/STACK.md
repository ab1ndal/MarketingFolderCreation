# Technology Stack

**Project:** Marketing Folder Creation Tool — v2 (Tkinter → PyQt6 Modernization)
**Researched:** 2026-03-31
**Confidence:** HIGH

---

## Recommended Stack

| Layer | Technology | Version | Why | Confidence |
|-------|-----------|---------|-----|-----------|
| GUI Framework | **PyQt6** | 6.11.0+ | Modern Qt6 bindings; QThreadPool prevents UI freezing; native Windows widgets | HIGH |
| Python Runtime | **Python** | 3.13+ | Current version; improved pathlib UNC path handling | HIGH |
| Background Ops | **QThreadPool + QRunnable** | bundled with PyQt6 | Manages worker threads for file ops; keeps UI responsive | HIGH |
| Thread Comms | **pyqtSignal** | bundled with PyQt6 | Thread-safe progress/completion updates from workers to UI | HIGH |
| Windows Shortcuts | **pywin32** (win32com) | 308+ | Only way to create .lnk files on Windows | HIGH |
| Path Handling | **pathlib** | 3.13+ stdlib | Handles UNC/mapped drive paths; use throughout | MEDIUM |
| File Operations | **shutil** | 3.13+ stdlib | Already in use; no issues with network paths via pathlib | HIGH |
| Word Templates | **docxtpl** | 0.20.x | Jinja2-based Word doc generation; pin python-docx==1.1.0 | MEDIUM |
| python-docx | **python-docx** | **1.1.0 (pinned)** | CRITICAL: 1.1.1+ breaks docxtpl compatibility | MEDIUM |
| Clipboard | **pyperclip** | 1.11.0+ | Stable, cross-platform clipboard; no external deps on Windows | HIGH |
| Packaging | **PyInstaller** | 6.19.0+ | --onedir mode; instant startup from network share | HIGH |
| Testing | **pytest + pytest-qt** | pytest 7.4+, pytest-qt 4.2+ | Headless PyQt6 widget testing via qtbot fixture | HIGH |

---

## Critical Version Pin

```
python-docx==1.1.0   # DO NOT upgrade — 1.1.1+ breaks docxtpl
```

---

## Alternatives Rejected

| Category | Rejected | Reason |
|----------|----------|--------|
| GUI | CustomTkinter | Still inherits Tkinter's single-threaded architecture; no real fix for UI freezing |
| GUI | PySide6 | Also excellent, but PyQt6 has longer history; use if licensing becomes an issue |
| Packaging | --onefile | Extracts to temp on every launch — 2–10 sec penalty from network share |
| Packaging | cx_Freeze | Less mature PyQt6 hook ecosystem |
| Threading | Raw QThread | QThreadPool simpler for short, independent tasks (copy/delete/shortcut) |

---

## PyInstaller Build Notes

Required hidden imports for bundling:
```
--hidden-import win32com.shell
--hidden-import win32com.shell.shell
--hidden-import win32timezone
```

Data files to include:
```python
datas=[('templates/A250.docx', 'templates')]
```

Runtime path resolution (use inside exe):
```python
import sys, os
base = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
template_path = os.path.join(base, 'templates', 'A250.docx')
```

---

## requirements.txt

```
PyQt6==6.11.0
pywin32==308
docxtpl==0.20.3
python-docx==1.1.0
pyperclip==1.11.0

# Dev/test only
pytest==7.4.0
pytest-qt==4.2.0
```

---

## Sources

- [PyQt6 Multithreading with QThreadPool](https://www.pythonguis.com/tutorials/multithreading-pyqt6-applications-qthreadpool/)
- [Packaging PyQt6 for Windows with PyInstaller](https://www.pythonguis.com/tutorials/packaging-pyqt6-applications-windows-pyinstaller/)
- [Qt for Python Deployment Guide](https://doc.qt.io/qtforpython-6/deployment/deployment-pyinstaller.html)
- [PyInstaller 6.x Documentation](https://pyinstaller.org/en/stable/)
- [pytest-qt Documentation](https://pytest-qt.readthedocs.io/en/latest/intro.html)

---
*Research: 2026-03-31*
