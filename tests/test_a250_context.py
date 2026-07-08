from datetime import datetime
from docxtpl import RichText  # noqa: F401 (import parity check)
from utils.a250_context import build_a250_context

NOW = datetime(2026, 4, 2)


def test_requested_by_short_single_newline():
    ctx = build_a250_context({
        "client_name": "Jane Doe", "client_license": "PE",
        "client_title": "Director", "client": "Acme Corp",
    }, now=NOW)
    rb = ctx["requested_by"]
    assert "Jane Doe" in rb and "PE" in rb and "Director" in rb and "Acme Corp" in rb
    assert "\n\n" not in rb  # short content -> single newline before title


def test_requested_by_long_double_newline():
    ctx = build_a250_context({
        "client_name": "Jonathan Alexander Smithsonian",
        "client_license": "PE, SE, LEED AP BD+C",
        "client_title": "Senior Vice President of Engineering",
        "client": "Big Corporation LLC",
    }, now=NOW)
    assert "\n\n" in ctx["requested_by"]


def test_invoice_to_defaults_to_requested_by():
    ctx = build_a250_context({
        "client_name": "Jane Doe", "client_license": "PE",
        "client_title": "Director", "client": "Acme Corp",
    }, now=NOW)
    assert ctx["invoice_to"] == ctx["requested_by"]


def test_invoice_to_custom_kept():
    ctx = build_a250_context({"invoice_to": "Custom\nSuite 100"}, now=NOW)
    assert ctx["invoice_to"] == "Custom\nSuite 100"


def test_client_signed_short_uses_comma():
    ctx = build_a250_context({"client_name": "Jane", "client_title": "PE"}, now=NOW)
    assert ctx["client_signed"] == "Jane, PE"


def test_client_signed_long_uses_newline():
    ctx = build_a250_context({
        "client_name": "Jonathan Alexander Smithsonian",
        "client_title": "Senior Vice President of Engineering",
    }, now=NOW)
    assert "\n" in ctx["client_signed"]


def test_fee_formatted():
    ctx = build_a250_context({"fee": "5000"}, now=NOW)
    assert ctx["fee"] == "5,000.00"


def test_dates_present():
    ctx = build_a250_context({}, now=NOW)
    assert ctx["today"] == "April 2, 2026"
    assert ctx["today_2"] == "04/02/2026"
    assert ctx["current_date"] == ctx["today"]


def test_passthrough_and_rich_untouched():
    ctx = build_a250_context({"project_title": "Tower A", "detailed_scope": "<b>x</b>"}, now=NOW)
    assert ctx["project_title"] == "Tower A"
    assert ctx["detailed_scope"] == "<b>x</b>"  # rich HTML left as-is
