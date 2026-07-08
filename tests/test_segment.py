import pytest
from utils.segment import project_number, derive_year, find_primary_folders


class TestProjectNumber:
    @pytest.mark.parametrize("name,expected", [
        ("12345.01 - Foundation", "12345"),
        ("25045 - Project Name", "25045"),
        ("  02031.BD  ", "02031"),
        ("89045", "89045"),
        ("No digits here", None),
        ("", None),
        (".01 leading dot", None),
    ])
    def test_extracts_leading_digit_run(self, name, expected):
        assert project_number(name) == expected


class TestDeriveYear:
    # current_year fixed at 2026 -> cur = 26
    @pytest.mark.parametrize("name,expected", [
        ("25045.01", 2025),
        ("02031", 2002),
        ("89045", 1989),
        ("99123", 1999),
        ("26123", 2026),
        ("27123", 1927),
        ("00999", 2000),
    ])
    def test_pivot_at_current_year(self, name, expected):
        assert derive_year(name, 2026) == expected

    def test_no_digits_returns_none(self):
        assert derive_year("Project", 2026) is None

    def test_single_digit_returns_none(self):
        assert derive_year("5 - foo", 2026) is None


class TestFindPrimaryFolders:
    def _mk(self, root, *names):
        for n in names:
            (root / n).mkdir()

    def test_exact_leading_token_match(self, tmp_path):
        self._mk(tmp_path, "12345 - Main Project", "99999 - Other")
        assert find_primary_folders(str(tmp_path), "12345") == ["12345 - Main Project"]

    def test_rejects_longer_number(self, tmp_path):
        self._mk(tmp_path, "12345 - Main", "123456 - Different")
        assert find_primary_folders(str(tmp_path), "12345") == ["12345 - Main"]

    def test_bare_number_folder_matches(self, tmp_path):
        self._mk(tmp_path, "12345")
        assert find_primary_folders(str(tmp_path), "12345") == ["12345"]

    def test_multiple_matches_sorted(self, tmp_path):
        self._mk(tmp_path, "12345 - Bravo", "12345.OLD - Alpha")
        assert find_primary_folders(str(tmp_path), "12345") == [
            "12345 - Bravo", "12345.OLD - Alpha",
        ]

    def test_ignores_files(self, tmp_path):
        (tmp_path / "12345 - file.txt").write_text("x")
        assert find_primary_folders(str(tmp_path), "12345") == []

    def test_missing_root_returns_empty(self, tmp_path):
        assert find_primary_folders(str(tmp_path / "nope"), "12345") == []

    def test_empty_nnnnn_returns_empty(self, tmp_path):
        (tmp_path / "12345 - Main").mkdir()
        assert find_primary_folders(str(tmp_path), "") == []
