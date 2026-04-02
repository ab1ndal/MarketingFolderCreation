---
phase: quick-260402-lxo
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - utils/richtext_utils.py
  - app.py
  - assets/editor.html
  - tests/test_a250_generation.py
  - tests/test_richtext_utils.py
autonomous: true
requirements: [LXO-01, LXO-02]

must_haves:
  truths:
    - "utils/richtext_utils.py contains only html_to_richtext (and its helpers) — no RichTextEditor class"
    - "app.py does not import RichTextEditor and has no isinstance(w, RichTextEditor) branch"
    - "Quill editor in editor.html defaults to Calibri Light 10pt for all typed text"
    - "pytest passes with no failures"
  artifacts:
    - path: utils/richtext_utils.py
      provides: html_to_richtext function only
      contains: "def html_to_richtext"
    - path: assets/editor.html
      provides: Quill editor with Calibri Light 10pt default
      contains: "Calibri Light"
  key_links:
    - from: app.py
      to: utils/richtext_utils
      via: "from utils.richtext_utils import html_to_richtext"
      pattern: "html_to_richtext"
    - from: assets/editor.html
      to: Quill root
      via: CSS font-family on #editor and Quill defaultFormats
      pattern: "Calibri Light"
---

<objective>
Remove the dead RichTextEditor class from utils/richtext_utils.py (replaced by WebRichTextEditor
in quick task 260402-l91), clean up the stale import and dead branch in app.py, and set
Calibri Light 10pt as the default font in assets/editor.html.

Purpose: Eliminate dead code that adds confusion and unused PyQt6 imports; match Word's default
heading font so A250 documents render in the expected font without manual selection.
Output: Trimmed richtext_utils.py, updated app.py, updated editor.html, passing tests.
</objective>

<execution_context>
@C:/Users/abindal/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/abindal/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Delete RichTextEditor from richtext_utils.py and clean app.py</name>
  <files>utils/richtext_utils.py, app.py</files>
  <action>
In utils/richtext_utils.py:

1. Delete the entire RichTextEditor class (line 189 to end of file, including the section comment
   "# RichTextEditor widget" at line 186).

2. Remove PyQt6 imports that are only used by RichTextEditor. The two import lines to modify:

   FROM:
     from PyQt6.QtWidgets import (
         QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QTextEdit, QPushButton,
     )
     from PyQt6.QtGui import QTextCharFormat, QTextCursor

   TO: DELETE both lines entirely (nothing in html_to_richtext needs PyQt6).

3. Update the module docstring (lines 1-7) to remove the "RichTextEditor" export line. Result:
     """Rich-text utilities for the A250 form.

     Exports:
         html_to_richtext - Convert QTextEdit/Quill HTML output to a docxtpl RichText object
     """

In app.py:

1. Line 24: change
     from utils.richtext_utils import RichTextEditor, html_to_richtext
   to:
     from utils.richtext_utils import html_to_richtext

2. In _generate_a250, inside the _get_val inner function, remove the dead branch:
     elif isinstance(w, RichTextEditor):
         return html_to_richtext(w.toHtml())
   Leave all other branches (QComboBox, WebRichTextEditor, QTextEdit, else) unchanged.
  </action>
  <verify>
    <automated>cd /c/Users/abindal/Documents/00_Python/MarketingFolderCreation && python -c "from utils.richtext_utils import html_to_richtext; print('import ok')" && python -c "src=open('utils/richtext_utils.py').read(); assert 'RichTextEditor' not in src; assert 'QWidget' not in src; print('richtext_utils clean')" && python -c "src=open('app.py').read(); assert 'RichTextEditor' not in src; print('app.py clean')"</automated>
  </verify>
  <done>richtext_utils.py exports only html_to_richtext; no PyQt6 imports remain in it; app.py has no RichTextEditor reference.</done>
</task>

<task type="auto">
  <name>Task 2: Set Calibri Light 10pt default in editor.html and update tests</name>
  <files>assets/editor.html, tests/test_a250_generation.py, tests/test_richtext_utils.py</files>
  <action>
In assets/editor.html:

