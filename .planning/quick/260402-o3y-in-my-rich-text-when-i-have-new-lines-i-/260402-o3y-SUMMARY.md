---
phase: quick-260402-o3y
plan: 01
subsystem: editor-ui
tags: [quill, rich-text, font, calibri-light, bug-fix]
dependency_graph:
  requires: []
  provides: [consistent-calibri-light-10pt-on-newlines]
  affects: [assets/editor.html]
tech_stack:
  added: []
  patterns: [quill-font-whitelist-registration, quill-format-default]
key_files:
  created: []
  modified:
    - assets/editor.html
decisions:
  - Register 'calibrilight' and '10pt' in Quill whitelists before creating the instance — Quill ignores unregistered format values silently
  - Call quill.format() after init rather than relying solely on CSS — CSS fallback works for display but Quill internal state still uses defaults that don't match
  - Add .ql-font-calibrilight CSS mapping as dual guard — Quill adds this class to spans, so both the class-based and CSS wildcard rules resolve to Calibri Light
metrics:
  duration: ~3min
  completed_date: "2026-04-02"
  tasks_completed: 1
  files_modified: 1
---

# Phase quick-260402-o3y Plan 01: Fix Quill New-Line Font Inconsistency Summary

**One-liner:** Quill Font/Size whitelist registration + `quill.format()` defaults so new paragraphs always render Calibri Light 10pt, not Calibri 11pt.

---

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Set Quill default format to Calibri Light 10pt in editor.html | ba0f285 | assets/editor.html |

---

## What Was Done

**Root cause:** When the user presses Enter in the Quill editor, Quill creates a new `<p>` element. Without a registered font/size whitelist and an explicit `quill.format()` call, Quill's internal default format does not match the CSS override. Quill would inject no inline style (or a mismatched one) on new paragraphs, causing the browser to fall back to its default font (Calibri 11pt).

**Fix applied in `assets/editor.html`:**

1. Registered `'calibrilight'` as a whitelisted Quill font format value via `Font.whitelist` before calling `Quill.register(Font, true)`.
2. Registered `'10pt'` as a whitelisted Quill size format value via `Size.whitelist` before calling `Quill.register(Size, true)`.
3. Called `quill.format('font', 'calibrilight')` and `quill.format('size', '10pt')` immediately after creating the Quill instance to set the active cursor default.
4. Added `.ql-font-calibrilight` CSS rule mapping the Quill-generated class to `font-family: 'Calibri Light', Calibri, sans-serif`.
5. Added `.ql-editor, .ql-editor *` CSS rule as a universal fallback ensuring all editor children use Calibri Light 10pt.

---

## Deviations from Plan

None - plan executed exactly as written.

---

## Verification

Automated check passed:
```
PASS: editor.html has Quill default format setup
```

Manual smoke test recommended:
1. Launch the application.
2. Open the A250 form and click into a rich-text field.
3. Type a line, press Enter, type another line.
4. Both lines must render in Calibri Light 10pt — identical visual weight and size.
5. Apply Bold to part of line 1; the second line after Enter should revert to normal Calibri Light 10pt.

---

## Self-Check: PASSED

- assets/editor.html: FOUND (verified by read)
- Commit ba0f285: present in git log
