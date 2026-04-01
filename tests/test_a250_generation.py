import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QLineEdit


# Ensure QApplication exists for widget tests
@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestA250Generation:

    def _make_a250_vars(self, overrides=None):
        """Build a minimal a250_vars dict of QLineEdit mocks."""
        fields = [
            "project_title", "project_address", "nya_project_code", "client_project_code",
            "client", "client_address", "client_phone", "client_mobile",
            "client_email", "client_invoice", "client_office",
            "Fname_R", "Lname_R", "title_R", "licenses",
            "invoice_to", "request_date", "work_type", "project_description",
            "detailed_scope", "fee", "save_location", "a250_creator",
        ]
        values = {f: "" for f in fields}
        values["project_title"] = "MyProject"
        if overrides:
            values.update(overrides)
        return {k: Mock(text=Mock(return_value=v)) for k, v in values.items()}

    def test_render_called_with_all_fields(self, qapp, tmp_path):
        from app import FolderSetupApp
        window = FolderSetupApp()
        a250_vars = self._make_a250_vars()
        mock_doc = MagicMock()
        with patch("app.DocxTemplate", return_value=mock_doc):
            with patch("app.QMessageBox.critical"):
                with patch("subprocess.Popen"):
                    window._generate_a250(a250_vars)
        render_call = mock_doc.render.call_args[0][0]
        assert "project_title" in render_call
        assert "current_date" in render_call
        assert render_call["project_title"] == "MyProject"

    def test_output_filename_uses_project_title(self, qapp, tmp_path):
        from app import FolderSetupApp
        window = FolderSetupApp()
        a250_vars = self._make_a250_vars({"save_location": str(tmp_path)})
        mock_doc = MagicMock()
        with patch("app.DocxTemplate", return_value=mock_doc):
            with patch("subprocess.Popen"):
                window._generate_a250(a250_vars)
        save_call = mock_doc.save.call_args[0][0]
        assert "MyProject" in str(save_call)
        assert str(save_call).endswith(".docx")

    def test_save_location_used_when_provided(self, qapp, tmp_path):
        from app import FolderSetupApp
        window = FolderSetupApp()
        a250_vars = self._make_a250_vars({"save_location": str(tmp_path)})
        mock_doc = MagicMock()
        with patch("app.DocxTemplate", return_value=mock_doc):
            with patch("subprocess.Popen"):
                window._generate_a250(a250_vars)
        save_path = mock_doc.save.call_args[0][0]
        assert str(tmp_path) in str(save_path)

    def test_save_location_blank_falls_back_to_cwd(self, qapp):
        from app import FolderSetupApp
        window = FolderSetupApp()
        a250_vars = self._make_a250_vars({"save_location": ""})
        mock_doc = MagicMock()
        with patch("app.DocxTemplate", return_value=mock_doc):
            with patch("subprocess.Popen"):
                window._generate_a250(a250_vars)
        save_path = Path(mock_doc.save.call_args[0][0])
        assert save_path.parent == Path.cwd()

    def test_missing_template_shows_error_dialog(self, qapp):
        from app import FolderSetupApp
        window = FolderSetupApp()
        a250_vars = self._make_a250_vars()
        with patch("app.DocxTemplate", side_effect=FileNotFoundError("template not found")):
            with patch("app.QMessageBox.critical") as mock_dialog:
                window._generate_a250(a250_vars)
        mock_dialog.assert_called_once()
        call_args = mock_dialog.call_args[0]
        assert "Error" in call_args[1]
