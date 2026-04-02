---
phase: quick-260402-kmm
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - utils/richtext_utils.py
  - app.py
  - tests/test_richtext_utils.py
  - tests/test_a250_generation.py
autonomous: true
requirements: [QUICK-260402-kmm]

must_haves:
  truths:
    - "project_description and detailed_scope fields show a toolbar with Bold, Italic, Underline, Strikethrough, Bullet List, and Clear Formatting buttons"
    - "Clicking a toolbar button applies the corresponding format to selected text in the field"
    - "Generated A250 .docx preserves bold/italic/underline/strikethrough applied via the toolbar in the rendered output"
    - "Bullet items in the rich text fields appear as bulleted paragraphs in the .docx output"
    - "All other A250 fields (addresses, invoice_to, etc.) continue to behave exactly as before"
  artifacts:
    - path: "utils/richtext_utils.py"
      provides: "RichTextEditor widget class and html_to_richtext() converter"
      exports: ["RichTextEditor", "html_to_richtext"]
    - path: "app.py"
      provides: "A250 form using RichTextEditor for project_description and detailed_scope"
      contains: "RichTextEditor"
    - path: "tests/test_richtext_utils.py"
      provides: "Unit tests for html_to_richtext converter"
    - path: "tests/test_a250_generation.py"
      provides: "Updated mocks compatible with RichTextEditor interface"
  key_links:
    - from: "app.py _generate_a250"
      to: "utils/richtext_utils.html_to_richtext"
      via: "called for project_description and detailed_scope when widget is RichTextEditor"
    - from: "html_to_richtext"
      to: "docxtpl.RichText"
      via: "RichText.add() calls with bold/italic/underline/strike flags"
---

<objective>
Add a rich-text formatting toolbar to the project_description and detailed_scope fields in the A250 form. Users can select text and click toolbar buttons (Bold, Italic, Underline, Strikethrough, Bullet List, Clear Formatting) to apply formatting. The applied formatting survives into the generated .docx via docxtpl's RichText mechanism.

Purpose: A250 scope and description fields often contain structured content (bulleted scope items, bold key terms). Currently all formatting is lost on generate. This makes the .docx output match the user's intent without requiring knowledge of Word keyboard shortcuts.

Output: utils/richtext_utils.py (new), app.py (modified), tests/test_richtext_utils.py (new), tests/test_a250_generation.py (updated)
</objective>

