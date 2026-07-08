"""Pure parsing/matching helpers for Segment mode. No Qt, no I/O side effects."""
import re
from pathlib import Path


def project_number(name: str) -> str | None:
    """Return the leading run of digits in name (the project number), else None."""
    m = re.match(r"\d+", name.strip())
    return m.group(0) if m else None


def derive_year(name: str, current_year: int) -> int | None:
    """Derive a 4-digit year from the first two digits of the project number.

    Pivots on the current 2-digit year: yy <= cur -> 2000+yy, else 1900+yy.
    Returns None if there is no 2+ digit leading number.
    """
    num = project_number(name)
    if not num or len(num) < 2:
        return None
    yy = int(num[:2])
    cur = current_year % 100
    return 2000 + yy if yy <= cur else 1900 + yy


def find_primary_folders(year_root: str, nnnnn: str) -> list[str]:
    """List immediate subfolders of year_root whose leading number token == nnnnn.

    Match rule: folder name starts with nnnnn AND the following character is not
    a digit (so '12345' does not match '123456 - X'). Returns sorted names;
    empty list if nnnnn is empty or year_root is not a directory.
    """
    root = Path(year_root)
    if not nnnnn or not root.is_dir():
        return []
    matches = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(nnnnn):
            rest = name[len(nnnnn):]
            if not (rest and rest[0].isdigit()):
                matches.append(name)
    return sorted(matches)
