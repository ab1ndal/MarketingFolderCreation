import pytest
from unittest.mock import Mock, patch
from utils.validate import validate_paths


class TestValidatePaths:

    def test_all_paths_exist_returns_true(self, tmp_path, mock_log_func):
        paths = {
            "marketing_template": str(tmp_path),
            "work_template": str(tmp_path),
            "bd_target": str(tmp_path),
            "work_target": str(tmp_path),
        }
        with patch("utils.validate.QMessageBox.critical") as mock_dialog:
            result = validate_paths(paths, mock_log_func)
        assert result is True
        mock_dialog.assert_not_called()
        mock_log_func.assert_not_called()

    def test_missing_path_returns_false_and_shows_dialog(self, tmp_path, mock_log_func):
        paths = {
            "marketing_template": str(tmp_path / "nonexistent"),
            "work_template": str(tmp_path),
            "bd_target": str(tmp_path),
            "work_target": str(tmp_path),
        }
        with patch("utils.validate.QMessageBox.critical") as mock_dialog:
            result = validate_paths(paths, mock_log_func)
        assert result is False
        mock_dialog.assert_called_once()
        call_args = mock_dialog.call_args
        assert "BD Template" in call_args[0][2]   # message contains human label

    def test_missing_path_calls_log_func(self, tmp_path, mock_log_func):
        paths = {
            "marketing_template": str(tmp_path / "nonexistent"),
        }
        with patch("utils.validate.QMessageBox.critical"):
            result = validate_paths(paths, mock_log_func)
        assert result is False
        mock_log_func.assert_called_once()
        call_args = mock_log_func.call_args[0]
        assert "BD Template" in call_args[0]

    def test_empty_string_path_returns_false(self, mock_log_func):
        paths = {"marketing_template": ""}
        with patch("utils.validate.QMessageBox.critical"):
            result = validate_paths(paths, mock_log_func)
        assert result is False

    @pytest.mark.parametrize("key,expected_label", [
        ("marketing_template", "BD Template"),
        ("work_template", "Work Template"),
        ("bd_target", "BD Target (V:)"),
        ("work_target", "Work Target (W:)"),
    ])
    def test_each_key_shows_correct_label(self, tmp_path, mock_log_func, key, expected_label):
        paths = {key: str(tmp_path / "nonexistent")}
        with patch("utils.validate.QMessageBox.critical") as mock_dialog:
            validate_paths(paths, mock_log_func)
        call_args = mock_dialog.call_args
        assert expected_label in call_args[0][2]

    def test_stops_at_first_failure(self, tmp_path, mock_log_func):
        """Only the first missing path triggers dialog; second path not checked."""
        paths = {
            "marketing_template": str(tmp_path / "bad1"),
            "work_template": str(tmp_path / "bad2"),
        }
        with patch("utils.validate.QMessageBox.critical") as mock_dialog:
            result = validate_paths(paths, mock_log_func)
        assert result is False
        assert mock_dialog.call_count == 1
        assert mock_log_func.call_count == 1
