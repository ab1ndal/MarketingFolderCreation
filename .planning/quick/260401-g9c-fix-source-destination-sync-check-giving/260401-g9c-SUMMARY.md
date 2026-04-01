---
phase: quick
plan: 260401-g9c
subsystem: operations/copy_ops
tags: [bug-fix, robocopy, tdd, copy-ops]
dependency_graph:
  requires: []
  provides: [correct-robocopy-exit-code-0-handling]
  affects: [workers/workflow_worker.py]
tech_stack:
  added: []
  patterns: [pre-capture destination existence flag before subprocess call]
key_files:
  created: []
  modified:
    - operations/copy_ops.py
    - tests/test_copy_ops.py
decisions:
  - Capture dst_existed_before as False (local, new) or None (network/unknown) — not True, because local pre-check already returns False early if dst exists
  - Network paths set dst_existed_before=None (unknown) so they always fall through to in-sync message, which is the safer default
  - No architectural changes required — single-function change within existing code structure
metrics:
  duration: ~5min
  completed: 2026-04-01
  tasks_completed: 1
  files_changed: 2
---

# Quick Task 260401-g9c: Fix Source/Destination Sync Check Giving False Positive

**One-liner:** Fixed robocopy exit-code 0 false-positive by tracking `dst_existed_before` to distinguish a newly created (empty-template) destination from a genuinely in-sync one.

---

## Objective

Robocopy exit code 0 is ambiguous — it means "nothing was copied" whether because the source template was empty (new destination created) or because the destination was already fully in sync. The old code always emitted the "already in sync" message, misleading users into thinking a new-folder copy was skipped.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED  | Add failing tests for new/in-sync distinction | 16837f2 | tests/test_copy_ops.py |
| GREEN | Implement dst_existed_before fix in copy_folder | e0e7d96 | operations/copy_ops.py |

---

## What Changed

### `operations/copy_ops.py`

After the network/local pre-existence check block, added:

```python
dst_existed_before = dst.exists() if not _is_network_path(dst) else None
```

In the `result.returncode == 0` branch, replaced single log call with:

```python
if dst_existed_before is False:
    log_func(f"Copied to new folder {dst} (source template is empty)", "warn")
else:
    log_func(f"Source and destination are already in sync (no files copied)", "info")
return True
```

### `tests/test_copy_ops.py`

- Updated `test_copy_folder_robocopy_returns_no_files`: dst not pre-created, now expects `"Copied to new folder {dst} (source template is empty)"` at `"warn"` level
- Added `test_copy_folder_robocopy_returns_no_files_dst_existed`: dst pre-created + `_is_network_path` patched to True, expects `"Source and destination are already in sync (no files copied)"` at `"info"` level

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Verification Results

- `python -m pytest tests/test_copy_ops.py -v` — 12 passed (was 11, new test added)
- `python -m pytest tests/ -v` — 48 passed, no regressions

---

## Self-Check: PASSED

- [x] `operations/copy_ops.py` exists and modified
- [x] `tests/test_copy_ops.py` exists and modified
- [x] Commit 16837f2 (RED) exists
- [x] Commit e0e7d96 (GREEN) exists
- [x] All 48 tests pass
