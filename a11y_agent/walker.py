"""Recursively discover candidate source files under a target directory."""

import os
from typing import Iterator, Iterable

SCANNED_EXTENSIONS = (".html", ".htm", ".jsx", ".tsx")

EXCLUDED_DIR_NAMES = {
    "node_modules",
    "dist",
    "build",
    ".git",
    ".next",
    ".venv",
    "venv",
    "__pycache__",
    ".cache",
    "coverage",
}


def find_source_files(root: str) -> Iterator[str]:
    """Yield paths to .html/.htm/.jsx/.tsx files under root.

    Skips common build/dependency/vcs directories so a scan of a real project
    doesn't waste time (and produce noise) walking vendored code.
    """
    if os.path.isfile(root):
        if root.endswith(SCANNED_EXTENSIONS):
            yield root
        return

    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded directories in-place so os.walk doesn't descend into them
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIR_NAMES)
        for filename in sorted(filenames):
            if filename.endswith(SCANNED_EXTENSIONS):
                yield os.path.join(dirpath, filename)


def find_source_files_list(root: str) -> Iterable[str]:
    return list(find_source_files(root))