<execution_context>
@C:/Users/abindal/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/abindal/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@app.py
@tests/test_a250_generation.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create RichTextEditor widget and html_to_richtext converter</name>
  <files>utils/richtext_utils.py, tests/test_richtext_utils.py</files>
  <behavior>
    html_to_richtext tests:
    - Plain text "Hello" → RichText with one segment, no formatting flags
    - "&lt;b&gt;Hello&lt;/b&gt;" → RichText segment with bold=True
    - "&lt;i&gt;Hello&lt;/i&gt;" → RichText segment with italic=True
    - "&lt;u&gt;Hello&lt;/u&gt;" → RichText segment with underline=True
    - "&lt;s&gt;Hello&lt;/s&gt;" or &lt;del&gt; → RichText segment with strike=True
    - "&lt;b&gt;&lt;i&gt;Hello&lt;/i&gt;&lt;/b&gt;" → RichText segment with bold=True and italic=True
    - "&lt;li&gt;Item&lt;/li&gt;" → RichText segment with text "• Item\n", no extra formatting
    - Multi-paragraph HTML (two &lt;p&gt; tags) → segments separated by newline
    - Empty string "" → RichText with no segments (empty)
    - HTML with &amp;nbsp; and other HTML entities → decoded to plain characters
  </behavior>
  <action>
    Create utils/richtext_utils.py with two exports:

    **html_to_richtext(html: str) -> docxtpl.RichText**

    Use Python's html.parser (stdlib, no extra deps) to parse QTextEdit's HTML output into a docxtpl RichText object. Walk the tag tree tracking a formatting state stack (bold, italic, underline, strike). On each text node, call rt.add(text, bold=..., italic=..., underline=..., strike=...). Handle:
    - Tags that imply formatting: &lt;b&gt;/&lt;strong&gt; → bold, &lt;i&gt;/&lt;em&gt; → italic, &lt;u&gt; → underline, &lt;s&gt;/&lt;del&gt;/&lt;strike&gt; → strike
    - &lt;li&gt; items: prepend "• " to the text content and append "\n"
    - &lt;p&gt; and &lt;br&gt;: add "\n" break segment between paragraphs (avoid double-newline for consecutive block elements)
    - HTML entities: use html.unescape() on all text nodes
    - QTextEdit wraps content in &lt;html&gt;&lt;body&gt;&lt;p style="..."&gt; — ignore all style= attributes, process structure only
    - Return an empty RichText() for empty or whitespace-only input

    The parser should be implemented as an HTMLParser subclass that accumulates (text, bold, italic, underline, strike) tuples, then constructs the RichText at the end by calling rt.add() for each non-empty segment.

    **RichTextEditor(QWidget)**

    A QWidget subclass that stacks a compact QToolBar above a QTextEdit. Constructor signature: RichTextEditor(parent=None, height=80).

    Toolbar buttons (use standard Unicode characters as labels — no icons required):
    - "B" → toggles bold (QTextCharFormat)
    - "I" → toggles italic
    - "U" → toggles underline
    - "S" → toggles strikethrough
    - "• List" → inserts a bullet character "• " at the start of the current block (does not use QTextList — just prefixes "• " to the line, keeping docx conversion simple)
    - "✕ Clear" → calls setCharFormat(QTextCharFormat()) to remove all character-level formatting from the selection

    Each B/I/U/S button should be checkable (QPushButton with setCheckable(True)) so it reflects the current cursor state. Connect currentCharFormatChanged signal from the QTextEdit to update button checked states.

    Public interface (mirrors QTextEdit for drop-in use in a250_vars dict):
    - toHtml() → self._editor.toHtml()
    - toPlainText() → self._editor.toPlainText()
    - setFixedHeight(h) → set overall widget height; internally allocate ~24px to toolbar and remainder to editor
    - setPlaceholderText(text) → self._editor.setPlaceholderText(text)

    Do NOT add toPlainText to the RichTextEditor as the primary extraction path — _generate_a250 will be updated in Task 2 to call toHtml() for these fields.

    Add utils/__init__.py only if it does not already exist.

    For tests/test_richtext_utils.py: pure unit tests, no QApplication needed for html_to_richtext tests. For RichTextEditor widget tests, use the module-scoped qapp fixture from conftest.py (or define one inline if needed).
  </action>
  <verify>
    <automated>cd /c/Users/abindal/Documents/00_Python/MarketingFolderCreation && python -m pytest tests/test_richtext_utils.py -v 2>&1 | tail -20</automated>
  </verify>
  <done>All html_to_richtext behavior tests pass. RichTextEditor can be instantiated without error. utils/richtext_utils.py exports RichTextEditor and html_to_richtext.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire RichTextEditor into A250 form and update generate logic + tests</name>
  <files>app.py, tests/test_a250_generation.py</files>
  <behavior>
    _generate_a250 behavior tests:
    - When project_description widget has toHtml() returning "&lt;b&gt;Scope&lt;/b&gt;", the rendered data["project_description"] must be a docxtpl.RichText instance (not a plain string)
    - When detailed_scope widget has toHtml() returning plain text "Scope", rendered data["detailed_scope"] is a RichText instance
    - All other fields (project_title, client_name, etc.) continue to render as plain strings — no regression
    - invoice_to custom text still works: when invoice_to widget.toPlainText() returns non-empty text, data["invoice_to"] is that plain string (invoice_to is NOT a RichTextEditor field)
    - invoice_to empty still falls back to the requested_by composite
  </behavior>
  <action>
    **app.py changes:**

    1. Add import at top: `from utils.richtext_utils import RichTextEditor, html_to_richtext`

    2. In _open_a250_form, update MULTILINE_FIELDS and widget creation:
       - Change MULTILINE_FIELDS set to only: `{"project_address", "client_address", "invoice_to"}` (remove project_description and detailed_scope — these get RichTextEditor instead)
       - Add a new set: `RICH_TEXT_FIELDS = {"project_description", "detailed_scope"}`
       - In the form loop, add a third branch: `elif key in RICH_TEXT_FIELDS:` → create `RichTextEditor(height=120)` and assign to a250_vars[key]

    3. In _generate_a250, update _get_val():
       Replace the current implementation:
       ```python
       def _get_val(w):
           if isinstance(w, QComboBox):
               return w.currentText()
           elif isinstance(w, QTextEdit):
               return w.toPlainText()
           else:
               return w.text()
       ```
       With:
       ```python
       def _get_val(w):
           if isinstance(w, QComboBox):
               return w.currentText()
           elif isinstance(w, RichTextEditor):
               return html_to_richtext(w.toHtml())
           elif isinstance(w, QTextEdit):
               return w.toPlainText()
           else:
               return w.text()
       ```
       The isinstance(w, RichTextEditor) check MUST come before isinstance(w, QTextEdit) because RichTextEditor is a QWidget subclass, not a QTextEdit subclass, so order does not actually matter — but placing it first makes the intent explicit.

    Note on invoice_to composite logic: invoice_to stays as a plain QTextEdit. The existing composite logic in _generate_a250 calls `data.get("invoice_to", "").strip()` — this continues to work because _get_val for QTextEdit returns toPlainText() (a string). No change needed there.

    **tests/test_a250_generation.py changes:**

    Update _make_a250_vars:
    - Move "project_description" and "detailed_scope" out of MULTILINE_FIELDS and into a new RICH_TEXT_FIELDS list
    - For RICH_TEXT_FIELDS, create mocks that have both toHtml() and toPlainText() methods:
      ```python
      RICH_TEXT_FIELDS = ["project_description", "detailed_scope"]
      # In _make_a250_vars:
      for f in RICH_TEXT_FIELDS:
          m = Mock()
          m.toHtml = Mock(return_value="<p></p>")
          m.toPlainText = Mock(return_value="")
          vars_[f] = m
      ```
    - In test_render_called_with_all_fields, the assertion `"project_title" in render_call` etc. still passes. No behavior change needed for existing assertions — they only check key presence, not value type.
    - The existing invoice_to tests (test_invoice_to_defaults_to_requested_by, test_invoice_to_custom_text) must still pass unchanged. These tests mock invoice_to as a QTextEdit with toPlainText — that path is unchanged.
    - Do NOT break TestA250TemplateRegression tests — those use FULL_RENDER_DATA with plain strings, which continue to work (docxtpl accepts both str and RichText for the same placeholder).
  </action>
  <verify>
    <automated>cd /c/Users/abindal/Documents/00_Python/MarketingFolderCreation && python -m pytest tests/test_a250_generation.py tests/test_richtext_utils.py -v 2>&1 | tail -30</automated>
  </verify>
  <done>All test_a250_generation tests pass. project_description and detailed_scope fields in the A250 dialog show a compact formatting toolbar. _generate_a250 passes RichText objects for those fields to docxtpl. No existing tests regressed.</done>
