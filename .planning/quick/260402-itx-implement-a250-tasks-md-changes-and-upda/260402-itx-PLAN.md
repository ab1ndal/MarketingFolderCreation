---
phase: quick-260402-itx
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app.py
  - tests/test_a250_generation.py
autonomous: true
requirements: [A250-01, A250-02, A250-03, A250-04, A250-05]

must_haves:
  truths:
    - "{{requested_by}} in the rendered doc contains client_name, client_license, client_title each on its own line, with a conditional extra newline before title when total length exceeds threshold"
    - "{{client_signed}} contains client_name and client_title, with conditional newline before title based on content length"
    - "{{invoice_to}} defaults to the same multi-line text as requested_by but can be overridden with custom text typed by the user"
    - "Principal, project manager, and fee type fields are QComboBox dropdowns populated from config options"
    - "Multi-line fields (project_description, detailed_scope, client_address) use QTextEdit for rich-text entry"
    - "All existing tests pass and new tests cover the composite field logic"
  artifacts:
    - path: "app.py"
      provides: "Updated A250 form with dropdowns, rich-text inputs, and composite field assembly"
    - path: "tests/test_a250_generation.py"
      provides: "Tests matching updated field names and composite field output"
  key_links:
    - from: "a250_vars dict (form widgets)"
      to: "_generate_a250 data assembly"
      via: "v.text() for QLineEdit / v.toPlainText() for QTextEdit / v.currentText() for QComboBox"
    - from: "client_name / client_license / client_title / client fields"
      to: "requested_by, client_signed, invoice_to template placeholders"
      via: "composite string construction with conditional \\n logic"
---

<objective>
Update the A250 form in app.py to:
1. Compose {{requested_by}}, {{client_signed}}, and {{invoice_to}} template fields from individual client sub-fields with conditional newline logic.
2. Replace QLineEdit with QComboBox for principal_name, project_manager, and fee_type (options already in config.py).
3. Replace QLineEdit with QTextEdit for rich-text multi-line fields: project_description, detailed_scope, client_address, invoice_to (custom override).
4. Update tests to match the new field names, widget types, and composite field output.

Purpose: The A250.docx template uses {{requested_by}}, {{client_signed}}, and {{invoice_to}} placeholders that require formatted multi-part content. The form must provide correct data shapes and allow rich text entry.
Output: Updated app.py and tests/test_a250_generation.py.
</objective>

<execution_context>
@C:/Users/abindal/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/abindal/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@app.py
@config.py
@tests/test_a250_generation.py

<interfaces>
<!-- From config.py — use these directly in QComboBox population -->
PRINCIPAL_OPTIONS = [
    "Choose a Principal",
    "Ryan Wilkerson, Principal, #S4728",
    "Michael Gemmill, Principal, #S4703",
    "Kelly Weldon, Principal, #S5780"
]
PROJECT_MANAGER_OPTIONS = [
    "Choose a Project Manager",
    "Anthony Giammona", "Jim Zeiner", "Kelly Weldon",
    "Michael Gemmill", "Owen Hata", "Ryan Wilkerson", "Sudharshan Navalpakkam"
]
FEE_TYPE_OPTIONS = [
    "LUMP SUM FEE",
    "TIME AND MATERIAL (N.T.E.)",
    "TIME AND MATERIAL ESTIMATED MAX",
    "TIME AND MATERIALS"
]

<!-- Current _generate_a250 uses: data = {k: v.text() for k, v in a250_vars.items()} -->
<!-- After change, must handle: QLineEdit (.text()), QTextEdit (.toPlainText()), QComboBox (.currentText()) -->
<!-- Composite fields are NOT form widgets — they are assembled in _generate_a250 from raw sub-fields -->

<!-- Current form field keys (in a250_vars): -->
<!-- Project Info: project_title, project_address, client, nya_project_code, client_project_code -->
<!-- Client Contact: client_name, client_title, client_license, client_phone, client_mobile, client_email -->
<!-- Billing: invoice_to, client_office_no, client_invoice_email, client_address -->
<!-- Scope & Fee: request_date, work_type, project_description, detailed_scope, fee_type, fee -->
<!-- Additional Info: principal_name, project_manager -->
<!-- Output: save_location, a250_creator -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update A250 form — dropdowns, rich-text fields, composite field assembly</name>
  <files>app.py</files>
  <action>
