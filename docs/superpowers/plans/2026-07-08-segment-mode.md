# Segment Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Create a Segment" mode that nests `NNNNN.XX` project segments under an existing primary folder (`<year>/<primary>/<segment>`) on both drives, deriving the year from the project number.

**Architecture:** Pure parsing/matching logic lives in a new `utils/segment.py` (no Qt, fully unit-testable). `WorkflowWorker` gains an optional `primary` argument and resolves the deeper target path. `app.py` adds a checkbox + primary dropdown, auto-populates the year in the target fields on name blur (both modes), scans `V:\<year>` for primaries in segment mode, and gates Run on a selected primary.

**Tech Stack:** Python 3, PyQt6, pytest + pytest-qt. Windows-only (robocopy, win32com).

## Global Constraints

- No new third-party dependencies — stdlib + existing PyQt6 only.
- Windows path semantics (`pathlib.Path`); drives like `V:\`, `W:\`.
- Year pivot is dynamic on the current year: `yy = int(NNNNN[:2])`; `cur = datetime.now().year % 100`; `yy <= cur → 2000+yy` else `1900+yy`.
- Primary match is leading-token exact: name starts with `NNNNN` AND the next char is not a digit.
- Tests use `tmp_path`; no real network drives. Mirror existing test style (pytest classes/functions, `unittest.mock`, `qtbot`/`qapp`).
- Normal (non-segment) behavior must stay byte-for-byte unchanged when the checkbox is off, except the year auto-populate which applies to both modes.

---

### Task 1: Pure segment logic (`utils/segment.py`)

**Files:**
- Create: `utils/segment.py`
- Test: `tests/test_segment.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `project_number(name: str) -> str | None` — leading digit run, else `None`.
  - `derive_year(name: str, current_year: int) -> int | None` — pivoted 4-digit year, else `None`.
  - `find_primary_folders(year_root: str, nnnnn: str) -> list[str]` — sorted folder names whose leading number token equals `nnnnn`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_segment.py`:

```python
import pytest
from utils.segment import project_number, derive_year, find_primary_folders


class TestProjectNumber:
    @pytest.mark.parametrize("name,expected", [
        ("12345.01 - Foundation", "12345"),
        ("25045 - Project Name", "25045"),
        ("  02031.BD  ", "02031"),
        ("89045", "89045"),
        ("No digits here", None),
        ("", None),
        (".01 leading dot", None),
    ])
    def test_extracts_leading_digit_run(self, name, expected):
        assert project_number(name) == expected


class TestDeriveYear:
    # current_year fixed at 2026 -> cur = 26
    @pytest.mark.parametrize("name,expected", [
        ("25045.01", 2025),
        ("02031", 2002),
        ("89045", 1989),
        ("99123", 1999),
        ("26123", 2026),
        ("27123", 1927),
        ("00999", 2000),
    ])
    def test_pivot_at_current_year(self, name, expected):
        assert derive_year(name, 2026) == expected

    def test_no_digits_returns_none(self):
        assert derive_year("Project", 2026) is None

    def test_single_digit_returns_none(self):
        assert derive_year("5 - foo", 2026) is None


class TestFindPrimaryFolders:
    def _mk(self, root, *names):
        for n in names:
            (root / n).mkdir()

    def test_exact_leading_token_match(self, tmp_path):
        self._mk(tmp_path, "12345 - Main Project", "99999 - Other")
        assert find_primary_folders(str(tmp_path), "12345") == ["12345 - Main Project"]

    def test_rejects_longer_number(self, tmp_path):
        self._mk(tmp_path, "12345 - Main", "123456 - Different")
        assert find_primary_folders(str(tmp_path), "12345") == ["12345 - Main"]

    def test_bare_number_folder_matches(self, tmp_path):
        self._mk(tmp_path, "12345")
        assert find_primary_folders(str(tmp_path), "12345") == ["12345"]

    def test_multiple_matches_sorted(self, tmp_path):
        self._mk(tmp_path, "12345 - Bravo", "12345.OLD - Alpha")
        assert find_primary_folders(str(tmp_path), "12345") == [
            "12345 - Bravo", "12345.OLD - Alpha",
        ]

    def test_ignores_files(self, tmp_path):
        (tmp_path / "12345 - file.txt").write_text("x")
        assert find_primary_folders(str(tmp_path), "12345") == []

    def test_missing_root_returns_empty(self, tmp_path):
        assert find_primary_folders(str(tmp_path / "nope"), "12345") == []

    def test_empty_nnnnn_returns_empty(self, tmp_path):
        (tmp_path / "12345 - Main").mkdir()
        assert find_primary_folders(str(tmp_path), "") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_segment.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'utils.segment'`.

- [ ] **Step 3: Write minimal implementation**

Create `utils/segment.py`:

```python
"""Pure parsing/matching helpers for Segment mode. No Qt, no I/O side effects."""
import re
from pathlib import Path


