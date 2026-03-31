# Codebase Structure

**Analysis Date:** 2026-03-31

## Directory Layout

```
MarketingFolderCreation/
├── app.py                      # Main GUI application (Tkinter entry point)
├── config.py                   # Default configuration (paths, constants)
├── logger.py                   # Logging utility (currently unused - legacy)
├── requirements.txt            # Python dependencies (pywin32, pyperclip, docxtpl)
├── README.md                   # Project documentation
├── operations/                 # Business logic for file operations
│   ├── __init__.py
│   ├── copy_ops.py             # Folder copying logic
│   ├── delete_ops.py           # Folder deletion with permission handling
│   └── shortcut_ops.py         # Windows shortcut creation (win32com)
├── utils/                      # Utility functions and helpers
│   ├── __init__.py
│   └── validate.py             # Path validation logic
├── templates/                  # Document templates for Word generation
│   └── A250.docx               # A250 form template (docxtpl)
├── build/                      # PyInstaller build artifacts (auto-generated)
├── dist/                       # Compiled executable output (auto-generated)
├── __pycache__/                # Python cache (auto-generated)
└── .git/                       # Version control metadata
```

## Directory Purposes

**Root Level:**
- Purpose: Python package root with main application entry point
- Contains: Application modules, configuration, dependencies manifest
- Key files: `app.py`, `config.py`, `requirements.txt`

**operations/**
- Purpose: Modular business logic for discrete file system operations
- Contains: Copy, delete, and shortcut creation functionality
- Key files: `copy_ops.py`, `delete_ops.py`, `shortcut_ops.py`

**utils/**
- Purpose: Reusable utility functions and validation helpers
- Contains: Input validation logic
- Key files: `validate.py`

**templates/**
- Purpose: Document templates for automated generation
- Contains: Word document templates for A250 forms
- Key files: `A250.docx`

**build/** and **dist/**
- Purpose: PyInstaller compilation output (distributable executables)
- Generated: Yes (from `pyinstaller` command)
- Committed: No (included in `.gitignore`)

## Key File Locations

**Entry Points:**
- `app.py`: Main application entry point - instantiates Tk window and FolderSetupApp class

**Configuration:**
- `config.py`: Centralized path constants for template locations and network drive targets
- `requirements.txt`: Python package dependencies

**Core Logic:**
- `operations/copy_ops.py`: Recursively copies folder structures using `shutil.copytree()`
- `operations/delete_ops.py`: Recursively deletes folders with read-only file handling
- `operations/shortcut_ops.py`: Creates Windows `.lnk` shortcuts using `win32com.client`
- `utils/validate.py`: Validates that all paths exist before workflow execution

**Testing:**
- No test files present - application lacks unit tests

**UI Implementation:**
- `app.py`: Contains `FolderSetupApp` class with full Tkinter GUI (lines 23-223)

## Naming Conventions

**Files:**
- Lowercase with underscores: `copy_ops.py`, `shortcut_ops.py`, `validate.py`
- Module names reflect functionality: `*_ops.py` for operations, `*_utils.py` or just module name for utilities
- Configuration file: `config.py`
- Main entry point: `app.py`

**Functions:**
- Lowercase with underscores: `copy_folder()`, `delete_folder()`, `create_shortcut()`, `validate_paths()`
- Private/helper functions use underscore prefix: `handle_remove_readonly()` (callback helper)
- GUI methods use descriptive names: `build_ui()`, `run_workflow()`, `open_a250_form()`, `browse_folder()`

**Variables:**
- Instance variables: camelCase with `self.` prefix: `self.paths`, `self.project_name`, `self.log_text`, `self.a250_vars`
- StringVar containers: Dictionaries mapping keys to Tkinter StringVar: `self.paths = {"marketing_template": tk.StringVar()}`
- Local variables: lowercase with underscores: `data`, `output_path`, `template_path`, `current_year`

**Types:**
- No explicit type hints in codebase (Python 3.8+ style not adopted)
- Pathlib `Path` objects preferred over strings: `Path(src)`, `Path(dst)`

## Where to Add New Code

**New Feature - Folder Operations:**
- Primary code: Create new file in `operations/` directory following naming pattern `operation_name_ops.py`
- Example: `operations/rename_ops.py` for folder renaming
- Pattern: Export single function accepting paths and `log_func` callback: `def rename_folder(src, dst, log_func):`
- Integration point: Import and call from `FolderSetupApp.run_workflow()` in `app.py`

**New Feature - Document Generation:**
- Primary code: Extend `FolderSetupApp` class in `app.py`
- Example: Add new method like `open_a250_form()` (already present at lines 46-94)
- Pattern: Create Toplevel window with form fields, use `DocxTemplate` to render and save
- Integration point: Add button in `build_ui()` method to trigger new form dialog

**New Validation Logic:**
- Implementation: Add function to `utils/validate.py`
- Example: `validate_folder_name()`, `validate_year_format()`
- Integration point: Call from `FolderSetupApp.run_workflow()` before operations

**New Configuration:**
- Implementation: Add constant to `config.py`
- Pattern: UPPERCASE_CONSTANT_NAME following existing convention
- Usage: Import in `app.py` and use in initialization or workflow

**Utilities:**
- Shared helpers: Place in `utils/` directory
- Pattern: One function per utility module or group related functions in single module
- Current: Only `validate.py` present with `validate_paths()` function

## Special Directories

**operations/**
- Purpose: Contains file system operation modules
- Generated: No
- Committed: Yes
- Pattern: Each operation is self-contained function accepting logging callback for UI-agnostic design

**utils/**
- Purpose: Contains validation and helper functions
- Generated: No
- Committed: Yes
- Pattern: Utility functions with no side effects

**templates/**
- Purpose: Contains document templates for Word document generation
- Generated: No (created manually or from Word)
- Committed: Yes
- Contains: `A250.docx` - Word template with merge fields for A250 form (referenced in `app.py` lines 103-110)

**build/** and **dist/**
- Purpose: PyInstaller output directories for standalone executable creation
- Generated: Yes (from `pyinstaller` command)
- Committed: No (in `.gitignore`)
- Output files: `ClickFolder.exe` created from `pyinstaller --onefile --windowed --name ClickFolder --icon=FolderCreatorTool.ico app.py`

## Module Import Structure

**app.py imports:**
- Tkinter: `tk`, `filedialog`, `ttk`, `scrolledtext`, `messagebox`
- External: `pathlib.Path`, `pyperclip`, `datetime`, `docxtpl.DocxTemplate`
- Internal: `config`, `logger`, `operations/copy_ops`, `operations/delete_ops`, `operations/shortcut_ops`, `utils/validate`

**operations modules import:**
- Standard library: `shutil`, `os`, `stat`, `pathlib.Path`
- External: `win32com.client` (only in `shortcut_ops.py`)
- Internal: `logger` (legacy - imported but not used)

**utils modules import:**
- Standard library: `pathlib.Path`
- No external dependencies

---

*Structure analysis: 2026-03-31*