Make the following changes to `_open_a250_form` and `_generate_a250` in app.py:

**1. Import additions (top of file — already has QComboBox, confirm QTextEdit is imported):**
No new imports needed — QComboBox and QTextEdit are already imported.

**2. Widget type changes in `_open_a250_form`:**

The `groups` list currently creates a QLineEdit for every field. Change the loop so:

- Fields using `QComboBox` (populated from config): `principal_name`, `project_manager`, `fee_type`
  - Create a `QComboBox`, call `addItems(OPTIONS_LIST)` from config, store in `a250_vars[key]`
  - For `fee_type`, use `FEE_TYPE_OPTIONS`; for `principal_name`, use `PRINCIPAL_OPTIONS`; for `project_manager`, use `PROJECT_MANAGER_OPTIONS`
  - Use `form.addRow(label, combo)` instead of `form.addRow(label, line_edit)`

- Fields using `QTextEdit` (multi-line rich entry): `project_description`, `detailed_scope`, `client_address`, `invoice_to`
  - Create a `QTextEdit()`, set a fixed height of ~80px (`setFixedHeight(80)`), store in `a250_vars[key]`
  - Use `form.addRow(label, text_edit)`

- All other fields remain `QLineEdit` as before.

To implement cleanly, define sets at the top of `_open_a250_form`:
```python
COMBO_FIELDS = {
    "principal_name": PRINCIPAL_OPTIONS,
    "project_manager": PROJECT_MANAGER_OPTIONS,
    "fee_type": FEE_TYPE_OPTIONS,
}
MULTILINE_FIELDS = {"project_description", "detailed_scope", "client_address", "invoice_to"}
```

Then in the loop:
```python
for key, label in field_pairs:
    if key in COMBO_FIELDS:
        widget = QComboBox()
        widget.addItems(COMBO_FIELDS[key])
        form.addRow(label, widget)
    elif key in MULTILINE_FIELDS:
        widget = QTextEdit()
        widget.setFixedHeight(80)
        form.addRow(label, widget)
    else:
        widget = QLineEdit()
        form.addRow(label, widget)
    a250_vars[key] = widget
```

**3. Update `_generate_a250` — extract text from mixed widget types:**

Replace the current single-line dict comprehension:
```python
data = {k: v.text() for k, v in a250_vars.items()}
```

With a helper that handles all three widget types:
```python
def _get_val(w):
    if isinstance(w, QComboBox):
        return w.currentText()
    elif isinstance(w, QTextEdit):
        return w.toPlainText()
    else:
        return w.text()

data = {k: _get_val(v) for k, v in a250_vars.items()}
```

Define `_get_val` as a local function inside `_generate_a250` or as a module-level helper.

**4. Composite field assembly in `_generate_a250` — add AFTER building `data`:**

After `data = {k: _get_val(v) ...}`, assemble the three composite fields:

```python
# --- Composite: requested_by ---
# Format: client_name\nclient_license\nclient_title\nclient
# If total length of name+license+title > 60 chars, add extra \n before title
name    = data.get("client_name", "").strip()
license_ = data.get("client_license", "").strip()
title   = data.get("client_title", "").strip()
client  = data.get("client", "").strip()

title_sep = "\n\n" if len(name) + len(license_) + len(title) > 60 else "\n"
data["requested_by"] = f"{name}\n{license_}{title_sep}{title}\n{client}"

# --- Composite: client_signed ---
# Format: client_name, client_title (with conditional \n before title)
title_sep2 = "\n" if len(name) + len(title) > 40 else ", "
data["client_signed"] = f"{name}{title_sep2}{title}"

# --- Composite: invoice_to ---
# Default: same as requested_by. Override if user typed custom text in invoice_to field.
invoice_custom = data.get("invoice_to", "").strip()
if not invoice_custom:
    data["invoice_to"] = data["requested_by"]
# else leave data["invoice_to"] as the custom text the user entered
```

**5. Key name for date field:** The current code uses `data["today"]`. The test checks for `"current_date"`. Confirm which key the A250.docx template uses — to avoid breaking the existing template, keep `data["today"]` AND also set `data["current_date"] = data["today"]` so both are available.

