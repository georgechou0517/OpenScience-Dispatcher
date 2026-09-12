#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Re-apply local fixes on top of the vendored skill tree after a rebuild.

`skills/` is a byte-for-byte copy of the upstream OpenScience tree, produced by
`tools/rebuild.py` via `shutil.copytree(..., dirs_exist_ok=True)`. Anything fixed
directly under `skills/` is therefore silently reverted the next time the tree is
rebuilt from upstream source.

`tools/patches/` mirrors the tree layout and holds the corrected files. This
script copies each one back over `skills/`. `rebuild.py` calls it automatically
as its last step, and it can also be run on its own:

    python tools/apply_patches.py

Exit status is 0 when every patch was applied, 1 if a patch target could not be
written (so a broken patch never passes unnoticed in a build).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PATCHES = HERE / "patches"
SKIP_NAMES = {"README.md", ".gitkeep"}


def apply(verbose: bool = True) -> tuple[list[Path], list[Path]]:
    """Copy every file under tools/patches/ over the same relative path in the tree.

    Returns (applied, skipped).
    """
    if not PATCHES.is_dir():
        if verbose:
            print("apply_patches: no tools/patches/ directory, nothing to do.")
        return [], []

    applied: list[Path] = []
    skipped: list[Path] = []
    for src in sorted(PATCHES.rglob("*")):
        if not src.is_file() or src.name in SKIP_NAMES:
            continue
        rel = src.relative_to(PATCHES)
        dst = ROOT / rel
        if not dst.parent.is_dir():
            # The upstream tree no longer has this skill: report it rather than
            # creating a stray directory that the next rebuild would delete.
            print(f"  SKIP  {rel.as_posix()}  (target directory missing)")
            skipped.append(rel)
            continue
        shutil.copyfile(src, dst)
        applied.append(rel)
        if verbose:
            print(f"  OK    {rel.as_posix()}")

    if verbose:
        total = len(applied) + len(skipped)
        print(f"apply_patches: {len(applied)}/{total} patch(es) applied.")
    return applied, skipped


def main() -> int:
    applied, skipped = apply()
    return 1 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
