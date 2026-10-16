#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Re-apply local fixes on top of the vendored skill tree after a rebuild.

`skills/` is a byte-for-byte copy of the upstream OpenScience tree, produced by
`tools/rebuild.py` via `shutil.copytree(..., dirs_exist_ok=True)`. Anything fixed
directly under `skills/` is therefore silently reverted the next time the tree is
rebuilt from upstream source.

Two things happen here, in this order:

1. **Patches.** `tools/patches/` mirrors the tree layout and holds corrected copies.
   Each one is copied back over the same relative path in `skills/`.
2. **Removals.** `tools/patches/remove.txt` lists paths that must not be redistributed
   at all. They are deleted *after* the copies, so a patch cannot resurrect one.

Run it on its own:

    python tools/apply_patches.py

`rebuild.py` calls both steps automatically as its last actions.

Exit status is 0 when every patch was applied, 1 if a patch target could not be
written (so a broken patch never passes unnoticed in a build). A removal whose target
is already gone is *not* an error — the list is idempotent.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PATCHES = HERE / "patches"
REMOVE_LIST = PATCHES / "remove.txt"

# Matched against the path *relative to tools/patches/*, so the directory's own README
# and remove list are ignored while a genuine upstream README.md patch still applies.
SKIP_REL = {"README.md", "remove.txt", ".gitkeep"}
# A stray __pycache__ from syntax-checking a patched script would otherwise be treated as
# a patch source, be skipped for a missing target, and fail the whole build.
SKIP_PARTS = {"__pycache__"}
SKIP_SUFFIX = (".pyc", ".pyo")


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
        if not src.is_file():
            continue
        rel = src.relative_to(PATCHES)
        if rel.as_posix() in SKIP_REL:
            continue
        if SKIP_PARTS & set(rel.parts) or src.name.endswith(SKIP_SUFFIX):
            continue
        dst = ROOT / rel
        if not dst.parent.is_dir():
            # The upstream tree no longer has this skill: report it rather than
            # creating a stray directory that the next rebuild would delete.
            print(f"  SKIP  {rel.as_posix()}  (target directory missing)")
            skipped.append(rel)
            continue
        # Byte-for-byte, so a patch copy has to carry the line endings the repository
        # stores -- LF, per .gitattributes. A CRLF copy would leave manifest.json (which
        # records byte sizes) disagreeing with the blob Gitee actually serves, and every
        # download of that file would then fail its size check.
        if b"\r\n" in src.read_bytes():
            print(f"  WARN  {rel.as_posix()}  (CRLF line endings; manifest sizes will not match)")
        shutil.copyfile(src, dst)
        applied.append(rel)
        if verbose:
            print(f"  OK    {rel.as_posix()}")

    if verbose:
        total = len(applied) + len(skipped)
        print(f"apply_patches: {len(applied)}/{total} patch(es) applied.")
    return applied, skipped


def removal_list() -> list[Path]:
    """Parse tools/patches/remove.txt into repo-relative paths."""
    if not REMOVE_LIST.is_file():
        return []
    out: list[Path] = []
    for line in REMOVE_LIST.read_text(encoding="utf-8").splitlines():
        line = line.split(" #", 1)[0].strip()
        if not line or line.startswith("#"):
            continue
        p = Path(line)
        if p.is_absolute() or ".." in p.parts:
            print(f"  SKIP  {line}  (refusing a path outside the tree)")
            continue
        out.append(p)
    return out


def remove(verbose: bool = True) -> tuple[list[Path], list[Path]]:
    """Delete every path listed in tools/patches/remove.txt.

    Returns (removed, already_gone). Running this twice is safe.
    """
    entries = removal_list()
    if not entries:
        if verbose:
            print("apply_patches: no removals listed, nothing to delete.")
        return [], []

    removed: list[Path] = []
    gone: list[Path] = []
    for rel in entries:
        dst = ROOT / rel
        if not dst.exists():
            gone.append(rel)
            if verbose:
                print(f"  GONE  {rel.as_posix()}  (already absent)")
            continue
        dst.unlink()
        removed.append(rel)
        if verbose:
            print(f"  DEL   {rel.as_posix()}")

    if verbose:
        print(f"apply_patches: {len(removed)}/{len(entries)} withheld file(s) deleted.")
    return removed, gone


def main() -> int:
    applied, skipped = apply()
    remove()
    return 1 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
