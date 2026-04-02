---
phase: quick-260402-jpl
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - templates/A250.docx
autonomous: true
requirements:
  - fix-a250-template-syntax
must_haves:
  truths:
    - "Clicking Generate A250 with any valid inputs no longer raises an error dialog"
    - "The generated .docx contains the nya_project_code value in the correct table cell"
  artifacts:
    - path: "templates/A250.docx"
      provides: "Valid Jinja2/docxtpl template with all tags properly closed"
      contains: "{{nya_project_code}}"
  key_links:
    - from: "templates/A250.docx Table0 Row4 Col5"
      to: "DocxTemplate.render()"
      via: "Jinja2 template parsing"
      pattern: "\\{\\{nya_project_code\\}\\}"
---

<objective>
Fix the "Unexpected }" TemplateSyntaxError that fires when the user clicks "Generate A250".

Purpose: The A250 template file has a malformed Jinja2 tag — `{{nya_project_code}` (single closing brace) instead of `{{nya_project_code}}` (double closing brace) in Table 0, Row 4, Col 5. docxtpl's Jinja2 parser sees the unbalanced brace and raises TemplateSyntaxError before any document is written.

Root cause confirmed by:
- `DocxTemplate('templates/A250.docx').get_undeclared_template_variables()` raises `TemplateSyntaxError: unexpected '}'`
- Inspecting the cell at run level: Run 0=`{{`, Run 1=`nya_project_code`, Run 2=`}` (only one closing brace)

Output: Repaired A250.docx where every `{{variable}}` tag has both braces closed, plus a regression test.
</objective>

<execution_context>
@C:/Users/abindal/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/abindal/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md

Relevant source: app.py `_generate_a250` method (lines 302–344) — calls `DocxTemplate(template_path).render(data)`.
The error is thrown at `doc.render(data)`, not in app.py code itself.

Bug location: `templates/A250.docx` — Table 0, Row 4, Col 5
Broken text:  `{{nya_project_code}`   ← single closing brace
Fixed text:   `{{nya_project_code}}`  ← double closing brace

All other `{{variable}}` tags in the template are correctly formed.
The `{{received_date}}` in Table 1 is syntactically correct (double braces); if not passed in data it renders as empty string (jinja2 Undefined, not an error).
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix malformed Jinja2 tag in A250.docx template</name>
  <files>templates/A250.docx</files>
  <action>
    Open `templates/A250.docx` using python-docx. Navigate to `doc.tables[0].rows[4].cells[5]`.

    The cell has one paragraph with three runs:
    - Run 0: `{{`
    - Run 1: `nya_project_code`
    - Run 2: `}` (BUG — only one brace)

    Fix: set `para.runs[2].text = '}}'` to close the tag properly.

    After the fix, verify by calling `DocxTemplate('templates/A250.docx').get_undeclared_template_variables()` — it must return a set without raising an exception. Also confirm `'nya_project_code'` appears in that set.

    Save the document back to `templates/A250.docx`.

    Important: use python-docx (`from docx import Document`) to open and save, NOT docxtpl (which cannot write templates). Preserve all existing formatting — only change the text of that one run.

    Code sketch:
    ```python
    from docx import Document
    doc = Document('templates/A250.docx')
    cell = doc.tables[0].rows[4].cells[5]
    para = cell.paragraphs[0]
    para.runs[2].text = '}}'   # was '}'
    doc.save('templates/A250.docx')
    ```

    Then validate with docxtpl:
    ```python
    from docxtpl import DocxTemplate
    t = DocxTemplate('templates/A250.docx')
    vars_ = t.get_undeclared_template_variables()
    assert 'nya_project_code' in vars_, f"nya_project_code not found in {vars_}"
    print("OK — variables:", sorted(vars_))
    ```
  </action>
  <verify>
    <automated>python -c "
