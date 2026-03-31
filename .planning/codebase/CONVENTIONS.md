# Coding Conventions

**Analysis Date:** 2026-03-31

## Naming Patterns

**Files:**
- Lowercase with underscores for multi-word files: `copy_ops.py`, `shortcut_ops.py`, `validate.py`
- Main application file: `app.py`
- Configuration file: `config.py`
- Logging utility: `logger.py`

**Functions:**
- snake_case for all function names
- Examples: `copy_folder()`, `delete_folder()`, `create_shortcut()`, `validate_paths()`, `open_a250_form()`, `browse_folder()`
- Descriptive action-based naming: functions begin with verb (copy, delete, create, validate, build)

**Variables:**
- snake_case for local variables and instance attributes
- UPPERCASE for constants in `config.py`: `DEFAULT_MARKETING_TEMPLATE`, `DEFAULT_WORK_TEMPLATE`, `DEFAULT_BD_TARGET`, `DEFAULT_WORK_TARGET`, `FOLDER_TO_DELETE`
- Dictionary keys in lowercase with underscores: `'marketing_template'`, `'work_template'`, `'bd_target'`, `'work_target'`
- Emoji usage in UI strings: `"📁 Project Folder Setup Tool"`, `"🚀 Run Folder Setup"` in `app.py`

**Classes:**
- PascalCase for class names: `FolderSetupApp`
- Single main class for GUI application

**Type Hints:**
- Not consistently used. Function parameters lack type hints except in `validate.py` where `paths: dict` is used
- Return types are not annotated

## Code Style

**Formatting:**
- No explicit formatter detected in configuration (no `.prettierrc` or similar)
- Indentation: 4 spaces (Python standard)
- Line length: No strict limit enforced; lines vary from 50-100+ characters

**Linting:**
- No linting configuration detected (no `.flake8`, `pylintrc`, or `pyproject.toml`)
- Code follows general Python conventions but without strict enforcement

## Import Organization

**Order:**
1. Standard library imports (tkinter, pathlib, os, shutil, stat, datetime)
2. Third-party imports (pyperclip, docxtpl, pywin32/win32com)
3. Local application imports (config, logger, operations modules, utils modules)

**Path Aliases:**
- No path aliases configured
- Absolute imports from project root: `from config import ...`, `from operations.copy_ops import ...`, `from utils.validate import ...`
- Local module imports use relative paths within packages

**Example from `app.py`:**
```python
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
from pathlib import Path
import pyperclip
from datetime import datetime
from docxtpl import DocxTemplate

from config import (
    DEFAULT_MARKETING_TEMPLATE,
    DEFAULT_WORK_TEMPLATE,
    DEFAULT_BD_TARGET,
    DEFAULT_WORK_TARGET,
    FOLDER_TO_DELETE
)
from logger import log
from operations.copy_ops import copy_folder
from operations.delete_ops import delete_folder
from operations.shortcut_ops import create_shortcut
from utils.validate import validate_paths
```

## Error Handling

**Patterns:**
- Try-except blocks for file operations and external calls
- Broad exception catching: `except Exception as e:` in most functions
- Errors logged via `log_func()` parameter passed to utility functions
- GUI errors shown via `messagebox.showerror()` for user-facing operations
- No custom exception classes used

**Examples:**
- `copy_ops.py` line 17-20: Copy operation wrapped in try-except with conditional existence checks
- `shortcut_ops.py` line 4-14: Shortcut creation wrapped in try-except
- `delete_ops.py` line 11-19: Deletion wrapped in try-except with special handler for read-only files
- `app.py` line 96-115: A250 generation wrapped in try-except

## Logging

**Framework:** Custom wrapper around GUI operations

**Patterns:**
- Logging function signature: `log_func(message: str, level: str)`
- Levels used: `"info"`, `"success"`, `"error"`, `"warn"`
- Emoji indicators for each level: `"✅"` (success), `"❌"` (error), `"⚠️"` (warn), `"🛠"` (info)
- Logging is passed as parameter to utility functions: `log_func` callback pattern
- Timestamp included in logger but not currently used in `app.py` version (logger.py has timestamp logic but app.py implements its own)

**Current usage in `app.py`:**
```python
def write_log(self, message, level="info"):
    symbol = {"info": "🛠", "success": "✅", "error": "❌", "warn": "⚠️"}.get(level, "🛠")
    line = f"{symbol} {message}\n"
```

## Comments

**When to Comment:**
- Function documentation absent (no docstrings)
- Inline comments minimal
- Code is self-documenting through function names

**Docstrings:**
- No docstrings present in any functions
- No JSDoc/TSDoc equivalents (Python doesn't use these)

## Function Design

**Size:**
- Functions vary from 5-60 lines
- Most utility functions are short (< 20 lines)
- Main application class methods range from 20-80 lines

**Parameters:**
- Utility functions accept explicit parameters: source, destination, log function
- GUI methods access instance variables directly via `self`
- String variables pattern: functions receive data directly, not wrapped in objects

**Return Values:**
- Utility functions in `operations/` return nothing (`None`), use callbacks for logging
- Validation function returns boolean: `validate_paths()` returns `True` or `False`
- Most operations use side effects and logging callbacks rather than return values

## Module Design

**Exports:**
- No explicit `__all__` definitions
- All public functions imported directly: `from operations.copy_ops import copy_folder`
- `__init__.py` files present but empty in `operations/` and `utils/` directories

**Barrel Files:**
- Not used; modules imported directly from their source files

## Constants and Configuration

**Configuration Location:**
- All application constants centralized in `config.py`: `DEFAULT_MARKETING_TEMPLATE`, `DEFAULT_WORK_TEMPLATE`, `DEFAULT_BD_TARGET`, `DEFAULT_WORK_TARGET`, `FOLDER_TO_DELETE`
- Configuration values use raw strings for Windows paths: `r"M:\..."`
- Current year calculated at runtime in `app.py`: `datetime.now().year`

---

*Convention analysis: 2026-03-31*
