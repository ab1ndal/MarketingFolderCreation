import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from config import FOLDER_TO_DELETE
from operations.copy_ops import copy_folder
from operations.delete_ops import delete_folder
from operations.shortcut_ops import create_shortcut


class WorkflowWorker(QThread):
    """
    Background worker that runs the 4-step folder setup workflow.

    Signals:
        progress(int, str): Emitted at each step. int = 0-100, str = plain-English description.
        log_message(str, str): Emitted for each operation log line. str1 = message, str2 = level.
        finished(bool): Emitted when complete. bool = True for success, False for error/cancel.
    """

    progress = pyqtSignal(int, str)
    log_message = pyqtSignal(str, str)
    finished = pyqtSignal(bool)

    def __init__(self, project_name: str, paths: dict, primary: str | None = None, parent=None):
        """
        Args:
            project_name: The project folder name entered by the user.
            paths: Dict with keys marketing_template, work_template, bd_target, work_target.
                   All values are strings (raw paths from UI fields).
            primary: In segment mode, the primary folder name to nest under; None otherwise.
            parent: Optional QObject parent.
        """
        super().__init__(parent)
        self.project_name = project_name
        self.paths = paths
        self.primary = primary
        self._cancel_event = threading.Event()

    def cancel(self):
        """Request cancellation. Worker checks this between steps and stops early."""
        self._cancel_event.set()

    def _is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def _log(self, message: str, level: str = "info"):
        """Emit a log_message signal (thread-safe via Qt signal)."""
        self.log_message.emit(message, level)

    def _resolve_targets(self):
        """Return (bd_target, work_target) Paths, inserting the primary folder in segment mode."""
        bd_root = Path(self.paths["bd_target"])
        work_root = Path(self.paths["work_target"])
        if self.primary:
            return (
                bd_root / self.primary / self.project_name,
                work_root / self.primary / self.project_name,
            )
        return (bd_root / self.project_name, work_root / self.project_name)

    def _maybe_warn_missing_primary(self):
        """Warn (but do not block) if the primary is missing under the Work year root."""
        if self.primary:
            work_primary = Path(self.paths["work_target"]) / self.primary
            if not work_primary.exists():
                self._log(
                    f"Primary '{self.primary}' not found on Work drive; it will be created",
                    "warn",
                )

    def run(self):
        """Main worker body. Runs in background thread."""
        try:
            bd_target, work_target = self._resolve_targets()
            self._maybe_warn_missing_primary()
            shortcut_name = FOLDER_TO_DELETE + ".lnk"

            # Step 1+2: Copy BD template and Work template in PARALLEL
            self.progress.emit(10, "Copying BD and Work templates...")
            if self._is_cancelled():
                self.finished.emit(False)
                return

            bd_success = False
            work_success = False

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_bd = executor.submit(
                    copy_folder,
                    self.paths["marketing_template"],
                    bd_target,
                    self._log,
                )
                future_work = executor.submit(
                    copy_folder,
                    self.paths["work_template"],
                    work_target,
                    self._log,
                )
                for future in as_completed([future_bd, future_work]):
                    result = future.result()
                    if future is future_bd:
                        bd_success = result
                    else:
                        work_success = result

            self.progress.emit(60, "Templates copied.")

            if self._is_cancelled():
                self.finished.emit(False)
                return

            # Step 3: Delete "1 Marketing" subfolder from work copy
            self.progress.emit(65, "Removing Marketing subfolder from Work copy...")
            delete_folder(work_target / FOLDER_TO_DELETE, self._log)
            self.progress.emit(80, "Marketing subfolder removed.")

            if self._is_cancelled():
                self.finished.emit(False)
                return

            # Step 4: Create shortcut in work folder pointing to BD folder
            self.progress.emit(85, "Creating shortcut to BD folder...")
            create_shortcut(bd_target, work_target / shortcut_name, self._log)
            self.progress.emit(100, "Setup complete.")

            self.finished.emit(True)

        except Exception as e:
            self._log(f"Workflow failed unexpectedly: {e}", "error")
            self.finished.emit(False)
