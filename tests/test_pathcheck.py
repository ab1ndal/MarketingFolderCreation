from utils.pathcheck import deepest_relative_len, projected_path_len, exceeds_limit


class TestDeepestRelativeLen:
    def test_empty_folder_returns_zero(self, tmp_path):
        assert deepest_relative_len(str(tmp_path)) == 0

    def test_missing_root_returns_zero(self, tmp_path):
        assert deepest_relative_len(str(tmp_path / "nope")) == 0

    def test_finds_longest_relative_path(self, tmp_path):
        # deepest: sub/inner/file.txt  -> "sub\inner\file.txt"
        deep = tmp_path / "sub" / "inner"
        deep.mkdir(parents=True)
        (deep / "file.txt").write_text("x")
        (tmp_path / "short.txt").write_text("y")
        import os
        expected = len(os.path.join("sub", "inner", "file.txt"))
        assert deepest_relative_len(str(tmp_path)) == expected


class TestProjectedPathLen:
    def test_base_plus_deepest_with_separator(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "f.txt").write_text("x")  # deepest rel = "a\f.txt"
        import os
        deepest = len(os.path.join("a", "f.txt"))
        base = r"V:\2025\12345 - Main\12345.01 - Seg"
        assert projected_path_len(base, str(tmp_path)) == len(base) + 1 + deepest

    def test_empty_template_is_base_len_only(self, tmp_path):
        base = r"V:\2025\Proj"
        assert projected_path_len(base, str(tmp_path)) == len(base)


class TestExceedsLimit:
    def test_under_limit_false(self, tmp_path):
        (tmp_path / "f.txt").write_text("x")
        assert exceeds_limit(r"V:\2025\Proj", str(tmp_path), margin=0, limit=260) is False

    def test_over_limit_true(self, tmp_path):
        (tmp_path / "f.txt").write_text("x")  # deepest rel = 5 ("f.txt")
        base = "V:\\" + ("X" * 260)  # 3 + 260 + 1 + 5 = 269 > 260
        assert exceeds_limit(base, str(tmp_path), margin=0, limit=260) is True

    def test_margin_pushes_over(self, tmp_path):
        (tmp_path / "f.txt").write_text("x")
        base = "V:\\" + ("X" * 200)  # projected ~ 3+200+1+5 = 209
        assert exceeds_limit(base, str(tmp_path), margin=0, limit=260) is False
        assert exceeds_limit(base, str(tmp_path), margin=60, limit=260) is True
