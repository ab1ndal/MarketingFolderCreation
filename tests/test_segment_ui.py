import re
from pathlib import Path
import pytest
from app import FolderSetupApp


@pytest.fixture
def window(qtbot):
    w = FolderSetupApp()
    qtbot.addWidget(w)
    return w


class TestSegmentToggle:
    def test_primary_row_hidden_by_default(self, window):
        assert window.segment_checkbox.isChecked() is False
        assert window.primary_row.isVisible() is False

    def test_toggle_shows_primary_row(self, window, qtbot):
        window.show()
        window.segment_checkbox.setChecked(True)
        assert window.primary_row.isVisible() is True
        window.segment_checkbox.setChecked(False)
        assert window.primary_row.isVisible() is False


class TestDerivedYear:
    def test_rewrites_year_segment_both_fields(self, window):
        window.path_fields["bd_target"].setText(r"V:\2099")
        window.path_fields["work_target"].setText(r"W:\2099")
        window.project_name_field.setText("25045.01 - Seg")
        window._apply_derived_year()
        assert Path(window.path_fields["bd_target"].text()).parts[-1] == "2025"
        assert Path(window.path_fields["work_target"].text()).parts[-1] == "2025"

    def test_no_digits_leaves_fields_untouched(self, window):
        window.path_fields["bd_target"].setText(r"V:\2026")
        window.project_name_field.setText("Project Without Number")
        window._apply_derived_year()
        assert window.path_fields["bd_target"].text() == r"V:\2026"


class TestScanPrimaries:
    def test_single_match_auto_selected(self, window, tmp_path):
        (tmp_path / "12345 - Main").mkdir()
        window.path_fields["bd_target"].setText(str(tmp_path))
        window.project_name_field.setText("12345.01 - Seg")
        window._scan_primaries()
        assert window.primary_combo.isEnabled() is True
        assert window.primary_combo.count() == 1
        assert window.primary_combo.currentText() == "12345 - Main"
        assert window.primary_hint.text() == ""

    def test_multiple_matches_listed(self, window, tmp_path):
        (tmp_path / "12345 - Bravo").mkdir()
        (tmp_path / "12345.OLD - Alpha").mkdir()
        window.path_fields["bd_target"].setText(str(tmp_path))
        window.project_name_field.setText("12345.01 - Seg")
        window._scan_primaries()
        assert window.primary_combo.count() == 2

    def test_zero_matches_shows_hint_and_disables(self, window, tmp_path):
        window.path_fields["bd_target"].setText(str(tmp_path))
        window.project_name_field.setText("77777.01 - Seg")
        window._scan_primaries()
        assert window.primary_combo.count() == 0
        assert window.primary_combo.isEnabled() is False
        assert "77777" in window.primary_hint.text()
