from datetime import datetime

def log(window, message, level="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    tag = {"success": "✅", "warn": "⚠️", "error": "❌", "info": "🛠"}.get(level, "🛠")
    color = {"success": 'lightgreen', "warn": 'yellow', "error": 'red', "info": 'white'}.get(level, 'white')
    window['log'].print(f"[{timestamp}] {tag} {message}", text_color=color)
