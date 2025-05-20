import shutil
from logger import log
from pathlib import Path

def copy_folder(src, dst, log_func):
    dst = Path(dst)
    src = Path(src)

    if not src.exists():
        log_func(f"❌ Source folder does not exist: {src}", "error")
        return

    if dst.exists():
        log_func(f"⚠️ Destination already exists: {dst}, deleting...", "warn")
        shutil.rmtree(dst)

    shutil.copytree(src, dst)
    log_func(f"✅ Copied from {src} to {dst}", "success")