You are working on a PyQt6 desktop application that currently uses a custom `RichTextEditor` built on top of `QTextEdit`. This editor is used in two fields:

* project_description
* detailed_scope

The current implementation has issues with inconsistent HTML output, CSS pollution, and unreliable formatting for lists and rich text when converting to docxtpl.RichText.

Your task is to **replace the existing RichTextEditor implementation with a modern embedded web-based editor using Quill, while keeping the application fully offline and compatible with the existing A250 generation pipeline.**

---

## High-Level Requirements

1. The app must remain a **fully offline desktop application**
2. Replace QTextEdit-based rich text editor with **QWebEngineView + Quill**
3. Preserve compatibility with existing:
   * html_to_richtext()
   * docxtpl pipeline
4. Ensure clean, minimal HTML output (no , no CSS noise)
5. Maintain current UI structure and form behavior

---

## Step 1: Remove Old Editor Usage

* Remove or deprecate `RichTextEditor` usage in:
  * app.py
  * richtext_utils.py (do not delete html_to_richtext yet)
* Replace usage of:
  widget.toHtml()

with:
a method that retrieves HTML from the embedded web editor

---

## Step 2: Create New Web-Based Editor Component

Create a new Python file:

utils/web_editor.py

Implement a class:

class WebRichTextEditor(QWidget):

This class should:

* Internally use QWebEngineView
* Load a local HTML file (editor.html)
* Expose:
  get_html(callback)
  set_html(html)

Example interface:

def get_html(self, callback):
self.view.page().runJavaScript("getContent();", callback)

def set_html(self, html):
escaped = html.replace("`", "\\`")
self.view.page().runJavaScript(f"setContent(`{escaped}`);")

---

## Step 3: Create Local HTML Editor

Create a new file:

assets/editor.html

This file must:

* Load Quill locally (NO CDN)
* Include toolbar with:
  bold, italic, underline, strike
  bullet list, numbered list
  clear formatting

Example structure:

* Include quill.js and quill.snow.css from local assets
* Initialize Quill with toolbar
* Define:

function getContent() {
return quill.root.innerHTML;
}

function setContent(html) {
quill.root.innerHTML = html;
}

Ensure:

* No external network requests
* No inline pollution beyond minimal

---

## Step 4: Add Quill Assets

Create:

assets/quill.js
assets/quill.snow.css

Download from official Quill distribution and store locally.

---

## Step 5: Update app.py

In A250 form creation:

Replace:

widget = RichTextEditor(...)

with:

widget = WebRichTextEditor(...)

---

Update value extraction logic:

Current:

elif isinstance(w, RichTextEditor):
return html_to_richtext(w.toHtml())

Replace with asynchronous-safe pattern:

* Collect all normal fields first
* For WebRichTextEditor fields:
  call get_html(callback)
  store results
* After all HTML is collected, convert using html_to_richtext

You may implement a small synchronization helper to wait for both editors.

---

## Step 6: Clean HTML Before Parsing

Update html_to_richtext:

* Strip , , using regex before parsing
* Ensure only body content is parsed

---

## Step 7: Update PyInstaller Spec

Modify:

C:\Users\abindal\Documents\00_Python\MarketingFolderCreation\ClickFolder_v2.spec

Add the following files to datas:

* assets/editor.html
* assets/quill.js
* assets/quill.snow.css

Example:

datas=[
('assets/editor.html', 'assets'),
('assets/quill.js', 'assets'),
('assets/quill.snow.css', 'assets'),
]

Ensure:

* _resource_path() is used to resolve paths correctly in bundled mode

---

## Step 8: Path Handling

Ensure WebRichTextEditor loads editor.html using:

_resource_path("assets/editor.html")

---

## Step 9: Maintain Backward Compatibility

* Keep html_to_richtext unchanged except for cleanup improvements
* Ensure output still works with docxtpl.RichText

---

## Step 10: Final Validation

Verify:

1. App launches without internet
2. Editor loads correctly
3. Formatting works:
   * bold, italic, underline
   * bullet and numbered lists
4. Copy paste from Word behaves reasonably
5. Generated A250 document preserves formatting
6. No CSS or content appears in output

---

## Deliverables

Claude should:

1. Create:
   * utils/web_editor.py
   * assets/editor.html
   * include quill assets
2. Modify:
   * app.py
   * ClickFolder_v2.spec
3. Ensure:
   * clean integration
   * no breaking changes to existing workflow

---

Focus on clean, maintainable implementation. Avoid overengineering. Keep the integration minimal but robust.
