import sys
import re
import subprocess
import pyperclip
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QDialog, QScrollArea, QFormLayout,
    QDialogButtonBox, QGroupBox, QComboBox, QCheckBox, QSplitter, QTextBrowser
)
from PyQt6.QtCore import Qt, pyqtSlot, QEvent, QTimer
from PyQt6.QtGui import QTextCursor, QFont
from docxtpl import DocxTemplate

from config import (
    DEFAULT_MARKETING_TEMPLATE, DEFAULT_WORK_TEMPLATE,
    DEFAULT_BD_TARGET, DEFAULT_WORK_TARGET, PRINCIPAL_OPTIONS,
    PROJECT_MANAGER_OPTIONS, FEE_TYPE_OPTIONS, PATH_LENGTH_MARGIN
)
from utils.validate import validate_paths, validate_folder_name
from utils.web_editor import WebRichTextEditor
from utils.segment import derive_year, project_number, find_primary_folders
from utils.pathcheck import projected_path_len, WINDOWS_MAX_PATH
from utils.richtext_utils import html_to_richtext
from workers import WorkflowWorker
from utils.formatting import format_number
from utils.a250_context import build_a250_context


def _resource_path(relative: str) -> Path:
    """Resolve a resource path that works both in dev and in a PyInstaller bundle.

    In a bundle, sys._MEIPASS is set to the extraction root.
    In dev, falls back to the directory containing app.py.
    """
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    return base / relative


def _a250_display_filename(raw: dict) -> str:
    """Resolve the `<stem>.docx` display/output filename from raw field values.

    Single source of truth for the file_name stem, based on the raw (un-suffixed)
    value so it can't be double-suffixed. Used both for the {{file_name}} template
    variable (rendered by render_a250_docx) and for the saved output path
    (_generate_a250), so the footer text and the actual saved filename always match.
    """
    stem = raw.get("file_name") or f"A250_{raw.get('project_title', 'output')}"
    return f"{stem}.docx"


def render_a250_docx(raw: dict, out_path) -> None:
    """Render the real A250 docx from raw field values into out_path.

    Shared by the live preview and the Generate button so the preview shows
    exactly what generation produces. Does not resolve output filename or
    save location - the caller handles that.
    """
    data = build_a250_context(raw)
    data["file_name"] = _a250_display_filename(raw)
    for key in ("project_description", "detailed_scope"):
        data[key] = html_to_richtext(raw.get(key, ""))
    template_path = _resource_path("templates/A250.docx")
    doc = DocxTemplate(template_path)
    doc.render(data)
    doc.save(Path(out_path))


A250_FIELD_GROUPS = [
    ("Project Info", [
        ("project_title", "Project Title"),
        ("project_address", "Project Address"),
        ("client", "Company Name"),
        ("nya_project_code", "NYA Project Code"),
        ("client_project_code", "Client Project Code"),
    ]),
    ("Client Contact", [
        ("client_name", "Client Name"),
        ("client_title", "Title"),
        ("client_license", "Licenses"),
        ("client_phone", "Phone Number"),
        ("client_mobile", "Mobile Number"),
        ("client_email", "Email Address"),
    ]),
    ("Billing", [
        ("invoice_to", "Invoice To"),
        ("client_office_no", "Office Number"),
        ("client_invoice_email", "Invoice Email"),
        ("client_address", "Client Address"),
    ]),
    ("Scope & Fee", [
        ("request_date", "Request Date"),
        ("received_date", "Received Date"),
        ("project_description", "Project Description"),
        ("detailed_scope", "Detailed Scope"),
        ("fee_type", "Fee Type"),
        ("fee", "Fee"),
    ]),
    ("Additional Info", [
        ("principal_name", "Principal Name"),
        ("project_manager", "Project Manager"),
    ]),
    ("Output", [
        ("save_location", "Save Location"),
        ("file_name", "File Name"),
        ("a250_creator", "Created By"),
    ]),
]