Do NOT change the `doc.render(data)` or `doc.save(output_path)` logic.
  </action>
  <verify>
    <automated>cd C:\Users\abindal\Documents\00_Python\MarketingFolderCreation && .venv/Scripts/python.exe -c "import ast, sys; ast.parse(open('app.py').read()); print('app.py syntax OK')"</automated>
  </verify>
  <done>
- `_open_a250_form` renders QComboBox for principal_name, project_manager, fee_type
- `_open_a250_form` renders QTextEdit for project_description, detailed_scope, client_address, invoice_to
- `_generate_a250` correctly reads all three widget types
- `data["requested_by"]`, `data["client_signed"]`, `data["invoice_to"]` are computed composite strings
- Conditional extra newline before title fires when combined length exceeds threshold
- app.py has no syntax errors
  </done>
</task>

<task type="auto">
  <name>Task 2: Update tests for new field names, widget types, and composite field output</name>
  <files>tests/test_a250_generation.py</files>
  <action>
The existing tests use stale field names (`Fname_R`, `Lname_R`, `title_R`, `licenses`, `client_invoice`, `client_office`) that no longer exist in the form. The `_make_a250_vars` helper must be rebuilt to match the current field list, and tests must use the right mock `.text()` / `.toPlainText()` / `.currentText()` methods.

**1. Update `_make_a250_vars`:**

Replace the old `fields` list with the current canonical field list (matching `a250_vars` keys in app.py):

```python
LINE_EDIT_FIELDS = [
    "project_title", "project_address", "nya_project_code", "client_project_code",
    "client", "client_name", "client_title", "client_license",
    "client_phone", "client_mobile", "client_email",
    "client_office_no", "client_invoice_email",
    "request_date", "work_type", "fee", "save_location", "a250_creator",
]
COMBO_FIELDS = ["principal_name", "project_manager", "fee_type"]
MULTILINE_FIELDS = ["project_description", "detailed_scope", "client_address", "invoice_to"]
```

Build the mock dict:
```python
def _make_a250_vars(self, overrides=None):
    from PyQt6.QtWidgets import QLineEdit, QComboBox, QTextEdit
    vars_ = {}
    for f in LINE_EDIT_FIELDS:
        m = Mock(spec=QLineEdit)
        m.text = Mock(return_value="")
        vars_[f] = m
    for f in COMBO_FIELDS:
        m = Mock(spec=QComboBox)
        m.currentText = Mock(return_value="")
        vars_[f] = m
    for f in MULTILINE_FIELDS:
        m = Mock(spec=QTextEdit)
        m.toPlainText = Mock(return_value="")
        vars_[f] = m
    vars_["project_title"].text = Mock(return_value="MyProject")
    if overrides:
        for k, v in overrides.items():
            if k in vars_:
                widget = vars_[k]
                # Set the right method based on widget type
                if hasattr(widget, 'toPlainText'):
                    widget.toPlainText = Mock(return_value=v)
                elif hasattr(widget, 'currentText'):
                    widget.currentText = Mock(return_value=v)
                else:
                    widget.text = Mock(return_value=v)
    return vars_
```

**2. Update `test_render_called_with_all_fields`:**

The test checks `render_call["current_date"]`. Keep this check. Also add assertions for the composite fields:
```python
assert "requested_by" in render_call
assert "client_signed" in render_call
assert "invoice_to" in render_call
```
Remove the assertion `assert "current_date" in render_call` only if `_generate_a250` no longer sets it — but since Task 1 sets both `today` and `current_date`, keep it.

**3. Add test for composite field assembly:**

