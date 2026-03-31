import sys

try:
    import win32com.client
    _WIN32COM_AVAILABLE = True
except ImportError:
    _WIN32COM_AVAILABLE = False


def create_shortcut(target, shortcut_path, log_func):
    if not _WIN32COM_AVAILABLE or sys.modules.get('win32com.client') is None:
        log_func("win32com module not available. Shortcut creation requires pywin32.", "error")
        return False
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = str(target)
        shortcut.WorkingDirectory = str(target.parent)
        shortcut.IconLocation = "explorer.exe"
        shortcut.save()
        log_func(f"Shortcut created: {shortcut_path} → {target}", "success")
        return True
    except Exception as e:
        log_func(f"Shortcut creation failed: {e}", "error")
        return False
