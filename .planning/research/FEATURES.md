# Features Research: PyQt6 Desktop Tool Modernization

**Research Date:** 2026-03-31
**Domain:** PyQt6 desktop app UX for non-technical users

---

## Table Stakes (Must-Have)

Features users expect. Missing these causes abandonment or complaints.

| Feature | Description | Complexity |
|---------|-------------|------------|
| Non-blocking UI | Window never freezes during file operations (QThread) | Medium |
| Progress feedback | Visible indication work is happening (progress bar or spinner) | Low |
| Cancellation support | User can stop a running operation mid-workflow | Medium |
| Jargon-free errors | Error messages in plain English, no stack traces | Low |
| Windows-native file dialogs | Use QFileDialog — matches OS conventions users know | Low |
| Readable fonts + contrast | Legible text, sufficient contrast for varied monitors | Low |

## Differentiators

Features that improve experience without being required.

| Feature | Description | Complexity |
|---------|-------------|------------|
| Searchable operation log | Filter/search log entries for auditing | Medium |
| Path memory | Remember last-used paths across sessions (QSettings) | Low |
| Toast / status notifications | Non-intrusive success/error feedback in corner | Medium |
| Settings dialog | Let power users adjust defaults without editing config files | Medium |
| Keyboard shortcuts | Enter to run, Escape to cancel | Low |

## Anti-Features (Deliberately Excluded)

| Feature | Reason |
|---------|--------|
| Terminal/console window | Frightens non-technical users |
| Custom file dialogs | Use native Windows dialogs — users already know them |
| Undo/rollback | High complexity, low value for this workflow |
| Real-time folder monitoring | Out of scope |
| Animations/transitions | Distracting, can reduce trust with non-technical audience |
| Multi-language support | Not needed for current audience |

## MVP Priority

**Tier 1 — Phase: PyQt6 Migration**
- Non-blocking QThread operations
- Progress bar
- Cancellation
- Plain-English error messages
- Modern PyQt6 UI layout

**Tier 2 — Phase: UX Polish**
- Dark/light mode toggle (QApplication palette)
- Tooltips on all inputs
- Clipboard copy after success
- Keyboard shortcuts (Enter to run)

**Tier 3 — Future**
- Searchable log
- Path memory via QSettings
- Settings dialog

## Feature Dependencies

```
Non-blocking UI (QThread)
  └── Cancellation support (requires worker signal)
  └── Real-time progress updates (requires progress signal)
      └── Toast notifications (optional enhancement)
```

---
*Research: 2026-03-31*
