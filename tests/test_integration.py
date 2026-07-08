"""
Integration tests for the full user workflow:
fill project name -> click Run -> wait for finished signal -> verify folder structure on disk.

All filesystem operations run against a temporary directory (no real network drives touched).
Requires robocopy (Windows) and pywin32. Tests are skipped if robocopy is unavailable.
"""

import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox


def _robocopy_available():
    """Return True if robocopy is available (Windows only)."""
    try:
        result = subprocess.run(["robocopy", "/?"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.mark.skipif(not _robocopy_available(), reason="robocopy not available")
class TestWorkflowIntegration:

    def _setup_temp_dirs(self, tmp_path):
        """Create the minimal folder structure the worker needs."""
        mkt = tmp_path / "marketing_template"
        mkt.mkdir()
        (mkt / "1 Marketing").mkdir()
        (mkt / "SomeFile.txt").write_text("marketing content")

        work = tmp_path / "work_template"
        work.mkdir()
        (work / "1 Marketing").mkdir()
        (work / "WorkFile.txt").write_text("work content")

        bd_target = tmp_path / "bd_target"
        bd_target.mkdir()

        work_target = tmp_path / "work_target"
        work_target.mkdir()

        return mkt, work, bd_target, work_target

    def test_happy_path_creates_correct_folder_structure(self, qtbot, tmp_path):
        from app import FolderSetupApp
        mkt, work, bd_target, work_target = self._setup_temp_dirs(tmp_path)

        window = FolderSetupApp()
        qtbot.addWidget(window)
        window.show()

        project_name = "TestProject"
        window.project_name_field.setText(project_name)
        window.path_fields["marketing_template"].setText(str(mkt))
        window.path_fields["work_template"].setText(str(work))
        window.path_fields["bd_target"].setText(str(bd_target))
        window.path_fields["work_target"].setText(str(work_target))

        # Patch pyperclip.copy to avoid clipboard contention errors in headless/CI environments.
        # Long tmp paths trip the path-length guard, so auto-confirm it.
        with patch("app.pyperclip.copy"), \
             patch("app.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            qtbot.mouseClick(window.run_btn, Qt.MouseButton.LeftButton)

            # Wait for the worker.finished signal (timeout 30s for robocopy)
            with qtbot.waitSignal(window.worker.finished, timeout=30000) as blocker:
                pass

        assert blocker.args[0] is True, "Worker finished with failure — check log"

        bd_dir = bd_target / project_name
        work_dir = work_target / project_name

        assert bd_dir.exists(), f"BD folder not created: {bd_dir}"
        assert work_dir.exists(), f"Work folder not created: {work_dir}"
        assert not (work_dir / "1 Marketing").exists(), "'1 Marketing' subfolder should have been deleted"
        assert (work_dir / "1 Marketing.lnk").exists(), "Shortcut to BD folder should exist"

    def test_cancel_during_run_does_not_crash(self, qtbot, tmp_path):
        from app import FolderSetupApp
        mkt, work, bd_target, work_target = self._setup_temp_dirs(tmp_path)

        window = FolderSetupApp()
        qtbot.addWidget(window)
        window.show()

        window.project_name_field.setText("CancelProject")
        window.path_fields["marketing_template"].setText(str(mkt))
        window.path_fields["work_template"].setText(str(work))
        window.path_fields["bd_target"].setText(str(bd_target))
        window.path_fields["work_target"].setText(str(work_target))

        # Patch QMessageBox.warning to avoid blocking dialog if workflow emits finished(False).
        # Long tmp paths trip the path-length guard, so auto-confirm it.
        with patch("app.QMessageBox.warning"), \
             patch("app.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            qtbot.mouseClick(window.run_btn, Qt.MouseButton.LeftButton)

            # Cancel immediately after starting (worker may still be running or may have finished)
            if window.cancel_btn.isEnabled():
                qtbot.mouseClick(window.cancel_btn, Qt.MouseButton.LeftButton)

            # Wait for run_btn to be re-enabled — that happens in _on_workflow_finished
            # regardless of whether the run succeeded or was cancelled.
            # This avoids the race condition where a fast robocopy completes before
            # waitSignal is registered (leading to a 30s false timeout).
            qtbot.waitUntil(lambda: window.run_btn.isEnabled(), timeout=30000)

        # After finish (success or cancel): run_btn must be re-enabled, cancel disabled
        assert window.run_btn.isEnabled(), "run_btn should be re-enabled after finish"
        assert not window.cancel_btn.isEnabled(), "cancel_btn should be disabled after finish"


@pytest.mark.skipif(not _robocopy_available(), reason="robocopy not available")
class TestSegmentWorkflow:

    def _setup(self, tmp_path):
        mkt = tmp_path / "marketing_template"; mkt.mkdir()
        (mkt / "1 Marketing").mkdir()
        (mkt / "SomeFile.txt").write_text("m")
        work = tmp_path / "work_template"; work.mkdir()
        (work / "1 Marketing").mkdir()
        (work / "WorkFile.txt").write_text("w")
        # Year roots + existing primary on BD only
        bd_year = tmp_path / "V" / "2025"; bd_year.mkdir(parents=True)
        (bd_year / "12345 - Main Project").mkdir()
        work_year = tmp_path / "W" / "2025"; work_year.mkdir(parents=True)
        return mkt, work, bd_year, work_year

    def test_segment_creates_nested_structure(self, qtbot, tmp_path):
        from app import FolderSetupApp
        mkt, work, bd_year, work_year = self._setup(tmp_path)
        window = FolderSetupApp()
        qtbot.addWidget(window)
        window.show()

        window.path_fields["marketing_template"].setText(str(mkt))
        window.path_fields["work_template"].setText(str(work))
        window.path_fields["bd_target"].setText(str(bd_year))
        window.path_fields["work_target"].setText(str(work_year))
        window.segment_checkbox.setChecked(True)
        window.project_name_field.setText("12345.01 - Foundation")
        window._scan_primaries()
        assert window.primary_combo.currentText() == "12345 - Main Project"

        with patch("app.pyperclip.copy"), \
             patch("app.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            qtbot.mouseClick(window.run_btn, Qt.MouseButton.LeftButton)
            with qtbot.waitSignal(window.worker.finished, timeout=30000) as blocker:
                pass

        assert blocker.args[0] is True
        seg_bd = bd_year / "12345 - Main Project" / "12345.01 - Foundation"
        seg_work = work_year / "12345 - Main Project" / "12345.01 - Foundation"
        assert seg_bd.exists()
        assert seg_work.exists()
        assert not (seg_work / "1 Marketing").exists()
        assert (seg_work / "1 Marketing.lnk").exists()

    def test_run_blocked_when_no_primary(self, qtbot, tmp_path):
        from app import FolderSetupApp
        mkt, work, bd_year, work_year = self._setup(tmp_path)
        window = FolderSetupApp()
        qtbot.addWidget(window)
        window.show()
        window.path_fields["marketing_template"].setText(str(mkt))
        window.path_fields["work_template"].setText(str(work))
        window.path_fields["bd_target"].setText(str(bd_year))
        window.path_fields["work_target"].setText(str(work_year))
        window.segment_checkbox.setChecked(True)
        window.project_name_field.setText("77777.01 - NoMatch")
        window._scan_primaries()

        qtbot.mouseClick(window.run_btn, Qt.MouseButton.LeftButton)
        assert window.worker is None  # worker never started
        assert window.primary_hint.text() != ""


class TestPathLengthGuard:
    """The path-length guard runs before the worker starts, so no robocopy needed."""

    def _setup_long_template(self, tmp_path):
        longname = "L" * 200  # single component well within 255, deep enough to trip guard
        mkt = tmp_path / "mkt"
        (mkt / longname).mkdir(parents=True)
        (mkt / longname / "f.txt").write_text("x")
        work = tmp_path / "work"
        (work / longname).mkdir(parents=True)
        (work / longname / "f.txt").write_text("x")
        bd_target = tmp_path / "V"; bd_target.mkdir()
        work_target = tmp_path / "W"; work_target.mkdir()
        return mkt, work, bd_target, work_target

    def _fill(self, window, mkt, work, bd_target, work_target, name):
        window.path_fields["marketing_template"].setText(str(mkt))
        window.path_fields["work_template"].setText(str(work))
        window.path_fields["bd_target"].setText(str(bd_target))
        window.path_fields["work_target"].setText(str(work_target))
        window.project_name_field.setText(name)

    def test_long_path_prompts_and_cancel_stops_run(self, qtbot, tmp_path):
        from app import FolderSetupApp
        mkt, work, bd_target, work_target = self._setup_long_template(tmp_path)
        window = FolderSetupApp()
        qtbot.addWidget(window)
        self._fill(window, mkt, work, bd_target, work_target, "Proj")

        with patch("app.QMessageBox.question",
                   return_value=QMessageBox.StandardButton.No) as q:
            window._run_workflow()

        q.assert_called_once()
        assert window.worker is None

    def test_short_path_does_not_prompt(self, qtbot, tmp_path):
        from app import FolderSetupApp
        # Shallow templates + short synthetic target => guard must not fire,
        # regardless of PATH_LENGTH_MARGIN. Real tmp paths are long, so use short bases.
        mkt = tmp_path / "mkt"; mkt.mkdir(); (mkt / "a.txt").write_text("x")
        work = tmp_path / "work"; work.mkdir(); (work / "b.txt").write_text("x")
        window = FolderSetupApp()
        qtbot.addWidget(window)
        paths = {
            "marketing_template": str(mkt),
            "work_template": str(work),
            "bd_target": r"V:\2025",
            "work_target": r"W:\2025",
        }

        with patch("app.QMessageBox.question") as q:
            proceed = window._confirm_path_length(paths, "Proj", None)
        q.assert_not_called()
        assert proceed is True
