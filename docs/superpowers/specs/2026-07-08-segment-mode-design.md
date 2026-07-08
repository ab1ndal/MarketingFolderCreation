# Segment Mode — Design Spec

**Date:** 2026-07-08
**Component:** MarketingFolderCreation (PyQt6 folder setup tool)
**Status:** Approved design, pending spec review

---

## Problem

Today the tool creates one top-level project folder per year root:

- BD:   `V:\<year>\<name>`
- Work: `W:\<year>\<name>`

Sometimes a new project number is a **segment** of an existing project —
`NNNNN.00`, `NNNNN.01`, `NNNNN.10`, `NNNNN.BD`, etc. These should NOT get a new
top-level folder under the year. Instead they nest under the existing primary
project folder:

- BD:   `V:\<year>\<primary>\<segment>`
- Work: `W:\<year>\<primary>\<segment>`

The user needs a way to (a) flag segment mode, (b) find the correct primary
folder, and (c) run the same setup workflow one level deeper.

Additionally, the `<year>` folder is **not** the current year — it is encoded
in the project number and must be derived.

---

## Year derivation (applies to BOTH normal and segment mode)

The first two digits of the project number encode the year. The firm has
operated since 1989, and project numbers are assigned by accounting based on
address and can reach far back, so a century pivot is required.

- Extract the **project number** = leading digit run of the name:
  `re.match(r"\d+", name.strip())`. For `12345.01 - Foundation` → `12345`;
  for `25045 - Project Name` → `25045`.
- `yy = int(project_number[:2])`.
- **Pivot at the current 2-digit year** (dynamic): let `cur = datetime.now().year % 100`.
  - `yy <= cur` → year = `2000 + yy`
  - `yy >  cur` → year = `1900 + yy`
- Examples (current year 2026, `cur = 26`): `25045`→2025, `02031`→2002,
  `89045`→1989, `99xxx`→1999.

**Path population:** on project-name blur, if a year can be derived, rewrite the
`<year>` segment of BOTH the BD Target and Work Target fields:
- If the field's last path component matches `^(19|20)\d{2}$`, replace it with
  the derived year.
- Otherwise append the derived year.

This keeps the user-chosen root (`V:\`, `W:\`) intact while correcting the year.
If no leading digits exist, leave the fields untouched.

---

## UI changes (`app.py`)

Add a row above the path fields:

- **Checkbox "Create a Segment"** — unchecked = today's behavior, nothing changes.
- When checked, reveal a **Primary Folder** row: a read-only `QComboBox`,
  initially empty and disabled until a scan runs.

The existing **"Project Folder Name"** field is reused:
- Normal mode: the top-level folder name (as today).
- Segment mode: the full segment folder name, e.g. `12345.01 - Foundation Package`.

The whole entered string becomes the created folder name; parsing only reads the
leading digits for year + primary matching.

---

## Matching logic (new `utils/segment.py`)

Pure functions, no Qt, unit-testable:

- `derive_year(name: str, now_year: int) -> int | None`
  Returns the pivoted 4-digit year, or `None` if no leading digits.
- `project_number(name: str) -> str | None`
  Returns the leading digit run (`NNNNN`), or `None`.
- `find_primary_folders(year_root: str, nnnnn: str) -> list[str]`
  Lists immediate subfolders of `year_root` whose **leading number token equals
  `nnnnn`** — name starts with `nnnnn` AND the next character is not a digit
  (so `12345` does not match `123456 - X`). Returns folder names, sorted.
  Returns `[]` if `year_root` doesn't exist.

Trigger (segment mode only), on segment-name **blur** and on checkbox toggle:

1. Derive `nnnnn`. If empty/non-numeric → clear dropdown, disable it.
2. Scan the **BD Target** field value (`V:\<derived year>`) via
   `find_primary_folders`.
3. Populate dropdown:
   - **1 match** → auto-select it.
   - **>1 matches** → list all; user picks.
   - **0 matches** → inline red hint
     (`No primary folder starting with <nnnnn> found in <path>`), dropdown stays
     empty, and **Run is blocked**.

Scan source is the **BD Target (V:)** field only. The same primary folder name is
reused on the Work drive.

---

## Workflow changes (`workers/workflow_worker.py`)

`WorkflowWorker.__init__` gains an optional `primary: str | None` argument
(default `None`). In `run()`:

- Segment mode (`primary` set):
  - `bd_target   = Path(paths["bd_target"])   / primary / project_name`
  - `work_target = Path(paths["work_target"]) / primary / project_name`
- Normal mode (`primary is None`): unchanged.

Everything else is identical: parallel BD + Work template copy, delete
`1 Marketing`, create shortcut.

**Missing primary on Work drive:** the V: scan guarantees the primary exists on
the BD drive (0 matches blocks Run, so a primary is never created on V:). The
primary is expected to already exist under `W:\<year>` as well. Before starting
the copy, the worker checks `W:\<year>\<primary>`; if missing, it emits a
**warning** log line (`Primary <primary> not found on Work drive; it will be
created`) and continues — `robocopy` creates the intermediate `<primary>` level
using the same name, keeping the two drives consistent. Run is NOT blocked in
this case.

---

## Validation / gating (`app.py`, `utils/validate.py`)

- Segment name still runs `validate_folder_name`. Dots are legal in Windows
  folder names, so `validate_folder_name` needs **no change**.
- `_run_workflow`: if segment mode is ON and no primary is selected (0 matches or
  not yet scanned) → show inline error and do NOT start the worker.
- Pass the selected primary into `WorkflowWorker` when in segment mode.
- Final clipboard copy uses the deeper `work_target`
  (`W:\<year>\<primary>\<segment>`).

---

## Out of scope

- A250 fee-proposal dialog — unaffected.
- Renaming / moving existing folders — this only creates new ones.

---

## Testing

New `tests/test_segment.py` (pure functions, no drives needed):

- `derive_year`: pivot boundaries — `25045`→2025, `02031`→2002, `89045`→1989,
  `99xxx`→1999, `26xxx`→2026, `27xxx`→1927; no-digit input → `None`.
- `project_number`: extracts leading run, stops at `.`, space, or dash; `None`
  when no leading digit.
- `find_primary_folders` (using `tmp_path`): exact leading-token match, rejects
  `123456` for query `12345`, sorted output, missing root → `[]`, multiple matches.

Extend existing worker tests to cover the segment target path
(`year/primary/segment`) with mocked copy/delete/shortcut ops.
