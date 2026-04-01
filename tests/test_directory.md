# Test Directory

Overview of every test in the suite. All tests run with `python -m pytest tests/`.

---

## conftest.py — Shared Fixtures

Not a test file. Defines fixtures available to all test modules:

| Fixture | What it provides |
|---------|-----------------|
| `temp_dir` | A fresh `tmp_path` as a `Path` object; cleaned up after each test |
| `mock_log_func` | A `Mock()` standing in for the app's `log()` function; lets tests assert log messages without a real GUI |
| `sample_folder` | A pre-built source tree under `temp_dir`: 2 files, a `subdir/`, and a `deep/nested/folder/` — used by copy tests |
| `mock_robocopy_success` | Patches `subprocess.run` to return robocopy exit code `1` (files copied successfully) |
| `mock_win32com` | Patches `win32com.client.Dispatch` and returns a dict of `{dispatch, shell, shortcut}` mocks for shortcut tests |

---

## test_copy_ops.py — `copy_folder()`

Tests the robocopy-based folder copy in `operations/copy_ops.py`.

| Test | What it checks |
|------|---------------|
| `test_copy_folder_success` | Happy path: robocopy returns exit code 1, result is `True`, log messages are correct, robocopy is called with `/E /MT:16 /R:5` |
| `test_copy_folder_source_missing` | Source path does not exist → returns `False`, logs an error |
| `test_copy_folder_dest_exists` | Destination already exists → returns `False`, logs a warning (no overwrite) |
| `test_copy_folder_robocopy_returns_no_files` | Exit code 0 (nothing to copy, already in sync) → still returns `True`, logs "in sync" message |
| `test_copy_folder_robocopy_warnings` | Exit code 3 (files copied with warnings) → returns `True` (treat as success) |
| `test_copy_folder_robocopy_failure` | Exit code 16 (fatal error) → returns `False`, logs exit code and stderr |
| `test_copy_folder_robocopy_timeout` | `TimeoutExpired` raised → returns `False`, logs timeout message |
| `test_copy_folder_robocopy_not_found` | `FileNotFoundError` raised → returns `False`, logs "robocopy not found" |
| `test_copy_folder_general_exception` | Unexpected exception → returns `False`, logs the exception message |
| `test_copy_folder_with_unc_paths` | Source/dest are UNC paths (`\\server\share\...`) → robocopy called with the UNC strings unchanged |
| `test_copy_folder_with_network_mapped_drive` | Source/dest are mapped drives (`V:/`, `W:/`) → robocopy called with mapped drive paths |

---

## test_delete_ops.py — `delete_folder()`, helpers

Tests the two-stage delete strategy in `operations/delete_ops.py`: robocopy mirror first, shutil fallback second.

| Test | What it checks |
|------|---------------|
| `test_delete_folder_success` | Folder exists and is deleted → returns `True`, folder gone from disk, logs success |
| `test_delete_folder_missing` | Folder does not exist → returns `False`, logs a warning |
| `test_delete_folder_uses_robocopy_first` | Confirms robocopy mirror is attempted before shutil |
| `test_delete_folder_fallback_to_shutil` | When robocopy mirror returns `False`, shutil retry is called and result is `True` |
| `test_robocopy_mirror_success` | `delete_with_robocopy_mirror()` calls robocopy with `/MIR` flag and returns `True` on exit code 1 |
| `test_robocopy_mirror_failure` | Exit code 16 → returns `False` |
| `test_robocopy_mirror_exception` | Exception during robocopy → returns `False`, logs warning |
| `test_shutil_retry_success` | `delete_with_shutil_retry()` removes folder successfully |
| `test_shutil_retry_with_readonly_files` | Handles read-only files (chmod) — clears them and deletes |
| `test_shutil_retry_permission_error` | Fails first 2 attempts with `PermissionError`, succeeds on 3rd — confirms retry logic |
| `test_shutil_retry_all_fail` | All retry attempts fail → returns `False`, logs error with reason |

