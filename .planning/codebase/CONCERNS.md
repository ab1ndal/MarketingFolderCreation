# Codebase Concerns

**Analysis Date:** 2026-03-31

## Tech Debt

**Broad Exception Handling:**
- Issue: Bare `except Exception as e` blocks catch all exceptions without distinction, masking underlying issues
- Files: `app.py` (lines 114, 216), `operations/copy_ops.py` (line 20), `operations/delete_ops.py` (line 16), `operations/shortcut_ops.py` (line 13)
- Impact: Debugging is difficult; transient errors and critical failures are treated identically. Users see generic error messages without actionable information
- Fix approach: Replace with specific exception types (e.g., `FileNotFoundError`, `PermissionError`, `OSError`). Provide context-specific error messages to users

**Unused Import and Dead Code:**
- Issue: `logger.log` function imported in multiple modules but never called; instead, modules pass `log_func` parameter. The module-level `log()` function in `logger.py` is unused
- Files: `logger.py` (function definition), imports in `operations/copy_ops.py` (line 2), `operations/delete_ops.py` (line 4), `operations/shortcut_ops.py` (line 1)
- Impact: Code confusion, maintenance burden, unclear logging strategy. The actual logging happens via callback functions, not the imported `log` module
- Fix approach: Remove unused `log()` function from `logger.py` and clean up unused imports. Document logging strategy: callbacks are the standard pattern

**Hardcoded Template Path:**
- Issue: Template path `templates/A250.docx` is hardcoded in `app.py` line 103, assumes template exists in working directory. No validation that file exists
- Files: `app.py` (line 103)
- Impact: A250 generation silently fails if template is missing or working directory is wrong. No user feedback about path issues
- Fix approach: Store template path in `config.py` alongside other defaults. Validate template existence before document generation. Make configurable via UI

**Print Statement in Production Code:**
- Issue: Debug print statement left in `app.py` line 186 outputs paths dictionary to console
- Files: `app.py` (line 186)
- Impact: Clutters console output during normal operation. May leak sensitive internal state in logs
- Fix approach: Remove or replace with proper debug logging that can be toggled

**Missing Logging File Persistence:**
- Issue: Log output exists only in UI (in-memory ScrolledText widget); logs are lost when application closes
- Files: `app.py` (self.log_text widget)
- Impact: No audit trail, difficult to debug issues that occurred during previous sessions, unable to track project creation history
- Fix approach: Implement file-based logging alongside UI logging. Write logs to `.log` file with rotation policy

## Known Bugs

**Logger Function Mismatch:**
- Symptoms: `logger.py` defines `log(window, message, level)` that expects a window object with a specific interface. This function is never called in codebase; all logging uses `log_func` callbacks instead
- Files: `logger.py` (lines 3-7), called nowhere
- Trigger: Function exists but unreachable from production code
- Workaround: Current system works via callbacks; unused function can be ignored but causes confusion

**A250 Generation Missing Error Recovery:**
- Symptoms: `generate_a250()` catches generic Exception and shows to user via messagebox, but also logs to UI. No distinction between template validation errors, write permission errors, or data rendering errors
- Files: `app.py` (lines 96-115)
- Trigger: Missing template, invalid data, no write permissions
- Workaround: Users must manually verify template exists and that `templates/` directory is accessible

## Security Considerations

**Command Injection via File Paths:**
- Risk: File paths from user input (via `browse_folder` dialog) are directly passed to `shutil.copytree()` and other operations without sanitization. Malicious paths could potentially exploit symlinks or junction points
- Files: `app.py` (lines 158-161), `operations/copy_ops.py` (lines 5-20)
- Current mitigation: Validation checks only that paths exist; no checks for symlinks or suspicious structure
- Recommendations: Add validation to reject symlinks in source/destination paths. Use `Path.resolve()` to eliminate relative path traversal. Add checks for system-critical directories (Windows, Program Files, etc.) to prevent accidental deletion

**Plaintext Path Storage in Config:**
- Risk: Network paths (M:\, V:\, W:\) containing organizational data structure are stored in plaintext in `config.py`, which is version-controlled
- Files: `config.py` (all lines)
- Current mitigation: File is accessible only to developers with repo access
- Recommendations: Move default paths to environment variables or a local (non-versioned) config file. Keep `config.py` as a template with placeholder values