def project_number(name: str) -> str | None:
    """Return the leading run of digits in name (the project number), else None."""
    m = re.match(r"\d+", name.strip())
    return m.group(0) if m else None


def derive_year(name: str, current_year: int) -> int | None:
    """Derive a 4-digit year from the first two digits of the project number.

    Pivots on the current 2-digit year: yy <= cur -> 2000+yy, else 1900+yy.
    Returns None if there is no 2+ digit leading number.
    """
    num = project_number(name)
    if not num or len(num) < 2:
        return None
    yy = int(num[:2])
    cur = current_year % 100
    return 2000 + yy if yy <= cur else 1900 + yy


def find_primary_folders(year_root: str, nnnnn: str) -> list[str]:
    """List immediate subfolders of year_root whose leading number token == nnnnn.

    Match rule: folder name starts with nnnnn AND the following character is not
    a digit (so '12345' does not match '123456 - X'). Returns sorted names;
    empty list if nnnnn is empty or year_root is not a directory.
    """
    root = Path(year_root)
    if not nnnnn or not root.is_dir():
        return []
    matches = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(nnnnn):
            rest = name[len(nnnnn):]
            if not (rest and rest[0].isdigit()):
                matches.append(name)
    return sorted(matches)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_segment.py -v`
Expected: PASS (all cases).

- [ ] **Step 5: Commit**

```bash
git add utils/segment.py tests/test_segment.py
git commit -m "feat(segment): add year-derivation and primary-folder matching helpers"
```

---

### Task 2: Worker segment target + missing-primary warning (`workers/workflow_worker.py`)

**Files:**
- Modify: `workers/workflow_worker.py`
- Test: `tests/test_workflow_worker.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces:
  - `WorkflowWorker(project_name, paths, primary=None, parent=None)` — new optional `primary` kwarg.
  - `WorkflowWorker._resolve_targets() -> tuple[Path, Path]` — `(bd_target, work_target)`.
  - `WorkflowWorker._maybe_warn_missing_primary() -> None` — emits a `warn` log line if `primary` set and missing under the Work year root.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workflow_worker.py`:

```python
from pathlib import Path
from workers.workflow_worker import WorkflowWorker


def _worker(tmp_path, primary=None):
    paths = {
        "marketing_template": str(tmp_path / "mkt"),
        "work_template": str(tmp_path / "work"),
        "bd_target": str(tmp_path / "V" / "2025"),
        "work_target": str(tmp_path / "W" / "2025"),
    }
    return WorkflowWorker("12345.01 - Seg", paths, primary=primary)


class TestResolveTargets:
    def test_normal_mode(self, qapp, tmp_path):
        w = _worker(tmp_path)
        bd, work = w._resolve_targets()
        assert bd == tmp_path / "V" / "2025" / "12345.01 - Seg"
        assert work == tmp_path / "W" / "2025" / "12345.01 - Seg"

    def test_segment_mode_inserts_primary(self, qapp, tmp_path):
        w = _worker(tmp_path, primary="12345 - Main")
        bd, work = w._resolve_targets()
        assert bd == tmp_path / "V" / "2025" / "12345 - Main" / "12345.01 - Seg"
        assert work == tmp_path / "W" / "2025" / "12345 - Main" / "12345.01 - Seg"


