import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
from pathlib import Path
import pyperclip

from config import (
    DEFAULT_MARKETING_TEMPLATE,
    DEFAULT_WORK_TEMPLATE,
    DEFAULT_BD_TARGET,
    DEFAULT_WORK_TARGET,
    FOLDER_TO_DELETE
)
from logger import log
from operations.copy_ops import copy_folder
from operations.delete_ops import delete_folder
from operations.shortcut_ops import create_shortcut
from utils.validate import validate_paths

SHORTCUT_NAME = FOLDER_TO_DELETE + ".lnk"

class FolderSetupApp:
    def __init__(self, root):
        self.root = root
        root.title("📁 Project Folder Setup Tool")
        root.update_idletasks()
        width, height = 850, 600
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")

        self.paths = {
            "marketing_template": tk.StringVar(value=DEFAULT_MARKETING_TEMPLATE),
            "work_template": tk.StringVar(value=DEFAULT_WORK_TEMPLATE),
            "bd_target": tk.StringVar(value=DEFAULT_BD_TARGET),
            "work_target": tk.StringVar(value=DEFAULT_WORK_TARGET),
        }

        self.project_name = tk.StringVar()

        self.build_ui()

    def build_ui(self):
        row = 0

        tk.Label(text="Project Folder Name:").grid(row=row, column=0, sticky='w', padx=10)
        tk.Entry(textvariable=self.project_name, width=80).grid(row=row, column=1, padx=10, pady=5)
        row += 1

        for label, key in [
            ("BD Template", "marketing_template"),
            ("Work Template", "work_template"),
            ("BD Target (V:)", "bd_target"),
            ("Work Target (W:)", "work_target"),
        ]:
            tk.Label(text=label).grid(row=row, column=0, sticky='w', padx=10)
            tk.Entry(textvariable=self.paths[key], width=80).grid(row=row, column=1, padx=10)
            tk.Button(text="Browse", command=lambda k=key: self.browse_folder(k)).grid(row=row, column=2, padx=5)
            row += 1

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=600, mode="determinate")
        self.progress.grid(row=row, column=0, columnspan=3, pady=(15, 5), padx=10)
        row += 1

        tk.Button(text="🚀 Run Folder Setup", command=self.run_workflow).grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        tk.Button(text="🧹 Clear Log", command=self.clear_log).grid(row=row, column=2, padx=10, sticky="ew")
        row += 1

        tk.Label(text="Log Output:").grid(row=row, column=0, sticky='nw', padx=10)
        self.log_text = scrolledtext.ScrolledText(self.root, width=100, height=15, state='disabled', font=('Consolas', 10))
        self.log_text.grid(row=row, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_rowconfigure(row, weight=1)

    def browse_folder(self, key):
        folder = filedialog.askdirectory()
        if folder:
            self.paths[key].set(folder)

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

    def write_log(self, message, level="info"):
        symbol = {"info": "🛠", "success": "✅", "error": "❌", "warn": "⚠️"}.get(level, "🛠")
        line = f"{symbol} {message}\n"
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, line)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update()

    def run_workflow(self):
        self.clear_log()
        name = self.project_name.get().strip()

        if not name:
            self.write_log("Please enter a project folder name.", "error")
            return

        paths = {k: v.get().strip() for k, v in self.paths.items()}
        print(paths)
        if not validate_paths(paths, self.write_log):
            return

        bd_target = Path(paths['bd_target']) / name
        work_target = Path(paths['work_target']) / name

        try:
            self.progress.config(value=0)
            self.write_log("Starting project folder setup...", "info")
            self.progress.config(value=20)

            copy_folder(paths['marketing_template'], bd_target, self.write_log)
            self.progress.config(value=40)

            copy_folder(paths['work_template'], work_target, self.write_log)
            self.progress.config(value=60)

            delete_folder(work_target / FOLDER_TO_DELETE, self.write_log)
            self.progress.config(value=80)

            create_shortcut(bd_target, work_target / SHORTCUT_NAME, self.write_log)
            self.progress.config(value=100)

            self.write_log("Project setup completed successfully.", "success")
            
            # Copy the link to Work Drive folder in the clipboard
            pyperclip.copy(str(work_target))
            self.write_log(f"Copied Work Drive folder link to clipboard: {work_target}", "success")

        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = FolderSetupApp(root)
    root.mainloop()