**Windows Shortcut Elevation Risk:**
- Risk: `create_shortcut()` creates shortcuts without validation of target permissions. Created shortcuts may require elevated privileges that end-user doesn't have, or may point to inaccessible network paths
- Files: `operations/shortcut_ops.py` (lines 3-14)
- Current mitigation: Function logs errors if shortcut creation fails
- Recommendations: Validate target path is accessible before creating shortcut. Test shortcut creation with current user privileges. Document privilege requirements

**Unvalidated File Operations on Network Paths:**
- Risk: Operations assume network paths (V:\ and W:\) are always available. If network is disconnected, copy/delete operations may hang or fail ungracefully
- Files: `operations/copy_ops.py`, `operations/delete_ops.py`, `operations/shortcut_ops.py`
- Current mitigation: Basic exception handling in each function
- Recommendations: Add network availability check before operations. Set connection timeout for network path access. Provide user feedback for network-related failures

## Performance Bottlenecks

**Synchronous UI Blocking:**
- Problem: Large folder copies block UI thread completely. Progress bar updates only after copy completes
- Files: `app.py` (lines 177-217), `operations/copy_ops.py` (line 18)
- Cause: `shutil.copytree()` is synchronous and blocks event loop. `self.root.update()` at line 175 is insufficient for responsive UI
- Improvement path: Move copy/delete/shortcut operations to background thread using `threading.Thread`. Update progress bar via thread-safe queue. Keep UI responsive during long operations

**File Copy Has No Progress Feedback:**
- Problem: For large folders (100+ GB), copy operation shows no intermediate progress; users see frozen UI for minutes
- Files: `operations/copy_ops.py` (lines 17-20)
- Cause: `shutil.copytree()` provides no callback mechanism for progress
- Improvement path: Implement custom recursive copy with file-level progress callbacks. Update UI progress bar per file rather than per operation

**Path Validation on Every Operation:**
- Problem: `validate_paths()` checks existence of all 4 paths, but paths don't change after validation. Called once per workflow, so not critical, but inefficient pattern
- Files: `utils/validate.py` (lines 3-7), called at `app.py` line 187
- Cause: No caching of validation results
- Improvement path: Cache validation results per workflow session. Re-validate only if user changes paths via UI

## Fragile Areas

**Hardcoded Year Calculation:**
- Files: `app.py` (line 33), `app.py` (lines 38-39)
- Why fragile: Current year is computed once at app initialization. If app runs past midnight or across year boundary, paths may be inconsistent
- Safe modification: Compute year dynamically at operation time, not initialization time. Pass current year to operations as parameter
- Test coverage: No tests for year boundary conditions; no tests for leap year edge cases

**Folder Deletion Without Confirmation:**
- Files: `app.py` (line 204), `operations/delete_ops.py` (lines 11-19)
- Why fragile: Deletes `1 Marketing` folder with no user confirmation. If config value changes or paths are wrong, user could accidentally delete important data
- Safe modification: Add confirmation dialog before deletion. Display what will be deleted. Allow user to preview folder contents before deletion
- Test coverage: No tests for deletion workflow; no dry-run mode to test paths before actual deletion

**Tightly Coupled Config and Behavior:**
- Files: `config.py` (hardcoded network paths), `app.py` (lines 35-40)
- Why fragile: Changing default paths in config requires code modification and venv reactivation. No runtime configuration override mechanism
- Safe modification: Support environment variables or config file override. Allow CLI arguments or config file to override defaults
- Test coverage: No automated tests for configuration loading; no validation that defaults are sensible

**Missing A250 Template Validation:**
- Files: `app.py` (line 103), `templates/A250.docx` (exists but not validated)
- Why fragile: Template path is hardcoded string; if file missing or corrupted, function fails silently with generic exception
- Safe modification: Load and validate template structure at app startup. Check that template has expected placeholders before user attempts generation
- Test coverage: No tests for A250 workflow; no tests for missing/invalid template

## Scaling Limits

**Single-Threaded Copy Operations:**
- Current capacity: Folder copy speed limited by single-thread I/O, typically 100-500 MB/s depending on network
- Limit: User cannot perform other actions while copying large folders (500 GB+). UI becomes unresponsive for 10+ minutes
- Scaling path: Implement multi-threaded or async copy with worker pool. Consider using `concurrent.futures.ThreadPoolExecutor` for parallel file operations

**In-Memory Log Widget:**
- Current capacity: ScrolledText widget can store ~100,000 lines before performance degrades
- Limit: Very large projects with many operations may cause memory bloat. No automatic log rotation
- Scaling path: Implement rolling file logger. Keep only recent N entries in UI. Archive older logs to file

