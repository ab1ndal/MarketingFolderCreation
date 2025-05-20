from logger import log

def create_shortcut(target, shortcut_path, log_func):
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = str(target)
        shortcut.WorkingDirectory = str(target.parent)
        shortcut.IconLocation = "explorer.exe"
        shortcut.save()
        log_func(f"✅ Shortcut created: {shortcut_path} → {target}", "success")
    except Exception as e:
        log_func(f"❌ Shortcut creation failed: {e}", "error")