class TestMissingPrimaryWarning:
    def _collect(self, w):
        logs = []
        w.log_message.connect(lambda msg, lvl: logs.append((msg, lvl)))
        return logs

    def test_warns_when_primary_missing_on_work(self, qapp, tmp_path):
        (tmp_path / "W" / "2025").mkdir(parents=True)
        w = _worker(tmp_path, primary="12345 - Main")
        logs = self._collect(w)
        w._maybe_warn_missing_primary()
        assert any(lvl == "warn" and "12345 - Main" in msg for msg, lvl in logs)

    def test_no_warn_when_primary_exists(self, qapp, tmp_path):
        (tmp_path / "W" / "2025" / "12345 - Main").mkdir(parents=True)
        w = _worker(tmp_path, primary="12345 - Main")
        logs = self._collect(w)
        w._maybe_warn_missing_primary()
        assert logs == []

    def test_no_warn_in_normal_mode(self, qapp, tmp_path):
        w = _worker(tmp_path)
        logs = self._collect(w)
        w._maybe_warn_missing_primary()
        assert logs == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_workflow_worker.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'primary'` (or `AttributeError` on `_resolve_targets`).

- [ ] **Step 3: Modify `__init__` to accept `primary`**

In `workers/workflow_worker.py`, change the constructor signature and store the value. Replace lines 27-38:

```python
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
```

- [ ] **Step 4: Add `_resolve_targets` and `_maybe_warn_missing_primary` helpers**

In `workers/workflow_worker.py`, add these two methods immediately after `_log` (after line 49):

```python
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
```

- [ ] **Step 5: Use the helpers in `run()`**

In `workers/workflow_worker.py`, replace the target-derivation lines at the top of `run()` (currently lines 54-56):

```python
            bd_target = Path(self.paths["bd_target"]) / self.project_name
            work_target = Path(self.paths["work_target"]) / self.project_name
            shortcut_name = FOLDER_TO_DELETE + ".lnk"
```

with:

```python
            bd_target, work_target = self._resolve_targets()
            self._maybe_warn_missing_primary()
            shortcut_name = FOLDER_TO_DELETE + ".lnk"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_workflow_worker.py -v`
Expected: PASS (all cases).

- [ ] **Step 7: Regression check existing worker/integration tests**

Run: `python -m pytest tests/test_integration.py -v`
Expected: PASS (normal mode unchanged).

- [ ] **Step 8: Commit**

```bash
git add workers/workflow_worker.py tests/test_workflow_worker.py
git commit -m "feat(segment): worker resolves nested target and warns on missing Work primary"
```

---

### Task 3: UI controls, year auto-populate, primary scan (`app.py`)

**Files:**
- Modify: `app.py`
- Test: `tests/test_segment_ui.py`

**Interfaces:**
- Consumes: `derive_year`, `project_number`, `find_primary_folders` from Task 1.
- Produces (attributes/methods used by Task 4):
  - `self.segment_checkbox: QCheckBox`
  - `self.primary_row: QWidget` (show/hide container)
  - `self.primary_combo: QComboBox`
  - `self.primary_hint: QLabel`
  - `self._apply_derived_year() -> None`
  - `self._scan_primaries() -> None`
  - `self._on_segment_toggled(checked: bool) -> None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_segment_ui.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_segment_ui.py -v`
Expected: FAIL — `AttributeError: 'FolderSetupApp' object has no attribute 'segment_checkbox'`.

- [ ] **Step 3: Add imports**

In `app.py`, add `re` and `QCheckBox` and the segment helpers. Change the import block:

Line 1-5 region — add `import re` after `import sys`:

```python
import sys
import re
import subprocess
```

In the `PyQt6.QtWidgets` import (lines 7-12), add `QCheckBox`:

```python
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QDialog, QScrollArea, QFormLayout,
    QDialogButtonBox, QGroupBox, QComboBox, QCheckBox
)
```

After the `from utils.web_editor import WebRichTextEditor` line region (after line 23), add:

```python
from utils.segment import derive_year, project_number, find_primary_folders
```

- [ ] **Step 4: Build the segment UI row**

In `app.py` `_build_ui`, insert immediately after the `name_hint` block (after `layout.addWidget(self.name_hint)`, line 81):

```python
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
        primary_layout.addWidget(self.primary_combo, stretch=1)
        layout.addWidget(self.primary_row)

        self.primary_hint = QLabel("")
        self.primary_hint.setStyleSheet("color: #c0392b;")
        self.primary_hint.setWordWrap(True)
        layout.addWidget(self.primary_hint)

        self.primary_row.setVisible(False)
        self.primary_hint.setVisible(False)