**Network Path Dependency:**
- Current capacity: Assumes single network drive configuration (V:\ and W:\)
- Limit: If organization adds new network drives or changes drive letters, config must be manually updated
- Scaling path: Support multiple destination configurations. Allow user to select from available network paths at runtime

## Dependencies at Risk

**PyWin32 Windows-Only Dependency:**
- Risk: Application completely depends on `pywin32` for shortcut creation. If package becomes unmaintained or has security vulnerabilities, no fallback exists
- Impact: Cannot create shortcuts on non-Windows systems. If pywin32 has breaking changes, app is broken
- Migration plan: Evaluate `pathlib.Path` alternatives or OS-agnostic methods. Consider fallback to batch file or VBScript approach if import fails

**Pyperclip Platform Dependency:**
- Risk: Clipboard operations may fail on some systems (SSH sessions, restricted environments). No handling for clipboard unavailability
- Impact: "Copy to clipboard" silently fails without user notification
- Migration plan: Wrap pyperclip in try-except. Provide fallback (e.g., show path in dialog) if clipboard not available

**DocxTemplate Without Version Pin:**
- Risk: `requirements.txt` lists `docxtpl` without version pin. Major version updates could break template rendering
- Impact: A250 generation may break silently if dependency auto-updates
- Migration plan: Pin all dependencies to specific versions. Add version constraints with upper bounds (e.g., `docxtpl>=0.16,<1.0`)

## Missing Critical Features

**Dry-Run Mode:**
- Problem: Users cannot preview what will be created without actually creating it. No way to test configuration before committing
- Blocks: Users cannot safely test new configurations; no way to validate paths without real consequences
- Recommendation: Implement `--dry-run` flag that shows what would be created/deleted without modifying filesystem

**Undo/Rollback:**
- Problem: Once folders are created and files copied, there is no undo. If user accidentally runs workflow twice, second run skips copy but user has no record of what happened
- Blocks: Users cannot recover from mistakes; incomplete operations cannot be rolled back
- Recommendation: Implement transaction-style operations. Create manifest file listing all files created. Provide "undo last operation" feature

**Configuration Persistence:**
- Problem: UI defaults always come from hardcoded config.py. User customizations made in UI are lost when app closes
- Blocks: Users must re-enter custom paths every session
- Recommendation: Save UI state (paths, last used values) to JSON config file. Load on app startup

## Test Coverage Gaps

**No Tests for Folder Copy Operations:**
- What's not tested: `copy_folder()` function with various source types (empty folders, nested structures, symbolic links, permission errors)
- Files: `operations/copy_ops.py`
- Risk: Regression in copy logic could silently fail for edge cases. Large folder copies untested
- Priority: High - core functionality

**No Tests for Folder Deletion:**
- What's not tested: `delete_folder()` with read-only files, symbolic links, in-use files, permission denied scenarios
- Files: `operations/delete_ops.py`
- Risk: Data loss possible if deletion fails unexpectedly on read-only files. Symlink handling untested
- Priority: High - data deletion is critical

**No Tests for Shortcut Creation:**
- What's not tested: `create_shortcut()` with long paths, special characters, invalid targets, permission errors
- Files: `operations/shortcut_ops.py`
- Risk: Shortcuts may fail silently; no validation that created shortcuts are functional
- Priority: Medium - non-critical feature

**No Tests for UI Workflow:**
- What's not tested: Full end-to-end workflow (input validation → copy → delete → shortcut → success). Error states, user input validation
- Files: `app.py` (FolderSetupApp class)
- Risk: UI bugs discovered only in manual testing. Regression in workflow logic undetected
- Priority: Medium - integration testing needed

**No Tests for A250 Generation:**
- What's not tested: Template rendering, missing template handling, invalid data, file write failures
- Files: `app.py` (generate_a250 method)
- Risk: A250 functionality completely untested. Template compatibility unknown with docxtpl version changes
- Priority: Medium - feature added but never validated

**No Tests for Path Validation:**
- What's not tested: `validate_paths()` with non-existent paths, symbolic links, inaccessible network paths, drive disconnections
- Files: `utils/validate.py`
- Risk: Validation logic may be insufficient; edge cases cause failures during operation
- Priority: Low - basic function but edge cases matter

---

*Concerns audit: 2026-03-31*
