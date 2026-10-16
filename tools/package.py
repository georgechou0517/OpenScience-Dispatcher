#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Part of OpenScience Dispatcher (dispatcher layer). Upstream content and full notices:
# see LICENSE, NOTICE, ATTRIBUTION.md, THIRD-PARTY-NOTICES.md.
"""Build the distribution zips. Zero third-party dependencies, Python 3.8+.

    openscience-dispatcher-skill.zip   submission build — flat root, no skills/
    openscience-dispatcher-full.zip    self-hosted build — everything, wrapped

Why two. The full tree is 1665 files / 21 MB because it carries all 312 upstream
sub-skills, and no host that accepts this package will swallow that. Verified 2026-10-16:
skillhub.cn caps an upload at 10 MB with ~200 files *suggested*; clawhub caps a bundle at
50 MB with **no** file-count limit. The submission build drops `skills/` and ships
`manifest.json` instead, so `dispatch.py fetch` can pull back exactly the files a task
needs — from the Gitee repo, which always keeps `skills/` because that is the source
those downloads come from.

The submission zip is flat on purpose: skillhub requires SKILL.md at the archive root,
so an extractor drops it straight into .../skills/openscience-dispatcher/.

    python tools/package.py                    # both, into ./dist
    python tools/package.py --which slim
    python tools/package.py --out ~/Desktop
"""
from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules", "dist"}
SKIP_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}
SKIP_SUFFIX = (".pyc", ".pyo", ".part")
SLIM_EXCLUDE_TOP = frozenset({"skills"})

# skillhub.cn upload caps. Reported, not enforced: a maintainer may still want the file
# even when it is over, but silently shipping an unpublishable archive is not useful.
# clawhub's only stated cap is 50 MB per bundle, so clearing these clears that too.
LIMIT_FILES = 200
LIMIT_BYTES = 10 * 1024 * 1024


def iter_files(exclude_top=frozenset()):
    """Yield (absolute path, path relative to the package root) for everything shippable."""
    for base, dirs, files in os.walk(ROOT):
        rel = Path(base).relative_to(ROOT)
        if rel.parts and rel.parts[0] in exclude_top:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in sorted(files):
            if f in SKIP_FILES or f.endswith(SKIP_SUFFIX):
                continue
            p = Path(base) / f
            yield p, p.relative_to(ROOT)


def build(dst, prefix="", exclude_top=frozenset()):
    dst.parent.mkdir(parents=True, exist_ok=True)
    files = 0
    raw = 0
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for src, rel in iter_files(exclude_top):
            arc = (Path(prefix) / rel) if prefix else rel
            z.write(src, arc.as_posix())
            files += 1
            try:
                raw += src.stat().st_size
            except OSError:
                pass
    return {"path": dst, "files": files, "raw": raw, "zip": dst.stat().st_size}


def report(tag, info, expect_root=None):
    z = info["zip"]
    print(f"[{tag}] {info['path'].name}")
    print(f"   文件 {info['files']} · 解压 {info['raw'] / 1048576:.2f} MB · zip {z / 1048576:.2f} MB")
    with zipfile.ZipFile(info["path"]) as zf:
        names = zf.namelist()
        tops = sorted({n.split("/")[0] for n in names})
        if expect_root is not None:
            ok = expect_root in names
            print(f"   {expect_root} 位于 zip 根: {'是' if ok else '否'}")
        print(f"   顶层: {', '.join(tops[:12])}{' …' if len(tops) > 12 else ''}")
        leaks = [n for n in names if "__pycache__" in n or n.endswith(".pyc") or "/.git/" in n]
        if leaks:
            print(f"   ⚠ 混入 {len(leaks)} 个应排除的条目，例如 {leaks[0]}")
    if info["files"] > LIMIT_FILES or info["raw"] > LIMIT_BYTES:
        print(f"   ⚠ 超出 skillhub.cn 上限（{LIMIT_FILES} 文件 / "
              f"{LIMIT_BYTES / 1048576:.0f} MB 解压），这个包投不上去")
    else:
        print(f"   ✓ 在 skillhub.cn 上限内（{LIMIT_FILES} 文件 / "
              f"{LIMIT_BYTES / 1048576:.0f} MB 解压）")


def main():
    ap = argparse.ArgumentParser(description="Build the slim and full distribution zips")
    ap.add_argument("--out", default=str(ROOT / "dist"), help="output directory (default: ./dist)")
    ap.add_argument("--which", choices=["both", "slim", "full"], default="both")
    a = ap.parse_args()
    out = Path(a.out).expanduser().resolve()

    if a.which in ("both", "slim"):
        info = build(out / "openscience-dispatcher-skill.zip", exclude_top=SLIM_EXCLUDE_TOP)
        report("slim", info, expect_root="SKILL.md")
    if a.which in ("both", "full"):
        info = build(out / "openscience-dispatcher-full.zip", prefix="openscience-dispatcher")
        report("full", info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
