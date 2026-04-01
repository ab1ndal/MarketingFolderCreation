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

        # Patch pyperclip.copy to avoid clipboard contention errors in headless/CI environments
        with patch("app.pyperclip.copy"):
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

        # Patch QMessageBox.warning to avoid blocking dialog if workflow emits finished(False)
        with patch("app.QMessageBox.warning"):
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
