import os
from pathlib import Path
import subprocess


def copy_folder(src, dst, log_func):
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        log_func(f"Source folder does not exist: {src}", "error")
        return False

    if os.path.exists(dst):
        log_func(f"Destination already exists: {dst}. Skipping copy.", "warn")
        return False

    log_func(f"Starting robocopy from {src} to {dst}...", "info")

    cmd = [
        "robocopy",
        str(src),
        str(dst),
        "/E",
        "/NP",
        "/R:5",
        "/W:5",
        "/MT:16",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            log_func("Source and destination are already in sync (no files copied)", "info")
            return True
        elif result.returncode <= 7:
            log_func(f"Successfully copied from {src} to {dst}", "success")
            return True
        else:
            log_func(f"Robocopy failed with exit code {result.returncode}: {result.stderr}", "error")
            return False
    except subprocess.TimeoutExpired:
        log_func(f"Robocopy timed out after 1 hour copying {src} to {dst}", "error")
        return False
    except FileNotFoundError:
        log_func("Robocopy not found. Please ensure Windows is properly installed.", "error")
        return False
    except Exception as e:
        log_func(f"Robocopy failed: {e}", "error")
        return False
