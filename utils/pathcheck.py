"""Windows path-length projection helpers.

Segment mode nests folders one level deeper (year/primary/segment), pushing the
copied template subfolders closer to the classic Windows MAX_PATH (260) limit.
These pure functions project the longest path that will exist after a copy so the
UI can warn before creating folders that may be unusable by Explorer/Office/COM.
"""
from pathlib import Path

WINDOWS_MAX_PATH = 260


def deepest_relative_len(root: str) -> int:
    """Return the length of the longest descendant path relative to root.

    0 if root is missing or empty. This is the deepest subpath that will be
    appended under a copy destination.
    """
    base = Path(root)
    if not base.is_dir():
        return 0
    longest = 0
    for child in base.rglob("*"):
        rel = len(str(child.relative_to(base)))
        if rel > longest:
            longest = rel
    return longest


def projected_path_len(target_base: str, template_root: str) -> int:
    """Project the longest absolute path after copying template_root into target_base.

    = len(target_base) + separator + deepest relative subpath of the template.
    When the template is empty, it is just len(target_base).
    """
    deepest = deepest_relative_len(template_root)
    base_len = len(str(target_base))
    return base_len + (1 + deepest if deepest else 0)


def exceeds_limit(target_base: str, template_root: str, margin: int = 0,
                  limit: int = WINDOWS_MAX_PATH) -> bool:
    """True if the projected longest path exceeds (limit - margin).

    margin reserves headroom for files the user adds inside the folders later.
    """
    return projected_path_len(target_base, template_root) > (limit - margin)
