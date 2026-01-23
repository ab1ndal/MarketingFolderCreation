# 📁 Project Folder Setup Tool

This Python-based GUI tool automates the creation of structured project directories for both marketing and working drives, based on template folders of Nabih Youssef & Associates. It copies, configures, and links folders with minimal user input and is ideal for architecture, engineering, and construction firms with consistent folder standards.

---

## 🔧 Features

* Copy full folder structure (including all subfolders/files) from predefined templates
* User-friendly GUI with folder pickers and progress bar
* Real-time color-coded log output for each step
* Automatically deletes and replaces `1 Marketing` folder with a shortcut in the work folder
* Fully modular and customizable Python code

---

## 📂 Folder Structure (Modular Codebase)

```
project_setup_tool/
├── app.py                     # Main GUI interface
├── config.py                  # Default path configuration
├── logger.py                  # Timestamped, color-coded log function
├── operations/
│   ├── copy_ops.py            # Folder copying logic
│   ├── delete_ops.py          # Folder deletion logic
│   └── shortcut_ops.py        # Shortcut creation logic (Windows only)
├── utils/
│   └── validate.py            # Input path validation
```

---

## 🖥️ How to Use

1. **Install dependencies** (once):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
2. **Run the app**:

   ```bash
   python app.py
   ```
3. **Enter inputs**:

   * Project Folder Name
   * Adjust default template and destination paths (optional)
   * Click **Run Folder Setup**
   * Click **Clear Log** to clear the log (optional)

The tool logs and tracks each step as it:

* Copies the marketing template to `V:\{current year}\{Project Folder}`
* Copies the work template to `W:\{current year}\{Project Folder}`
* Deletes the `1 Marketing` folder in the work folder
* Replaces it with a shortcut to the marketing folder location in V Drive

---

## 🔒 Requirements

* Windows OS (for shortcut creation via `pywin32`)
* Python 3.8 or newer

---

## 🛠 Build a Standalone .exe

To distribute without requiring Python:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name ClickFolder --icon=FolderCreatorTool.ico app.py
```

Output will be located in the `dist/` folder.

---

## ✅ Customization Ideas

* Save logs to `.txt` file
* Add dry-run / preview mode
* Extend with email notifications or integrations

---

## 👤 Author

Developed by Abhinav Bindal for internal automation of project directory setup at Nabih Youssef & Associates.