</task>

</tasks>

<verification>
Full test suite (excluding integration tests that require network paths):

```
cd /c/Users/abindal/Documents/00_Python/MarketingFolderCreation && python -m pytest tests/test_richtext_utils.py tests/test_a250_generation.py -v
```

Manual smoke test: launch app.py, click "Create A250", verify project_description and detailed_scope fields each have a toolbar row above the text area with B/I/U/S/• List/✕ Clear buttons.
</verification>

<success_criteria>
- utils/richtext_utils.py exists with RichTextEditor and html_to_richtext exports
- A250 form: project_description and detailed_scope each show a formatting toolbar; all other fields unchanged
- Bold/Italic/Underline/Strikethrough applied via toolbar are preserved in the generated .docx as formatted runs
- Bullet-listed lines appear as "• item" paragraphs in the .docx
- All tests in test_a250_generation.py and test_richtext_utils.py pass
- No regression in TestA250TemplateRegression (template render still works with plain strings)
</success_criteria>

<output>
After completion, create .planning/quick/260402-kmm-add-full-rich-text-editor-toolbar-to-a25/260402-kmm-SUMMARY.md

Summary should include:
- What was built (RichTextEditor widget, html_to_richtext converter, A250 integration)
- Key implementation decisions (HTMLParser approach, RichText vs plain str dispatch in _get_val, toolbar button design)
- Files changed
- Test coverage added
</output>
