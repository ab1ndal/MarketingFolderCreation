# tests/test_formatting.py

import pytest
from utils.formatting import format_number


class TestFormatNumber:

    def test_comma_placement(self):
        assert format_number("1234567.8") == "1,234,567.80"

    def test_comma_with_existing_commas(self):
        assert format_number("1,234,567.8") == "1,234,567.80"

    def test_decimal_rounding(self):
        assert format_number("1234567.891") == "1,234,567.89"

    def test_negative_numbers(self):
        assert format_number("-1234567.8") == "-1,234,567.80"

    def test_integer_handling(self):
        assert format_number("1234567") == "1,234,567.00"
        assert format_number("1234567.0") == "1,234,567.00"
        assert format_number("1234567.00") == "1,234,567.00"

    def test_string_handling(self):
        assert format_number("abc") == ""

    def test_empty_string(self):
        assert format_number("") == ""

    def test_none_input(self):
        assert format_number(None) is None

    def test_incorrect_comma_placement(self):
        assert format_number("1234567.891,") == "1,234,567.89"
        assert format_number("12,3,4,5,67.89") == "1,234,567.89"