1. Update the CSS for #editor to include the Calibri Light font at 10pt. Change:
     #editor { height: calc(100% - 42px); font-size: 13px; }
   to:
     #editor { height: calc(100% - 42px); font-size: 10pt; font-family: 'Calibri Light', Calibri, sans-serif; }

2. Set Quill's defaultFormats so that text typed without explicit formatting inherits this font.
   Add a `formats` option to the Quill constructor:

   FROM:
     var quill = new Quill('#editor', {
       theme: 'snow',
       modules: { toolbar: '#toolbar' }
     });

   TO:
     var quill = new Quill('#editor', {
       theme: 'snow',
       modules: { toolbar: '#toolbar' }
     });
     quill.format('font', false);   // reset any Quill-injected default
     // CSS on #editor already applies Calibri Light 10pt to quill.root

   Note: Quill inherits font from the container element via CSS, so the CSS change alone is
   sufficient for default display. No additional JS is required beyond what's already there.
   Simply remove the extra quill.format line if it causes issues — the CSS rule is the primary fix.

In tests/test_a250_generation.py:

The two _make_a250_vars helpers (in TestA250Generation and TestA250RichTextFields) currently mock
rich text fields as Mock(spec=RichTextEditor). Since the fields now hold WebRichTextEditor
widgets, update the mocks to use WebRichTextEditor spec and call get_html_sync instead of toHtml:

1. Remove the import on line 8:
     from utils.richtext_utils import RichTextEditor

2. Add import at top of file (alongside existing imports):
     from utils.web_editor import WebRichTextEditor

3. In both _make_a250_vars helpers, change the rich text mock block from:
     for f in RICH_TEXT_FIELDS:
         m = Mock(spec=RichTextEditor)
         m.toHtml = Mock(return_value="<p></p>")
         m.toPlainText = Mock(return_value="")
         vars_[f] = m
   to:
     for f in RICH_TEXT_FIELDS:
         m = Mock(spec=WebRichTextEditor)
         m.get_html_sync = Mock(return_value="<p></p>")
         m.toPlainText = Mock(return_value="")
         vars_[f] = m

4. In the override logic inside both _make_a250_vars helpers, change:
     if k in RICH_TEXT_FIELDS:
         widget.toHtml = Mock(return_value=v)
   to:
     if k in RICH_TEXT_FIELDS:
         widget.get_html_sync = Mock(return_value=v)

In tests/test_richtext_utils.py:

Remove the TestRichTextEditor class entirely (lines 168-210, from the section comment
"# RichTextEditor widget tests" through the last test method test_exports). The
html_to_richtext tests above it and the TestHtmlToRichtextBodyStripping class below it
must be preserved unchanged.
  </action>
  <verify>
    <automated>cd /c/Users/abindal/Documents/00_Python/MarketingFolderCreation && python -c "src=open('assets/editor.html').read(); assert 'Calibri Light' in src; assert '10pt' in src; print('editor.html ok')" && python -m pytest tests/test_a250_generation.py tests/test_richtext_utils.py -x -q 2>&1 | tail -10</automated>
  </verify>
  <done>editor.html shows Calibri Light 10pt in #editor CSS; no RichTextEditor references remain in any test file; all tests pass.</done>
</task>

</tasks>

<verification>
Run full test suite:
  cd /c/Users/abindal/Documents/00_Python/MarketingFolderCreation && python -m pytest -x -q 2>&1 | tail -15

Confirm zero references to RichTextEditor remain:
  grep -r "RichTextEditor" --include="*.py" .
(Expected: no output)
</verification>

<success_criteria>
- RichTextEditor class deleted from richtext_utils.py; file is PyQt6-free
- app.py: no RichTextEditor import, no isinstance(w, RichTextEditor) branch
- editor.html: #editor CSS includes font-family: 'Calibri Light', Calibri, sans-serif; font-size: 10pt
- All pytest tests pass (no failures, no errors)
- No remaining references to RichTextEditor anywhere in the codebase
</success_criteria>

<output>
After completion, create .planning/quick/260402-lxo-clean-unused-richtexteditor-code-and-set/260402-lxo-SUMMARY.md
</output>
