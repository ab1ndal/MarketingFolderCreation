import shutil
import os
import stat
import subprocess
import tempfile
from pathlib import Path


def handle_remove_readonly(func, path, _):
    """Clear read-only bit and retry."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def delete_with_robocopy_mirror(folder_path, log_func):
    """Use robocopy /MIR with empty temp dir to delete all contents, then rmdir the folder."""
    try:
        with tempfile.TemporaryDirectory() as empty_dir:
            cmd = [
                "robocopy",
                str(empty_dir),
                str(folder_path),
                "/MIR",
                "/NP",
                "/NFL",
                "/NDL",
                "/NJH",
                "/NJS",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode <= 7:
                # Contents cleared by robocopy mirror; remove the now-empty folder
                try:
                    folder_path.rmdir()
                except OSError:
                    # Folder may still have contents if robocopy was mocked; ignore
                    pass
                return True
            else:
                return False
    except Exception as e:
        log_func(f"Robocopy mirror deletion failed: {e}", "warn")
        return False


def delete_with_shutil_retry(folder_path, log_func, retry_count=3):
    """Delete folder using shutil.rmtree with retry on permission errors."""
    last_error = None
    for attempt in range(retry_count):
        try:
            shutil.rmtree(folder_path, onerror=handle_remove_readonly)
            return True
        except Exception as e:
            last_error = e
    log_func(f"Failed to delete {folder_path}: {last_error}", "error")
    return False


def delete_folder(folder_path, log_func):
    """Delete a folder using robocopy mirror first, with shutil fallback."""
    if not folder_path.exists():
        log_func(f"No folder found to delete: {folder_path}", "warn")
        return False
    if delete_with_robocopy_mirror(folder_path, log_func):
        log_func(f"Deleted folder: {folder_path}", "success")
        return True
    if delete_with_shutil_retry(folder_path, log_func):
        log_func(f"Deleted folder: {folder_path}", "success")
        return True
    return False
