"""Pure builder for the A250 docx template context.

Shared by both the live preview panel and the real docx generation so the two
cannot drift. No Qt, no filesystem access.
"""
from __future__ import annotations

from datetime import datetime

from utils.formatting import format_number


def build_a250_context(raw: dict, now: datetime | None = None) -> dict:
    """Return the full template context from raw form values.

    `raw` maps each field key to its string value; rich-text fields hold their
    HTML string and are passed through unchanged (the caller converts them to
    docxtpl.RichText for the document, or renders them as HTML in the preview).
    """
    now = now or datetime.now()
    ctx = dict(raw)

    name    = raw.get("client_name", "").strip()
    licence = raw.get("client_license", "").strip()
    title   = raw.get("client_title", "").strip()
    client  = raw.get("client", "").strip()

    # requested_by: single vs double newline before title based on combined length
    licence_sep = ", " if licence else ""
    title_sep = "\n\n" if len(name) + len(licence) + len(title) > 60 else "\n"
    ctx["requested_by"] = f"{name}{licence_sep}{licence}{title_sep}{title}\n{client}"

    # client_signed: comma vs newline before title based on combined length
    title_sep2 = "\n" if len(name) + len(title) > 40 else ", "
    ctx["client_signed"] = f"{name}{title_sep2}{title}"

    # invoice_to: custom text if provided, else same as requested_by
    invoice_custom = raw.get("invoice_to", "").strip()
    ctx["invoice_to"] = invoice_custom if invoice_custom else ctx["requested_by"]

    ctx["fee"] = format_number(f"{raw.get('fee', '')}")

    ctx["today"] = now.strftime("%B %#d, %Y")
    ctx["today_2"] = now.strftime("%m/%d/%Y")
    ctx["current_date"] = ctx["today"]

    return ctx