```

- [ ] **Step 5: Add the year/scan/toggle slots**

In `app.py`, add these methods after `_validate_name_field` (after line 169):

```python
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
```

- [ ] **Step 6: Trigger year/scan on name blur**

In `app.py` `eventFilter` (lines 153-157), extend the FocusOut branch:

```python
    def eventFilter(self, obj, event):
        """Validate the project name when the field loses focus (blur)."""
        if obj is self.project_name_field and event.type() == QEvent.Type.FocusOut:
            self._validate_name_field()
            self._apply_derived_year()
            if self.segment_checkbox.isChecked():
                self._scan_primaries()
        return super().eventFilter(obj, event)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/test_segment_ui.py -v`
Expected: PASS (all cases).

- [ ] **Step 8: Commit**

```bash
git add app.py tests/test_segment_ui.py
git commit -m "feat(segment): add segment checkbox, primary picker, year auto-populate and scan"
```

---

### Task 4: Run gating, wire primary into worker, clipboard path (`app.py`)

**Files:**
- Modify: `app.py`
- Test: `tests/test_integration.py` (extend)

**Interfaces:**
- Consumes: `self.segment_checkbox`, `self.primary_combo`, `self.primary_hint` (Task 3); `WorkflowWorker(..., primary=...)` (Task 2).
- Produces: gated `_run_workflow` and segment-aware clipboard path in `_on_workflow_finished`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_integration.py` (inside the file, after the existing class). These reuse the `_robocopy_available` guard already defined at module top:

```python
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

        with patch("app.pyperclip.copy"):
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_integration.py::TestSegmentWorkflow -v`
Expected: FAIL — nested folders not created (worker started without `primary`), and `test_run_blocked_when_no_primary` fails because the worker starts anyway.

- [ ] **Step 3: Gate Run and pass `primary` to the worker**

In `app.py` `_run_workflow`, after the `validate_paths` check and before `self.run_btn.setEnabled(False)` (i.e. after line 202), insert the segment gate and compute `primary`:

```python
        primary = None
        if self.segment_checkbox.isChecked():
            primary = self.primary_combo.currentText().strip()
            if not primary:
                self.primary_hint.setText(
                    "Select a primary folder before running (no matching primary found)."
                )
                self.write_log("Segment mode: no primary folder selected.", "error")
                return
```

Then change the worker construction (line 208) from:

```python
        self.worker = WorkflowWorker(project_name=name, paths=paths, parent=self)
```

to:

```python
        self.worker = WorkflowWorker(project_name=name, paths=paths, primary=primary, parent=self)
```

- [ ] **Step 4: Make the clipboard path segment-aware**

In `app.py` `_on_workflow_finished`, replace the `work_target` computation (lines 225-228):

```python
            work_target = (
                Path(self.path_fields["work_target"].text().strip())
                / self.project_name_field.text().strip()
            )
```

with:

```python
            parts = [self.path_fields["work_target"].text().strip()]
            if self.segment_checkbox.isChecked() and self.primary_combo.currentText().strip():
                parts.append(self.primary_combo.currentText().strip())
            parts.append(self.project_name_field.text().strip())
            work_target = Path(*parts)
```

- [ ] **Step 5: Run the new tests to verify they pass**

Run: `python -m pytest tests/test_integration.py::TestSegmentWorkflow -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite for regressions**

Run: `python -m pytest tests/ -q`
Expected: PASS (all existing tests + new).

- [ ] **Step 7: Commit**

```bash
git add app.py tests/test_integration.py
git commit -m "feat(segment): gate Run on primary selection, nest target, fix clipboard path"
```

---

## Self-Review

**Spec coverage:**
- Year derivation (pivot at current year, both modes, populate both fields) → Task 1 (`derive_year`) + Task 3 (`_apply_derived_year`). ✓
- Checkbox + primary dropdown, reuse name field → Task 3. ✓
- Scan V: on blur, 1/many/zero handling, block on zero → Task 3 (`_scan_primaries`) + Task 4 (gate). ✓
- Leading-token exact match → Task 1 (`find_primary_folders`). ✓
- Same 4-step workflow one level deeper → Task 2 (`_resolve_targets`). ✓
- Warn (not block) when primary missing on Work drive → Task 2 (`_maybe_warn_missing_primary`). ✓
- `validate_folder_name` unchanged (dots legal) → no task needed; segment name still validated in existing `_run_workflow` path. ✓
- Clipboard uses deeper path → Task 4. ✓
- A250 untouched → no task. ✓

**Placeholder scan:** No TBD/TODO; every code step has full code. ✓

**Type consistency:** `primary` (`str | None`) consistent across Tasks 2–4; `_resolve_targets`, `_maybe_warn_missing_primary`, `_apply_derived_year`, `_scan_primaries`, `_on_segment_toggled` names consistent between producing and consuming tasks. Helper names `derive_year`/`project_number`/`find_primary_folders` match Task 1 exactly. ✓
