# Architecture

**Analysis Date:** 2026-03-31

## Pattern Overview

**Overall:** Layered MVC (Model-View-Controller) with separation of concerns into modular operation handlers.

**Key Characteristics:**
- Single monolithic entry point (`app.py`) orchestrating workflow
- UI layer decoupled from business logic through callback functions
- Operation modules handle discrete file system tasks independently
- Configuration centralized in `config.py` for easy path adjustments
- Windows-specific implementation (uses `win32com` for shortcuts)

## Layers

**Presentation (UI) Layer:**
- Purpose: Display GUI window, capture user input, show progress and logs
- Location: `app.py` - `FolderSetupApp` class
- Contains: Tkinter widgets, event handlers, UI state management
- Depends on: Configuration values, operation modules, validation utilities
- Used by: End user via GUI window

**Business Logic Layer:**
- Purpose: Execute folder operations (copy, delete, shortcut creation) with validation
- Location: `operations/` directory
- Contains: `copy_ops.py`, `delete_ops.py`, `shortcut_ops.py`
- Depends on: Standard library modules (shutil, os, stat), win32com for shortcuts
- Used by: `app.py` workflow orchestration

**Utility Layer:**
- Purpose: Support validation and helper functions
- Location: `utils/validate.py`
- Contains: Path validation logic
- Depends on: pathlib.Path
- Used by: `app.py` before executing operations

**Configuration Layer:**
- Purpose: Store default paths and constants for network drives and templates
- Location: `config.py`
- Contains: Default template paths, target drive paths, folder names to delete
- Depends on: None (pure constants)
- Used by: `app.py` initialization, operation functions

## Data Flow

**Primary Workflow:**

1. **Initialization**: `app.py` loads default paths from `config.py` and builds UI window
2. **User Input**: User enters project name and adjusts template/target paths via GUI
3. **Validation**: `validate_paths()` in `utils/validate.py` checks all paths exist
4. **Workflow Execution**: Three sequential operations with progress tracking:
   - `copy_folder()` copies marketing template to BD target (V: drive)
   - `copy_folder()` copies work template to Work target (W: drive)
   - `delete_folder()` removes "1 Marketing" folder from work folder
   - `create_shortcut()` creates shortcut from work folder to BD folder
5. **Progress Feedback**: Each operation updates progress bar (20% increments) and writes to log widget
6. **Clipboard**: Work folder path copied to clipboard for user convenience

**State Management:**
- UI state stored in `FolderSetupApp.paths` (StringVar dictionary) and `project_name` (StringVar)
- Progress tracked via `ttk.Progressbar` widget (`self.progress`)
- Logging captured in scrolled text widget (`self.log_text`)
- A250 form state stored in `self.a250_vars` dictionary for document generation

## Key Abstractions

**FolderSetupApp Class:**
- Purpose: Encapsulates all UI and workflow orchestration logic
- Location: `app.py` lines 23-223
- Pattern: Monolithic class with methods for UI building, path browsing, workflow execution
- Responsibilities: Build UI, handle user input, validate paths, orchestrate operations, display logs

**Operation Functions:**
- Purpose: Single-responsibility functions for discrete file system operations
- Examples: `copy_folder()`, `delete_folder()`, `create_shortcut()`
- Pattern: Each operation function takes source/destination paths and a logging callback
- Logging injection: All operations accept `log_func` parameter to write progress without knowing UI implementation

**Logging Callback Pattern:**
- Purpose: Decouple operation modules from UI implementation
- Usage: Operations call `log_func("message", "level")` instead of printing directly
- Benefit: Same operation code can write to GUI, file, or any logging destination

## Entry Points

**Main Entry Point:**
- Location: `app.py` lines 220-223
- Triggers: User runs `python app.py`
- Responsibilities: Create root Tk window and instantiate `FolderSetupApp`

**Workflow Trigger:**
- Location: `FolderSetupApp.run_workflow()` (lines 177-217)
- Triggers: User clicks "🚀 Run Folder Setup" button
- Responsibilities: Validate input, execute four operations sequentially, handle errors, update UI progress

**A250 Form Trigger:**
- Location: `FolderSetupApp.open_a250_form()` (lines 46-94)
- Triggers: User clicks "📄 Create A250" button
- Responsibilities: Open separate window, render form fields, generate Word document from template

## Error Handling

**Strategy:** Try-catch wrapping with user-facing error messages and logging

**Patterns:**
- Path validation before workflow: `validate_paths()` checks all inputs exist
- Operation-level error handling: Each operation in `operations/` catches exceptions and logs them
- Read-only file handling: `delete_ops.py` includes `handle_remove_readonly()` to handle Windows permission issues
- User notification: Critical errors shown via `messagebox.showerror()` modal dialogs
- Graceful degradation: Operations with errors don't stop the workflow (e.g., "Destination already exists" logs warning and skips)

## Cross-Cutting Concerns

**Logging:**
- Implemented via callback injection - operations accept `log_func` parameter
- UI writes to `self.log_text` widget with emoji symbols and timestamps
- Levels: "info" (🛠), "success" (✅), "error" (❌), "warn" (⚠️)

**Validation:**
- Path existence checked before workflow in `utils/validate.py`
- Individual operations validate their specific preconditions (source exists, destination doesn't)

**Authentication:**
- None - application relies on user's file system permissions on network drives (V:, W:)

**Progress Tracking:**
- Manual progress bar updates in workflow: 0% → 20% → 40% → 60% → 80% → 100%
- Progress bar visual feedback for multi-step operations

---

*Architecture analysis: 2026-03-31*
