from pathlib import Path

def validate_paths(paths: dict, log_func):
    for label, path in paths.items():
        if not Path(path).exists():
            log_func(f"❌ Invalid path: {label} → {path}", "error")
            return False
    return True