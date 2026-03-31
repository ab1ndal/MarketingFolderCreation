# External Integrations

**Analysis Date:** 2026-03-31

## APIs & External Services

**Windows COM Interoperability:**
- WScript.Shell (via pywin32) - Creates Windows shortcuts (.lnk files)
  - SDK/Client: `win32com.client` (from pywin32 package)
  - Usage: `operations/shortcut_ops.py` - `create_shortcut()` function dispatches WScript.Shell to create shortcuts linking folders
  - Authentication: None - uses system-level COM access

## Data Storage

**Databases:**
- None - No database integration

**File Storage:**
- Local filesystem and Network-attached storage
  - Template sources: `M:\Project Folder Templates\...` (network drive)
  - BD/Marketing destination: `V:\\` (network drive)
  - Work destination: `W:\\` (network drive)
  - Client: Direct filesystem operations via Python `pathlib` and `shutil`
  - Operations: `operations/copy_ops.py` (copy_folder), `operations/delete_ops.py` (delete_folder)

**Document Templates:**
- Word document files (.docx) stored on local M: drive
  - Template path: `templates/A250.docx` (for A250 form generation)
  - Client: `docxtpl.DocxTemplate` for template rendering
  - Workflow: User inputs data in GUI form → docxtpl renders Word template → saves output .docx

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- Custom Windows file system permissions
  - Implementation: No explicit auth layer - relies on OS-level file access control for network drives
  - User must have read access to M: drive (templates) and write access to V: and W: drives (targets)

## Monitoring & Observability

**Error Tracking:**
- None - No external error tracking service

**Logs:**
- Local console and in-app GUI log display
  - Approach: Custom logging via `logger.py` - log() function writes to GUI log panel with timestamps and status symbols
  - Output: ScrolledText widget in Tkinter window shows real-time operation status

## CI/CD & Deployment

**Hosting:**
- Windows desktop/network environment
- Distribution: Standalone executable via PyInstaller

**CI Pipeline:**
- None detected

## Environment Configuration

**Required env vars:**
- None explicitly - all configuration is in `config.py` (hardcoded paths)

**Secrets location:**
- No secrets management - all paths are configured in `config.py`

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## System Integration Points

**Clipboard Integration:**
- `pyperclip` - Clipboard access for copying folder paths
  - Location: `app.py` - `run_workflow()` method copies work target folder path to clipboard after successful setup

**Shortcut Creation:**
- Windows COM/WScript.Shell - Creates .lnk file for easy folder access
  - Location: `operations/shortcut_ops.py` - `create_shortcut()` creates shortcut linking BD target folder
  - Target path: Saved to `work_target / {FOLDER_TO_DELETE}.lnk`

**File System Permissions:**
- Windows OS-level permissions for read-only file handling
  - Location: `operations/delete_ops.py` - `handle_remove_readonly()` clears read-only bits before deletion
  - Fallback: Uses `os.chmod()` with `stat.S_IWRITE` to override read-only attributes

## Network Dependencies

**Required Network Paths:**
- `M:\Project Folder Templates\...` - Source templates (must be accessible)
- `V:\\` - Marketing/BD destination drive (must be writable)
- `W:\\` - Work destination drive (must be writable)

**Validation:**
- `utils/validate.py` - `validate_paths()` checks existence of all configured paths before operations begin

---

*Integration audit: 2026-03-31*