# Derived/composite values shown in their own preview section with a note.
A250_COMPOSITE_KEYS = ["requested_by", "invoice_to", "client_signed", "fee", "today"]
A250_COMPOSITE_NOTES = {
    "requested_by": "auto-built from Name / License / Title / Company",
    "invoice_to": "your custom text, else same as Requested By",
    "client_signed": "auto-built from Name / Title",
    "fee": "formatted with thousands separators and 2 decimals",
    "today": "today's date, inserted automatically",
}


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
        # Validate on blur (focus out), not on every keystroke.
        self.project_name_field.installEventFilter(self)
        self.project_name_field.textChanged.connect(self._clear_name_error)
        name_row.addWidget(self.project_name_field, stretch=1)
        layout.addLayout(name_row)

        # Inline validation hint for the project name
        self.name_hint = QLabel("")
        self.name_hint.setStyleSheet("color: #c0392b;")
        self.name_hint.setWordWrap(True)
        layout.addWidget(self.name_hint)

        # Segment mode toggle + primary picker
        self.segment_checkbox = QCheckBox("Create a Segment")
        self.segment_checkbox.toggled.connect(self._on_segment_toggled)
        layout.addWidget(self.segment_checkbox)

        self.primary_row = QWidget()
        primary_layout = QHBoxLayout(self.primary_row)
        primary_layout.setContentsMargins(0, 0, 0, 0)
        primary_lbl = QLabel("Primary Folder")
        primary_lbl.setFixedWidth(140)
        primary_layout.addWidget(primary_lbl)
        self.primary_combo = QComboBox()
        self.primary_combo.setEnabled(False)
        self.primary_combo.currentIndexChanged.connect(lambda _=None: self._update_dest_note())
        primary_layout.addWidget(self.primary_combo, stretch=1)
        layout.addWidget(self.primary_row)

        self.primary_hint = QLabel("")
        self.primary_hint.setStyleSheet("color: #c0392b;")
        self.primary_hint.setWordWrap(True)
        layout.addWidget(self.primary_hint)

        self.primary_row.setVisible(False)
        self.primary_hint.setVisible(False)

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

        # Note under the targets: shows the nested destination in segment mode
        self.dest_note = QLabel("")
        self.dest_note.setStyleSheet("color: #555; font-style: italic;")
        self.dest_note.setWordWrap(True)
        self.dest_note.setVisible(False)
        layout.addWidget(self.dest_note)

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

    def eventFilter(self, obj, event):
        """Validate the project name when the field loses focus (blur)."""
        if obj is self.project_name_field and event.type() == QEvent.Type.FocusOut:
            self._validate_name_field()
            self._apply_derived_year()
            if self.segment_checkbox.isChecked():
                self._scan_primaries()
            self._update_dest_note()
        return super().eventFilter(obj, event)

    def _clear_name_error(self, text: str = ""):
        """Clear the inline error while the user edits the name."""
        if self.name_hint.text():
            self.name_hint.setText("")

    def _validate_name_field(self):
        """Show/clear the inline form error for the project name."""
        name = self.project_name_field.text().strip()
        reason = None if not name else validate_folder_name(name)
        self.name_hint.setText(reason or "")
        return bool(name) and reason is None

    def _apply_derived_year(self):
        """Rewrite the <year> segment of the BD and Work target fields from the project number.

        Applies in both normal and segment mode. If the field's last path component is a
        4-digit year it is replaced; otherwise the derived year is appended. No-op when the
        name has no usable leading number.
        """
        year = derive_year(self.project_name_field.text().strip(), datetime.now().year)
        if year is None:
            return
        for key in ("bd_target", "work_target"):
            field = self.path_fields[key]
            text = field.text().strip()
            if not text:
                continue
            parts = list(Path(text).parts)
            if parts and re.fullmatch(r"(19|20)\d{2}", parts[-1]):
                parts[-1] = str(year)
                field.setText(str(Path(*parts)))
            else:
                field.setText(str(Path(text) / str(year)))

    def _scan_primaries(self):
        """Scan the BD target (V:) year root for primary folders matching the project number."""
        self.primary_combo.clear()
        self.primary_hint.setText("")
        nnnnn = project_number(self.project_name_field.text().strip())
        year_root = self.path_fields["bd_target"].text().strip()
        if not nnnnn:
            self.primary_combo.setEnabled(False)
            return
        matches = find_primary_folders(year_root, nnnnn)
        if not matches:
            self.primary_combo.setEnabled(False)
            self.primary_hint.setText(
                f"No primary folder starting with {nnnnn} found in {year_root}"
            )
            return
        self.primary_combo.addItems(matches)
        self.primary_combo.setEnabled(True)
        self._update_dest_note()

    def _update_dest_note(self):
        """Show a note with the full nested destination path(s) in segment mode."""
        primary = self.primary_combo.currentText().strip()
        segment = self.project_name_field.text().strip()
        if not self.segment_checkbox.isChecked() or not primary or not segment:
            self.dest_note.setText("")
            self.dest_note.setVisible(False)
            return
        bd = Path(self.path_fields["bd_target"].text().strip()) / primary / segment
        work = Path(self.path_fields["work_target"].text().strip()) / primary / segment
        self.dest_note.setText(
            f"Segment will be created in:\nBD:   {bd}\nWork: {work}"
        )
        self.dest_note.setVisible(True)

    def _on_segment_toggled(self, checked: bool):
        """Show/hide the primary picker; scan on enable, clear on disable."""
        self.primary_row.setVisible(checked)
        self.primary_hint.setVisible(checked)
        if checked:
            self._scan_primaries()
        else:
            self.primary_combo.clear()
            self.primary_combo.setEnabled(False)
            self.primary_hint.setText("")
        self._update_dest_note()

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

    def _confirm_path_length(self, paths: dict, name: str, primary: str | None) -> bool:
        """Warn if the projected deepest path nears MAX_PATH. Return True to proceed.

        Projects, per drive, the target base (with the primary inserted in segment mode)
        plus the deepest subpath of the corresponding template. Reserves PATH_LENGTH_MARGIN
        below the limit for files the user adds later. Shows a Yes/No dialog on risk.
        """
        bd_base = Path(paths["bd_target"])
        work_base = Path(paths["work_target"])
        if primary:
            bd_base = bd_base / primary
            work_base = work_base / primary
        bd_base = bd_base / name
        work_base = work_base / name

        long_paths = []
        for label, base, template in (
            ("BD", bd_base, paths["marketing_template"]),
            ("Work", work_base, paths["work_template"]),
        ):
            projected = projected_path_len(str(base), template)
            if projected > WINDOWS_MAX_PATH - PATH_LENGTH_MARGIN:
                long_paths.append((label, projected))

        if not long_paths:
            return True

        detail = "\n".join(f"  {label} drive: ~{n} characters" for label, n in long_paths)
        resp = QMessageBox.question(
            self,
            "Long Path Warning",
            f"The deepest folder path may reach the lengths below, near Windows' "
            f"{WINDOWS_MAX_PATH}-character limit "
            f"({PATH_LENGTH_MARGIN} reserved for files you add later):\n\n{detail}\n\n"
            f"Paths this long can be hard to open in Explorer/Office and may break the "
            f"shortcut. Shorten the name/segment, or create anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            self.write_log("Cancelled: projected path length near the Windows limit.", "warn")
            return False
        return True

    def _run_workflow(self):
        self._clear_log()
        name = self.project_name_field.text().strip()
        if not name:
            self.name_hint.setText("Folder name is empty.")
            self.write_log("Please enter a project folder name.", "error")
            return

        reason = validate_folder_name(name)
        if reason:
            self.name_hint.setText(reason)
            self.write_log(f"Invalid folder name: {reason}", "error")
            return

        paths = {k: v.text().strip() for k, v in self.path_fields.items()}
        if not validate_paths(paths, self.write_log):
            return

        primary = None
        if self.segment_checkbox.isChecked():
            primary = self.primary_combo.currentText().strip()
            if not primary:
                self.primary_hint.setText(
                    "Select a primary folder before running (no matching primary found)."
                )
                self.write_log("Segment mode: no primary folder selected.", "error")
                return

        # Path-length guard: project the deepest path after copy and warn (allow
        # proceeding) if it nears the Windows MAX_PATH limit.
        if not self._confirm_path_length(paths, name, primary):
            return

        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)

        self.worker = WorkflowWorker(project_name=name, paths=paths, primary=primary, parent=self)
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
            parts = [self.path_fields["work_target"].text().strip()]
            if self.segment_checkbox.isChecked() and self.primary_combo.currentText().strip():
                parts.append(self.primary_combo.currentText().strip())
            parts.append(self.project_name_field.text().strip())
            work_target = Path(*parts)
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
        dialog.resize(1150, 820)

        outer_layout = QVBoxLayout(dialog)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        outer_layout.addWidget(splitter)

        # ---- Left: scrollable form ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        scroll.setWidget(container)
        splitter.addWidget(scroll)

        # ---- Right: live preview ----
        preview_panel = QWidget()
        pv_layout = QVBoxLayout(preview_panel)
        pv_layout.addWidget(QLabel("Preview — how your entries map to the document"))
        preview = QTextBrowser()
        pv_layout.addWidget(preview)
        splitter.addWidget(preview_panel)
        splitter.setStretchFactor(0, 55)
        splitter.setStretchFactor(1, 45)

        a250_vars = {}
        COMBO_FIELDS = {
            "principal_name": PRINCIPAL_OPTIONS,
            "project_manager": PROJECT_MANAGER_OPTIONS,
            "fee_type": FEE_TYPE_OPTIONS,
        }
        MULTILINE_FIELDS = {"project_address", "client_address", "invoice_to"}
        RICH_TEXT_FIELDS = {"project_description", "detailed_scope"}

        for section_title, field_pairs in A250_FIELD_GROUPS:
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

        # ---- Debounced live preview refresh ----
        preview_timer = QTimer(dialog)
        preview_timer.setSingleShot(True)
        preview_timer.setInterval(300)
        preview_timer.timeout.connect(lambda: self._refresh_preview(a250_vars, preview))

        def schedule(*_):
            preview_timer.start()  # restart cancels the prior pending fire

        for key, widget in a250_vars.items():
            if isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(schedule)
            elif isinstance(widget, WebRichTextEditor):
                widget.set_change_callback(schedule)
            elif isinstance(widget, QTextEdit):
                widget.textChanged.connect(schedule)
            else:
                widget.textChanged.connect(schedule)

        # Initial render (fields empty)
        self._refresh_preview(a250_vars, preview)

        # ---- Buttons ----
        btn_box = QDialogButtonBox()
        generate_btn = btn_box.addButton("Generate A250", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = btn_box.addButton("Close", QDialogButtonBox.ButtonRole.RejectRole)
        outer_layout.addWidget(btn_box)

        generate_btn.clicked.connect(lambda: self._generate_a250(a250_vars))
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec()

    def _refresh_preview(self, a250_vars: dict, preview: QTextBrowser) -> None:
        """Recompute the resolved-values preview from current field values."""
        try:
            raw = self._collect_a250_raw(a250_vars, use_cache=True)
            ctx = build_a250_context(raw)
            rich_keys = {k for k, w in a250_vars.items() if isinstance(w, WebRichTextEditor)}
            preview.setHtml(self._render_preview_html(ctx, rich_keys))
        except Exception as e:  # never let the preview crash the form
            import html as _h
            preview.setHtml(
                f"<p style='color:#c0392b'>Preview unavailable: {_h.escape(str(e))}</p>"
            )

    def _render_preview_html(self, ctx: dict, rich_keys: set) -> str:
        """Render the template context as grouped HTML for the QTextBrowser."""
        import html as _h

        def cell(key: str) -> str:
            v = ctx.get(key, "")
            if key in rich_keys:
                return v if (v and v.strip() and v.strip() != "<p></p>") \
                    else "<span style='color:#999'>&mdash;</span>"
            v = "" if v is None else str(v)
            if not v.strip():
                return "<span style='color:#999'>&mdash;</span>"
            return _h.escape(v).replace("\n", "<br>")

        parts = [
            "<style>"
            "body{font-family:'Segoe UI',sans-serif;font-size:13px;}"
            "h3{margin:12px 0 4px;font-size:13px;border-bottom:1px solid #ccc;}"
            "h3.comp{color:#2d7d46;}"
            "table{width:100%;border-collapse:collapse;}"
            "td{padding:2px 6px;vertical-align:top;}"
            "td.lbl{color:#555;width:40%;}"
            "td.comp{color:#2d7d46;font-weight:bold;}"
            ".note{color:#999;font-weight:normal;font-size:11px;}"
            "</style>"
        ]
        for section_title, field_pairs in A250_FIELD_GROUPS:
            parts.append(f"<h3>{_h.escape(section_title)}</h3><table>")
            for key, label in field_pairs:
                parts.append(
                    f"<tr><td class='lbl'>{_h.escape(label)}</td><td>{cell(key)}</td></tr>"
                )
            parts.append("</table>")

        parts.append("<h3 class='comp'>Derived &amp; Composite</h3><table>")
        for key in A250_COMPOSITE_KEYS:
            note = A250_COMPOSITE_NOTES.get(key, "")
            parts.append(
                f"<tr><td class='lbl comp'>{_h.escape(key)}"
                f"<br><span class='note'>{_h.escape(note)}</span></td>"
                f"<td>{cell(key)}</td></tr>"
            )
        parts.append("</table>")
        return "".join(parts)

    def _collect_a250_raw(self, a250_vars: dict, use_cache: bool = False) -> dict:
        """Gather raw string values from every A250 widget.

        Rich-text fields return HTML. When use_cache is True, rich-text uses the
        last value pushed by the Quill bridge (cheap, no JS round-trip), falling
        back to a synchronous pull if the cache is empty.
        """
        raw = {}
        for key, w in a250_vars.items():
            if isinstance(w, QComboBox):
                raw[key] = w.currentText()
            elif isinstance(w, WebRichTextEditor):
                # Preview reads the bridge cache only — a synchronous pull here can
                # run getContent() before the editor page has loaded, throwing
                # "getContent is not defined". Generation (use_cache=False) pulls.
                raw[key] = w.cached_html() if use_cache else w.get_html_sync()
            elif isinstance(w, QTextEdit):
                raw[key] = w.toPlainText()
            else:
                raw[key] = w.text()
        return raw

    def _generate_a250(self, a250_vars: dict):
        try:
            raw = self._collect_a250_raw(a250_vars)
            file_name = _a250_display_filename(raw)
            save_loc = raw.get("save_location", "").strip()
            output_path = (Path(save_loc) / file_name) if save_loc else (Path.cwd() / file_name)
            render_a250_docx(raw, output_path)
            subprocess.Popen(f'explorer /select,"{output_path}"', shell=True)
            self.write_log(f"A250 generated: {output_path}", "success")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FolderSetupApp()
    window.show()
    sys.exit(app.exec())
