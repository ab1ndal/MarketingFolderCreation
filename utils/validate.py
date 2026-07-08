from pathlib import Path
from PyQt6.QtWidgets import QMessageBox

# Characters Windows forbids in a file/folder name.
INVALID_FOLDER_CHARS = '<>:"/\\|?*'

# Names Windows reserves (case-insensitive, with or without extension).
RESERVED_FOLDER_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def validate_folder_name(name: str) -> str | None:
    """
    Check a folder name against Windows naming rules.
    Returns None if valid, else a human-readable reason string.
    """
    if not name:
        return "Folder name is empty."

    bad = sorted({c for c in name if c in INVALID_FOLDER_CHARS})
    if bad:
        return (
            "Folder name contains characters not allowed by Windows: "
            + " ".join(bad)
            + f"\n\nNot allowed: {' '.join(INVALID_FOLDER_CHARS)}"
        )

    ctrl = sorted({c for c in name if ord(c) < 32})
    if ctrl:
        return "Folder name contains control characters (tab/newline etc.)."

    if name != name.rstrip(" ."):
        return "Folder name cannot end with a space or a period."

    stem = name.split(".")[0].upper()
    if stem in RESERVED_FOLDER_NAMES:
        return f'"{name}" is a name reserved by Windows and cannot be used.'

    return None


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
        if not path or not Path(path).exists():
            label = label_names.get(key, key)
            msg = f"Path not found: {label}\n{path}"
            log_func(f"Invalid path: {label} -> {path}", "error")
            QMessageBox.critical(None, "Invalid Path", msg)
            return False
    return True
