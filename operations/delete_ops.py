import shutil
import os
import stat
from logger import log

def handle_remove_readonly(func, path, _):
    """Clear read-only bit and retry"""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def delete_folder(folder_path, log_func):
    if folder_path.exists():
        try:
            shutil.rmtree(folder_path, onerror=handle_remove_readonly)
            log_func(f"Deleted folder: {folder_path}", "success")
        except Exception as e:
            log_func(f"Failed to delete {folder_path}: {e}", "error")
    else:
        log_func(f"No folder found to delete: {folder_path}", "warn")
