import ctypes
from pathlib import Path
import subprocess


def _is_network_path(path):
    """Return True if path is on a UNC share or a mapped network drive (Windows).

    Uses GetDriveTypeW which returns immediately without network I/O.
    DRIVE_REMOTE = 4.
    """
    drive = Path(path).drive
    if not drive:
        return False
    if drive.startswith('\\\\'):
        return True  # UNC path
    try:
        drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive + '\\')
        return drive_type == 4  # DRIVE_REMOTE
    except Exception:
        return False


def copy_folder(src, dst, log_func):
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        log_func(f"Source folder does not exist: {src}", "error")
        return False

    # Skip the existence pre-check for network/UNC destinations to avoid blocking
    # network I/O on disconnected drives. Local destinations are checked directly.
    if not _is_network_path(dst) and dst.exists():
        log_func(f"Destination already exists: {dst}. Skipping copy.", "warn")
        return False

    # Track whether dst existed before robocopy runs so we can interpret exit code 0
    # correctly. For network paths we skip the pre-check above, so we record None
    # (unknown). For local paths, by the time we reach here the pre-check above has
    # already returned False if dst existed, so dst_existed_before will always be False
    # for local paths.
    dst_existed_before = dst.exists() if not _is_network_path(dst) else None

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
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode <= 7:
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
