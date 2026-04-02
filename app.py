import sys
import subprocess
import pyperclip
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QDialog, QScrollArea, QFormLayout,
    QDialogButtonBox, QGroupBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor, QFont
from docxtpl import DocxTemplate

from config import (
    DEFAULT_MARKETING_TEMPLATE, DEFAULT_WORK_TEMPLATE,
    DEFAULT_BD_TARGET, DEFAULT_WORK_TARGET, PRINCIPAL_OPTIONS, 
    PROJECT_MANAGER_OPTIONS, FEE_TYPE_OPTIONS
)
from utils.validate import validate_paths
from utils.web_editor import WebRichTextEditor
from utils.richtext_utils import html_to_richtext
from workers import WorkflowWorker


def _resource_path(relative: str) -> Path:
    """Resolve a resource path that works both in dev and in a PyInstaller bundle.

    In a bundle, sys._MEIPASS is set to the extraction root.
    In dev, falls back to the directory containing app.py.
    """
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    return base / relative


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
        dialog.resize(700, 780)

        outer_layout = QVBoxLayout(dialog)

        # Scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

        a250_vars = {}

        groups = [
            ("Project Info", [
                ("project_title",       "Project Title"),
                ("project_address",     "Project Address"),
                ("client",              "Company Name"),
                ("nya_project_code",    "NYA Project Code"),
                ("client_project_code", "Client Project Code"),
            ]),
            ("Client Contact", [
                ("client_name",    "Client Name"),
                ("client_title",   "Title"),
                ("client_license", "Licenses"),
                ("client_phone",   "Phone Number"),
                ("client_mobile",  "Mobile Number"),
                ("client_email",   "Email Address")
            ]),
            ("Billing", [
                ("invoice_to",           "Invoice To"),
                ("client_office_no",     "Office Number"),
                ("client_invoice_email", "Invoice Email"),
                ("client_address",       "Client Address")
            ]),
            ("Scope & Fee", [
                ("request_date",        "Request Date"),
                ("received_date",       "Received Date"),
                ("project_description", "Project Description"),
                ("detailed_scope",      "Detailed Scope"),
                ("fee_type",            "Fee Type"),
                ("fee",                 "Fee"),
            ]),
            ("Additional Info", [
                ("principal_name", "Principal Name"),
                ("project_manager", "Project Manager")
            ]),
            ("Output", [
                ("save_location", "Save Location"),
                ("file_name", "File Name"),
                ("a250_creator",  "Created By"),
            ]),
        ]

        COMBO_FIELDS = {
            "principal_name": PRINCIPAL_OPTIONS,
            "project_manager": PROJECT_MANAGER_OPTIONS,
            "fee_type": FEE_TYPE_OPTIONS,
        }
        MULTILINE_FIELDS = {"project_address", "client_address", "invoice_to"}
        RICH_TEXT_FIELDS = {"project_description", "detailed_scope"}

        for section_title, field_pairs in groups:
            group_box = QGroupBox(section_title)
            form = QFormLayout(group_box)
            for key, label in field_pairs:
                if key in COMBO_FIELDS:
                    widget = QComboBox()
                    widget.addItems(COMBO_FIELDS[key])
                    form.addRow(label, widget)
                elif key in RICH_TEXT_FIELDS:
                    widget = WebRichTextEditor(height=150)
                    form.addRow(label, widget)
                elif key in MULTILINE_FIELDS:
                    widget = QTextEdit()
                    widget.setFixedHeight(80)
                    form.addRow(label, widget)
                else:
                    widget = QLineEdit()
                    form.addRow(label, widget)
                a250_vars[key] = widget
            container_layout.addWidget(group_box)

        container_layout.addStretch()

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
            def _get_val(w):
                if isinstance(w, QComboBox):
                    return w.currentText()
                elif isinstance(w, WebRichTextEditor):
                    return html_to_richtext(w.get_html_sync())
                elif isinstance(w, QTextEdit):
                    return w.toPlainText()
                else:
                    return w.text()

            data = {k: _get_val(v) for k, v in a250_vars.items()}
            data["today"] = datetime.now().strftime("%B %#d, %Y")
            data["current_date"] = data["today"]

            # --- Composite: requested_by ---
            name     = data.get("client_name", "").strip()
            license  = data.get("client_license", "").strip()
            title    = data.get("client_title", "").strip()
            client   = data.get("client", "").strip()

            licence_sep = ", " if license else ""
            title_sep = "\n\n" if len(name) + len(license) + len(title) > 60 else "\n"
            data["requested_by"] = f"{name}{licence_sep}{license}{title_sep}{title}\n{client}"

            # --- Composite: client_signed ---
            title_sep2 = "\n" if len(name) + len(title) > 40 else ", "
            data["client_signed"] = f"{name}{title_sep2}{title}"

            # --- Composite: invoice_to ---
            invoice_custom = data.get("invoice_to", "").strip()
            if not invoice_custom:
                data["invoice_to"] = data["requested_by"]
            # else leave data["invoice_to"] as the custom text the user entered
            template_path = _resource_path("templates/A250.docx")
            if data.get("file_name"):
                output_name = f"{data.get('file_name')}.docx"
            else:
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