```python
def test_requested_by_composite_short(self, qapp, tmp_path):
    """Short name+license+title: single \\n before title."""
    from app import FolderSetupApp
    window = FolderSetupApp()
    a250_vars = self._make_a250_vars({
        "client_name": "Jane Doe",
        "client_license": "PE",
        "client_title": "Director",
        "client": "Acme Corp",
        "save_location": str(tmp_path),
    })
    mock_doc = MagicMock()
    with patch("app.DocxTemplate", return_value=mock_doc):
        with patch("subprocess.Popen"):
            window._generate_a250(a250_vars)
    render_data = mock_doc.render.call_args[0][0]
    req_by = render_data["requested_by"]
    assert "Jane Doe" in req_by
    assert "PE" in req_by
    assert "Director" in req_by
    assert "Acme Corp" in req_by
    # Short content: single newline before title (not double)
    assert "\n\n" not in req_by

def test_requested_by_composite_long(self, qapp, tmp_path):
    """Long name+license+title: double \\n before title."""
    from app import FolderSetupApp
    window = FolderSetupApp()
    a250_vars = self._make_a250_vars({
        "client_name": "Jonathan Alexander Smithsonian",
        "client_license": "PE, SE, LEED AP BD+C",
        "client_title": "Senior Vice President of Engineering",
        "client": "Big Corporation LLC",
        "save_location": str(tmp_path),
    })
    mock_doc = MagicMock()
    with patch("app.DocxTemplate", return_value=mock_doc):
        with patch("subprocess.Popen"):
            window._generate_a250(a250_vars)
    render_data = mock_doc.render.call_args[0][0]
    assert "\n\n" in render_data["requested_by"]

def test_invoice_to_defaults_to_requested_by(self, qapp, tmp_path):
    """Empty invoice_to defaults to requested_by composite."""
    from app import FolderSetupApp
    window = FolderSetupApp()
    a250_vars = self._make_a250_vars({
        "client_name": "Jane Doe",
        "client_license": "PE",
        "client_title": "Director",
        "client": "Acme Corp",
        "save_location": str(tmp_path),
        # invoice_to left empty (default)
    })
    mock_doc = MagicMock()
    with patch("app.DocxTemplate", return_value=mock_doc):
        with patch("subprocess.Popen"):
            window._generate_a250(a250_vars)
    render_data = mock_doc.render.call_args[0][0]
    assert render_data["invoice_to"] == render_data["requested_by"]

def test_invoice_to_custom_text(self, qapp, tmp_path):
    """Non-empty invoice_to uses custom text, not requested_by."""
    from app import FolderSetupApp
    window = FolderSetupApp()
    a250_vars = self._make_a250_vars({
        "invoice_to": "Custom Billing Address\nSuite 100",
        "save_location": str(tmp_path),
    })
    mock_doc = MagicMock()
    with patch("app.DocxTemplate", return_value=mock_doc):
        with patch("subprocess.Popen"):
            window._generate_a250(a250_vars)
    render_data = mock_doc.render.call_args[0][0]
    assert render_data["invoice_to"] == "Custom Billing Address\nSuite 100"
```

**4. Remove or update stale field assertions** in `test_render_called_with_all_fields` — remove any reference to old fields like `Fname_R`, `Lname_R`, `title_R` that no longer exist.

**5. Keep all existing structural tests** (`test_output_filename_uses_project_title`, `test_save_location_used_when_provided`, `test_save_location_blank_falls_back_to_cwd`, `test_missing_template_shows_error_dialog`) — they test save/path behavior that is unchanged. Only update their `_make_a250_vars()` calls if needed (the helper rebuild above makes them work automatically).
  </action>
  <verify>
    <automated>cd C:\Users\abindal\Documents\00_Python\MarketingFolderCreation && .venv/Scripts/python.exe -m pytest tests/test_a250_generation.py -v 2>&1</automated>
  </verify>
  <done>
- `_make_a250_vars` uses current field list with correct mock types (QLineEdit/QComboBox/QTextEdit specs)
- All 5 original tests pass
- 4 new composite field tests pass
- No references to stale field names (Fname_R, Lname_R, title_R, licenses, client_invoice, client_office)
  </done>
</task>

</tasks>

<verification>
Run full test suite after both tasks:

```bash
cd C:\Users\abindal\Documents\00_Python\MarketingFolderCreation && .venv/Scripts/python.exe -m pytest tests/test_a250_generation.py -v
```

All tests (original + new) must pass. No import errors.
</verification>

<success_criteria>
- QComboBox used for principal_name, project_manager, fee_type with config options pre-populated
- QTextEdit used for project_description, detailed_scope, client_address, invoice_to
- {{requested_by}} = "client_name\nclient_license\nclient_title\nclient" with double-\n before title when len(name+license+title) > 60
- {{client_signed}} = "client_name, client_title" or "client_name\nclient_title" when len > 40
- {{invoice_to}} = requested_by composite when blank, custom text otherwise
- All tests pass: pytest tests/test_a250_generation.py
</success_criteria>

<output>
After completion, create `.planning/quick/260402-itx-implement-a250-tasks-md-changes-and-upda/260402-itx-SUMMARY.md`
</output>
