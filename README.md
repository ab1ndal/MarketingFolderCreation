# Project Folder Setup Tool

A PyQt6 GUI application that automates creation of structured project directories for both marketing (BD) and work drives at Nabih Youssef & Associates. Copies template folder structures, replaces the `1 Marketing` subfolder in the work tree with a shortcut pointing back to the BD drive, and can generate A250 fee proposal documents from a Word template.

---

## Folder Structure

```
MarketingFolderCreation/
├── app.py                     # Main GUI — FolderSetupApp window, WorkerThread, A250 dialog
├── config.py                  # Default path configuration (template/target defaults)
├── logger.py                  # Timestamped, color-coded log function
├── MarketingFolderCreation.spec  # PyInstaller spec (--onedir, production build)
├── templates/
│   └── A250.docx              # Word template for A250 fee proposals (docxtpl)
├── operations/
│   ├── copy_ops.py            # Folder copy via robocopy
│   ├── delete_ops.py          # Folder delete (robocopy mirror → shutil fallback)
│   └── shortcut_ops.py        # Windows .lnk shortcut creation via win32com
└── utils/
    └── validate.py            # Input path validation with PyQt6 error dialogs
```

---

## Running from Source

**1. Create and activate a virtual environment:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**2. Install dependencies:**

```bash
pip install -r requirements.txt
```

**3. Run the app:**

```bash
python app.py
```

**4. Use the GUI:**

- Enter the project folder name
- Adjust template and destination paths if needed (defaults load from `config.py`)
- Click **Run Folder Setup** to copy templates and create the shortcut
- Click **Create A250** to open the fee proposal form
- Click **Clear Log** to reset the log panel

---

## Running Tests

The test suite uses `pytest` and `pytest-qt`. All 47 tests run without real network drives — filesystem operations use `tmp_path` and win32com/robocopy calls are mocked where needed.

**Run all tests:**

```bash
python -m pytest tests/
```

**Run with coverage report:**

```bash
python -m pytest tests/ --cov=operations --cov=utils --cov=app --cov-report=term --cov-report=html
```

Coverage HTML report is written to `htmlcov/index.html`.

**Run a specific test file:**

```bash
python -m pytest tests/test_copy_ops.py -v
```

**Run only integration tests** (requires robocopy — skipped automatically if unavailable):

```bash
python -m pytest tests/test_integration.py -v
```

**Run tests excluding integration** (faster, no robocopy needed):

```bash
python -m pytest tests/ --ignore=tests/test_integration.py -v
```

See [`tests/test_directory.md`](tests/test_directory.md) for a description of every test.

---

## Packaging (Building the .exe)

The project uses a production PyInstaller `--onedir` spec. The output is a folder (not a single file), which gives faster startup and is the recommended distribution format.

**Prerequisites:**

```bash
pip install pyinstaller
```

**Build the bundle:**

```bash
pyinstaller MarketingFolderCreation.spec
```

Output: `dist/MarketingFolderCreation/`

**What gets bundled automatically:**
- All PyQt6 DLLs and platform plugins
- `templates/A250.docx` (resolved at runtime via `sys._MEIPASS`)
- win32com, docxtpl, and all other dependencies
- Application icon (`FolderCreatorTool.ico`)

**Distribute:** Copy the entire `dist/MarketingFolderCreation/` folder to the network share. Users double-click `MarketingFolderCreation.exe` — no Python installation required.

**Rebuild after code changes:**

```bash
pyinstaller MarketingFolderCreation.spec
```

PyInstaller overwrites `dist/MarketingFolderCreation/` on each build. The `build/` folder is intermediate and can be deleted safely.

---

## Further Development

### With Claude Code (AI-assisted)

The project uses [GSD](https://github.com/anthropics/claude-code) for structured development. The `.planning/` directory contains the roadmap, phase plans, and state.

**Check project status:**

```
/gsd:progress
```

**Start a new feature or fix:**

```
/gsd:quick <describe what you want to change>
```

**For larger changes, plan a new phase:**

```
/gsd:discuss-phase <N>
/gsd:plan-phase <N>
/gsd:execute-phase <N>
```

**Debug an issue:**

```
/gsd:debug
```

### Manual Development

**Key extension points:**

| What to change | Where |
|----------------|-------|
| Default drive paths | `config.py` |
| Folder copy flags (threads, retries) | `operations/copy_ops.py` |
| Delete strategy | `operations/delete_ops.py` |
| Shortcut target/icon | `operations/shortcut_ops.py` |
| Input validation rules | `utils/validate.py` |
| A250 form fields | `app.py` → `_open_a250_dialog()` and `_generate_a250()` |
| A250 template layout | `templates/A250.docx` (edit in Word; field names use `{{ variable }}` syntax) |
| GUI layout | `app.py` → `FolderSetupApp.__init__()` |

**Adding a new A250 field:**

1. Add a `QLineEdit` in `_open_a250_dialog()` in `app.py`
2. Add the matching `{{ field_name }}` placeholder to `templates/A250.docx`
3. Add a test in `tests/test_a250_generation.py` verifying the field appears in the render call

**Adding a new operation step to the workflow:**

1. Add a function in the relevant `operations/` module
2. Call it from `WorkerThread.run()` in `app.py`
3. Add unit tests in the matching `tests/test_*.py` file

**After any change, verify nothing broke:**

```bash
python -m pytest tests/
```

---

## Requirements

- Windows OS (robocopy and win32com shortcut creation are Windows-only)
- Python 3.10 or newer

---

## Author

Developed by Abhinav Bindal for internal automation of project directory setup at Nabih Youssef & Associates.
