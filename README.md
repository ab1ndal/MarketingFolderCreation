# Project Folder Setup Tool

A PyQt6 GUI application that automates creation of structured project directories for both marketing (BD) and work drives at Nabih Youssef & Associates. Copies template folder structures, replaces the `1 Marketing` subfolder in the work tree with a shortcut pointing back to the BD drive, and can generate A250 fee proposal documents from a Word template. Supports **Segment mode** for nesting sub-project numbers (`NNNNN.XX`) under an existing primary project folder.

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
    ├── validate.py            # Input path validation with PyQt6 error dialogs
    ├── segment.py             # Segment mode: year derivation + primary-folder matching
    └── pathcheck.py           # Projects deepest path length to warn near Windows MAX_PATH
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

## Segment Mode

Normal runs create one top-level folder per year: `V:\<year>\<name>` (BD) and `W:\<year>\<name>` (Work). A **segment** is a sub-project number like `12345.01`, `12345.10`, or `12345.BD` that should nest under the existing primary project instead of getting its own top-level folder.

**How to use it:**

1. Check **Create a Segment**.
2. Type the full segment folder name (e.g. `12345.01 - Foundation Package`) in the project name field.
3. The tool scans the BD Target (`V:\<year>`) for primary folders whose leading number matches (`12345`) and fills the **Primary Folder** dropdown:
   - one match → auto-selected;
   - several → pick one;
   - none → an inline message appears and **Run** is blocked.
4. A note under the target fields shows the full nested destination.
5. **Run Folder Setup** creates `V:\<year>\<primary>\<segment>` and `W:\<year>\<primary>\<segment>`, running the same copy / `1 Marketing` swap / shortcut steps one level deeper.

**Year is derived from the project number, not the current date.** The first two digits map to a year using a pivot on the current 2-digit year: `yy <= current` → `20yy`, otherwise `19yy` (e.g. `25045` → 2025, `02031` → 2002, `89045` → 1989). On name blur, the derived year replaces the `<year>` segment in both target-path fields, in normal and segment mode.

**Primary folder** must already exist on the BD drive (the scan guarantees this). If it is missing under `W:\<year>`, the tool logs a warning and creates it during the copy — it does not block.

### Path-length warning

Segment nesting pushes the copied template subfolders deeper, closer to Windows' 260-character `MAX_PATH` limit. Before creating anything, the tool projects the deepest resulting path (target base + the deepest subpath inside the template) for each drive. If it exceeds `260 − PATH_LENGTH_MARGIN`, a **Yes/No** dialog warns you — it never blocks. Choosing **Yes** proceeds; **No** cancels so you can shorten the name first.

**Adjusting how often the warning fires** — edit `PATH_LENGTH_MARGIN` in `config.py`:

- The warning triggers when the projected path is longer than `260 − PATH_LENGTH_MARGIN`.
- **Decrease** the buffer → higher trigger point → **fewer** warnings. Example: `40` warns only past ~220 characters.
- **Increase** the buffer → **more** warnings, reserving more headroom for files added inside the folders later.
- Default is `100` (warns past ~160 characters). The buffer is advisory only; you can always proceed.

---

## Running Tests

The test suite uses `pytest` and `pytest-qt`. All tests run without real network drives — filesystem operations use `tmp_path` and win32com/robocopy calls are mocked where needed.

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
| Path-length warning buffer (`PATH_LENGTH_MARGIN`) | `config.py` |
| Year-derivation / primary-folder matching | `utils/segment.py` |
| Path-length projection logic | `utils/pathcheck.py` |
| Folder copy flags (threads, retries) | `operations/copy_ops.py` |
| Delete strategy | `operations/delete_ops.py` |
| Shortcut target/icon | `operations/shortcut_ops.py` |
| Input validation rules | `utils/validate.py` |
| A250 form fields | `app.py` → `A250_FIELD_GROUPS` (drives both the form and the preview) and `_open_a250_form()` |
| A250 composite / date / fee logic | `utils/a250_context.py` → `build_a250_context()` (shared by preview and generation) |
| A250 live preview pane | `app.py` → `_render_preview_html()` / `_refresh_preview()` |
| A250 template layout | `templates/A250.docx` (edit in Word; field names use `{{ variable }}` syntax) |
| GUI layout | `app.py` → `FolderSetupApp.__init__()` |

**A250 live preview:** The form is a split pane — fields on the left, a read-only
preview on the right that updates ~300 ms after you stop typing. It shows every field's
resolved value plus the derived composites (`requested_by`, `invoice_to`, `client_signed`)
and the formatted `fee`, so you can see exactly what the document will contain before
generating it. Plain fields update via change signals; the Quill rich-text editors push
changes through a `QWebChannel` bridge (`utils/web_editor.py` + `assets/editor.html`).

**Adding a new A250 field:**

1. Add a `(key, "Label")` entry to the relevant group in `A250_FIELD_GROUPS` in `app.py`
   (a `QLineEdit` unless the key is in `COMBO_FIELDS` / `MULTILINE_FIELDS` / `RICH_TEXT_FIELDS`)
2. Add the matching `{{ field_name }}` placeholder to `templates/A250.docx`
3. Add a test in `tests/test_a250_generation.py` verifying the field appears in the render call
4. The field appears in the live preview automatically — the preview reads the same
   `A250_FIELD_GROUPS` list that builds the form

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
