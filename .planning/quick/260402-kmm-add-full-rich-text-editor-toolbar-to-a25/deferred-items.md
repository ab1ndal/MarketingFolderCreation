# Deferred Items — 260402-kmm

## Pre-existing Test Failures (Out of Scope)

These failures exist in commits predating this quick task and were not introduced by 260402-kmm.

### 1. test_requested_by_composite_long
- **File:** tests/test_a250_generation.py
- **Test:** `TestA250Generation::test_requested_by_composite_long`
- **Issue:** Test expects `"\n\n"` (double newline) in `requested_by` for long name+license+title combinations, but app.py logic always uses a single `"\n"` separator (`title_sep = "\n" if ... else ", "`).
- **Introduced by:** e929ea5 (quick-260402-itx)

### 2. test_invoice_to_defaults_to_requested_by  
- **File:** tests/test_a250_generation.py
- **Test:** `TestA250Generation::test_invoice_to_defaults_to_requested_by`
- **Issue:** Test expects `render_data["invoice_to"] == render_data["requested_by"]` when invoice_to is empty, but app.py sets it to `'Same as "Requested By"\n<client>'` — a different fallback string.
- **Introduced by:** e929ea5 (quick-260402-itx)
