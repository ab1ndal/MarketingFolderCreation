import sys
import subprocess
import pyperclip
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QDialog, QScrollArea, QFormLayout,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor, QFont
from docxtpl import DocxTemplate

from config import (
    DEFAULT_MARKETING_TEMPLATE, DEFAULT_WORK_TEMPLATE,
    DEFAULT_BD_TARGET, DEFAULT_WORK_TARGET, FOLDER_TO_DELETE,
)
from utils.validate import validate_paths
from workers import WorkflowWorker


class FolderSetupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Folder Setup Tool")
        self.resize(850, 600)

        # Center on screen
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                (geo.width() - 850) // 2,
                (geo.height() - 600) // 2,
            )

        self.worker = None
        self.current_year = str(datetime.now().year)
        self.path_fields = {}

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Row 1: Project name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Project Folder Name:"))
        self.project_name_field = QLineEdit()
        name_row.addWidget(self.project_name_field, stretch=1)
        layout.addLayout(name_row)

        # Rows 2-5: Path fields
        path_configs = [
            ("BD Template",     "marketing_template", DEFAULT_MARKETING_TEMPLATE),
            ("Work Template",   "work_template",      DEFAULT_WORK_TEMPLATE),
            ("BD Target (V:)",  "bd_target",          str(Path(DEFAULT_BD_TARGET) / self.current_year)),
            ("Work Target (W:)", "work_target",       str(Path(DEFAULT_WORK_TARGET) / self.current_year)),
        ]
        for label_text, key, default in path_configs:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(140)
            row.addWidget(lbl)
            field = QLineEdit(default)
            row.addWidget(field, stretch=1)
            browse_btn = QPushButton("Browse")
            browse_btn.clicked.connect(lambda checked, k=key: self._browse_folder(k))
            row.addWidget(browse_btn)
            self.path_fields[key] = field
            layout.addLayout(row)

        # Row 6: Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.step_label = QLabel("")
        self.step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.step_label)

        # Row 7: Buttons
        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("Run Folder Setup")
        self.run_btn.clicked.connect(self._run_workflow)
        btn_row.addWidget(self.run_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel_workflow)
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.cancel_btn)

        btn_a250 = QPushButton("Create A250")
        btn_a250.clicked.connect(self._open_a250_form)
        btn_row.addWidget(btn_a250)

        btn_clear = QPushButton("Clear Log")
        btn_clear.clicked.connect(self._clear_log)
        btn_row.addWidget(btn_clear)

        layout.addLayout(btn_row)

        # Row 8: Log panel
        layout.addWidget(QLabel("Log Output:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_text, stretch=1)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _browse_folder(self, key: str):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            self.path_fields[key].setText(path)

    def _clear_log(self):
        self.log_text.clear()

    @pyqtSlot(str, str)
    def write_log(self, message: str, level: str = "info"):
        symbol = {"info": ">>", "success": "[OK]", "error": "[ERR]", "warn": "[WARN]"}.get(level, ">>")
        line = f"{symbol} {message}"
        self.log_text.append(line)
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    @pyqtSlot(int, str)
    def _update_progress(self, value: int, description: str):
        self.progress_bar.setValue(value)
        self.step_label.setText(description)
        self.setWindowTitle(f"Project Folder Setup Tool — {description}")

    def _run_workflow(self):
        self._clear_log()
        name = self.project_name_field.text().strip()
        if not name:
            self.write_log("Please enter a project folder name.", "error")
            return

        paths = {k: v.text().strip() for k, v in self.path_fields.items()}
        if not validate_paths(paths, self.write_log):
            return

        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)

        self.worker = WorkflowWorker(project_name=name, paths=paths, parent=self)
        self.worker.progress.connect(self._update_progress)
        self.worker.log_message.connect(self.write_log)
        self.worker.finished.connect(self._on_workflow_finished)
        self.worker.start()

    def _cancel_workflow(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.write_log("Cancellation requested...", "warn")

    @pyqtSlot(bool)
    def _on_workflow_finished(self, success: bool):
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.setWindowTitle("Project Folder Setup Tool")
        if success:
            work_target = (
                Path(self.path_fields["work_target"].text().strip())
                / self.project_name_field.text().strip()
            )
            pyperclip.copy(str(work_target))
            self.write_log(f"Copied Work Drive folder link to clipboard: {work_target}", "success")
            self.write_log("Project setup completed successfully.", "success")
        else:
            QMessageBox.warning(
                self,
                "Workflow Incomplete",
                "The folder setup did not complete.\nCheck the log below for details.",
            )
            self.write_log("Workflow did not complete (cancelled or error).", "warn")

    # ------------------------------------------------------------------
    # A250 dialog
    # ------------------------------------------------------------------

    def _open_a250_form(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create A250")
        dialog.resize(700, 750)

        outer_layout = QVBoxLayout(dialog)

        # Scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)
        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

        fields = [
            "project_title", "project_address", "nya_project_code", "client_project_code",
            "client", "client_address", "client_phone", "client_mobile",
            "client_email", "client_invoice", "client_office",
            "Fname_R", "Lname_R", "title_R", "licenses",
            "invoice_to",
            "request_date", "work_type", "project_description", "detailed_scope",
            "fee",
            "save_location", "a250_creator",
        ]

        a250_vars = {}
        for field in fields:
            line_edit = QLineEdit()
            form.addRow(field, line_edit)
            a250_vars[field] = line_edit

        # Buttons
        btn_box = QDialogButtonBox()
        generate_btn = btn_box.addButton("Generate A250", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = btn_box.addButton("Close", QDialogButtonBox.ButtonRole.RejectRole)
        outer_layout.addWidget(btn_box)

        generate_btn.clicked.connect(lambda: self._generate_a250(a250_vars))
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec()

    def _generate_a250(self, a250_vars: dict):
        try:
            data = {k: v.text() for k, v in a250_vars.items()}
            data["current_date"] = datetime.now().strftime("%m/%d/%Y")
            template_path = Path("templates/A250.docx")
            output_name = f"A250_{data.get('project_title', 'output')}.docx"
            save_loc = data.get("save_location", "").strip()
            output_path = (Path(save_loc) / output_name) if save_loc else (Path.cwd() / output_name)
            doc = DocxTemplate(template_path)
            doc.render(data)
            doc.save(output_path)
            subprocess.Popen(f'explorer /select,"{output_path}"', shell=True)
            self.write_log(f"A250 generated: {output_path}", "success")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FolderSetupApp()
    window.show()
    sys.exit(app.exec())