from docxtpl import DocxTemplate
t = DocxTemplate('templates/A250.docx')
vars_ = t.get_undeclared_template_variables()
assert 'nya_project_code' in vars_, f'Missing nya_project_code in {vars_}'
print('PASS — template parses cleanly, nya_project_code present')
"</automated>
  </verify>
  <done>
    `DocxTemplate('templates/A250.docx').get_undeclared_template_variables()` returns successfully (no TemplateSyntaxError) and includes `nya_project_code` in the returned set.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add regression test for A250 template validity and render</name>
  <files>tests/test_a250.py</files>
  <behavior>
    - Test: template parses without TemplateSyntaxError
    - Test: all expected variables present in template (nya_project_code, project_title, requested_by, invoice_to, fee, today, client_signed, principal_name, project_manager)
    - Test: render() with a full data dict completes without exception and produces a docx file on disk
    - Test: rendered file contains nya_project_code value (open with python-docx and scan paragraphs)
  </behavior>
  <action>
    Open `tests/test_a250.py`. The file already has A250-related tests from the 260402-itx quick task. Add the following tests (do not remove existing tests):

    1. `test_template_parses_cleanly` — calls `get_undeclared_template_variables()`, asserts no exception, asserts `nya_project_code` in result.
    2. `test_render_produces_file` — builds a minimal data dict (all keys present, simple string values), calls `doc.render(data)` and `doc.save(tmp_path / "out.docx")`, asserts the output file exists.
    3. `test_render_contains_nya_code` — same render, then opens output with `Document`, scans all table cells, asserts the nya_project_code value appears somewhere in the document.

    Use the `tmp_path` pytest fixture for output files. Use `_resource_path` via direct path construction (`Path('templates/A250.docx')`) for template location in tests (tests run from repo root).

    Run: `pytest tests/test_a250.py -v` — all tests must pass.
  </action>
  <verify>
    <automated>pytest tests/test_a250.py -v</automated>
  </verify>
  <done>
    All tests in tests/test_a250.py pass, including the three new regression tests. No existing tests broken.
  </done>
</task>

</tasks>

<verification>
Full end-to-end check:

```python
from docxtpl import DocxTemplate
from pathlib import Path
import tempfile, os

t = DocxTemplate('templates/A250.docx')
data = {
    'project_title': 'Test Project', 'project_address': '123 Main St',
    'client': 'ACME Corp', 'nya_project_code': 'NYA-2026-001',
    'client_project_code': 'CP-001', 'client_name': 'Jane Doe',
    'client_title': 'PE', 'client_license': 'CA 12345',
    'client_phone': '555-1234', 'client_mobile': '555-5678',
    'client_email': 'jane@acme.com', 'invoice_to': '',
    'client_office_no': '555-9999', 'client_invoice_email': 'billing@acme.com',
    'client_address': '456 Elm St', 'request_date': '2026-04-02',
    'work_type': 'Structural Review', 'project_description': 'Desc',
    'detailed_scope': 'Scope', 'fee_type': 'Lump Sum', 'fee': '5000',
    'principal_name': 'John Smith', 'project_manager': 'Bob Jones',
    'save_location': '', 'a250_creator': 'Tester',
    'today': 'April 2, 2026', 'current_date': 'April 2, 2026',
    'requested_by': 'Jane Doe\nCA 12345\nPE\nACME Corp',
    'client_signed': 'Jane Doe\nPE',
}
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / 'A250_test.docx'
    t.render(data)
    t.save(out)
    print('PASS — generated:', out.stat().st_size, 'bytes')
```

Also run `pytest tests/test_a250.py -v`.
</verification>

<success_criteria>
- `DocxTemplate('templates/A250.docx').get_undeclared_template_variables()` runs without TemplateSyntaxError
- A250 generation from the GUI no longer shows "Unexpected }" error dialog
- All `pytest tests/test_a250.py` tests pass
- templates/A250.docx committed with the fix
</success_criteria>

<output>
After completion, create `.planning/quick/260402-jpl-fix-unexpected-error-when-generating-a25/260402-jpl-SUMMARY.md` with:
- Root cause found
- Fix applied
- Tests added/updated
- Commit hash
</output>
