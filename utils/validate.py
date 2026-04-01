from pathlib import Path
from PyQt6.QtWidgets import QMessageBox


def validate_paths(paths: dict, log_func) -> bool:
    """
    Validate that all paths in the dict exist.
    Shows a QMessageBox.critical dialog AND calls log_func on failure.
    Returns True if all paths exist, False on first failure.
    """
    label_names = {
        "marketing_template": "BD Template",
        "work_template": "Work Template",
        "bd_target": "BD Target (V:)",
        "work_target": "Work Target (W:)",
    }
    for key, path in paths.items():
        if not Path(path).exists():
            label = label_names.get(key, key)
            msg = f"Path not found: {label}\n{path}"
            log_func(f"Invalid path: {label} -> {path}", "error")
            QMessageBox.critical(None, "Invalid Path", msg)
            return False
    return True