---

## test_shortcut_ops.py — `create_shortcut()`

Tests Windows `.lnk` shortcut creation in `operations/shortcut_ops.py` using the `mock_win32com` fixture.

| Test | What it checks |
|------|---------------|
| `test_create_shortcut_success` | Happy path: `Dispatch("WScript.Shell")` called, `Targetpath`/`WorkingDirectory`/`IconLocation` set, `save()` called, logs success |
| `test_create_shortcut_with_file_target` | Target is a file (not a folder) → `WorkingDirectory` set to the file's parent |
| `test_create_shortcut_with_unc_path` | Target is a UNC path → `Targetpath` preserves UNC format |
| `test_create_shortcut_with_network_mapped_drive` | Target is a mapped drive path → passes through unchanged |
| `test_create_shortcut_win32com_import_error` | `win32com` not importable → returns `False`, logs "pywin32 required" |
| `test_create_shortcut_com_failure` | `Dispatch()` raises an exception → returns `False`, logs error |
| `test_create_shortcut_save_failure` | `shortcut.save()` raises `PermissionError` → returns `False`, logs error |
| `test_create_shortcut_invalid_path` | `CreateShortCut()` raises an exception (invalid chars) → returns `False`, logs error |
| `test_create_shortcut_with_long_paths` | 200-character path name → passes through without truncation |

---

## test_validate_paths.py — `validate_paths()`

Tests input validation in `utils/validate.py`. The function checks that each path exists and shows a `QMessageBox.critical` dialog on failure.

| Test | What it checks |
|------|---------------|
| `test_all_paths_exist_returns_true` | All four paths exist → returns `True`, no dialog, no log call |
| `test_missing_path_returns_false_and_shows_dialog` | One path missing → returns `False`, dialog shown once with human-readable label |
| `test_missing_path_calls_log_func` | Missing path → `log_func` called with label in message |
| `test_empty_string_path_returns_false` | Empty string path → returns `False` |
| `test_each_key_shows_correct_label` (parametrized × 4) | Each of the 4 path keys maps to the correct human label: "BD Template", "Work Template", "BD Target (V:)", "Work Target (W:)" |
| `test_stops_at_first_failure` | Two bad paths → dialog shown exactly once (short-circuits after first failure) |

---

## test_a250_generation.py — `FolderSetupApp._generate_a250()`

Tests A250 fee proposal document generation in `app.py`. All tests patch `DocxTemplate` to avoid needing the real Word template on disk.

| Test | What it checks |
|------|---------------|
| `test_render_called_with_all_fields` | `doc.render()` is called with a dict containing `project_title` and `current_date`; `project_title` value matches input |
| `test_output_filename_uses_project_title` | `doc.save()` is called with a path that contains the project title and ends in `.docx` |
| `test_save_location_used_when_provided` | When `save_location` field is filled, the output file is saved inside that directory |
| `test_save_location_blank_falls_back_to_cwd` | When `save_location` is empty, the output file is saved in the current working directory |
| `test_missing_template_shows_error_dialog` | `DocxTemplate` raises `FileNotFoundError` → `QMessageBox.critical` shown with "Error" in title |

---

## test_integration.py — End-to-end workflow

Full integration tests that drive the PyQt6 GUI with `pytest-qt`'s `qtbot`. Uses real robocopy and real filesystem operations against `tmp_path`. **Skipped automatically if robocopy is unavailable.**

| Test | What it checks |
|------|---------------|
| `test_happy_path_creates_correct_folder_structure` | Fills all fields, clicks **Run Folder Setup**, waits for `worker.finished` signal → BD folder created, Work folder created, `1 Marketing` subfolder deleted from work tree, `1 Marketing.lnk` shortcut created in its place |
| `test_cancel_during_run_does_not_crash` | Clicks **Run** then immediately clicks **Cancel** → app does not crash, `run_btn` is re-enabled and `cancel_btn` is disabled after finish (regardless of whether cancel beat the worker) |
