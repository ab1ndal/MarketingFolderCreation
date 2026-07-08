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
