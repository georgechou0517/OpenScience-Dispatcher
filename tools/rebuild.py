#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Part of OpenScience Dispatcher (dispatcher layer). Upstream content and full notices:/n# see LICENSE, NOTICE, ATTRIBUTION.md, THIRD-PARTY-NOTICES.md.
"""Rebuild skills/ and registry.json for this package from an OpenScience checkout.

Zero third-party dependencies. Python 3.8+.

Usage:
    git clone https://github.com/synthetic-sciences/openscience
    python tools/rebuild.py --source ./openscience
    python tools/rebuild.py --source ./openscience --out . --no-copy
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

SRC_SUBPATH = Path("backend") / "cli" / "skills"


def parse_frontmatter(text):
    """Parse a simple YAML frontmatter block delimited by --- lines."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}, text
    data = {}
    cur = None
    for line in m.group(1).split("\n"):
        if not line.strip():
            continue
        km = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line)
        if km and not line.startswith(" "):
            key, val = km.group(1), km.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                items = re.findall(r"([^,\[\]]+)", val[1:-1])
                data[key] = [x.strip().strip('"').strip("'") for x in items if x.strip()]
                cur = None
            elif val == "":
                data[key] = None
                cur = key
            else:
                data[key] = val.strip().strip('"').strip("'")
                cur = None
        elif line.lstrip().startswith("- ") and cur is not None:
            if not isinstance(data.get(cur), list):
                data[cur] = []
            data[cur].append(line.lstrip()[2:].strip().strip('"').strip("'"))
    return data, text[m.end():]


def get_section(body, *titles):
    """Text of the first heading whose title matches any of `titles` (prefix, case-insensitive)."""
    lines = body.splitlines()
    for i, l in enumerate(lines):
        mm = re.match(r"^#{2,3}\s+(.*)$", l)
        if not mm:
            continue
        title = mm.group(1).strip().lower()
        if any(title == t.lower() or title.startswith(t.lower()) for t in titles):
            buf = []
            for l2 in lines[i + 1:]:
                if re.match(r"^#{1,3}\s+", l2):
                    break
                buf.append(l2)
            return "\n".join(buf).strip()
    return ""


def first_paragraph(body):
    for p in (p.strip() for p in re.split(r"\n\s*\n", body)):
        if p and not p.startswith("#") and len(p) > 20:
            return p
    return ""


DROP_PREFIXES = (
    "use this skill when:", "use this skill when",
    "this skill should be used when:", "this skill should be used when",
    "this skill should be triggered when:", "this skill should be triggered when",
    "this skill is used when:", "this skill is triggered when:",
    "when to use this skill:", "when to use this skill", "when to use:",
    "use cases:", "common use cases:", "core capabilities:", "core workflows:",
    "common workflows:", "use the", "use it when", "triggers:",
)
PREAMBLE = re.compile(
    r"^(use|this|when|these|the following|common|core|typical|triggers?|scenarios?|"
    r"overview|purpose|examples?|capabilit|workflow|use ?cases?)",
    re.I,
)
LEADIN = re.compile(
    r"^\s*(?:"
    r"use this skill when\s+|use this skill for\s+|use this skill to\s+|"
    r"use this skill if\s+|use this skill\s+|"
    r"this skill should be used when\s+|this skill should be used\s+|"
    r"this skill is (?:used|triggered|intended|designed) (?:when|for|to)\s+|"
    r"when to use this skill\s*[:：]?\s*"
    r")",
    re.I,
)
LIST_LEADIN = re.compile(
    r"(?:in any of the following (?:scenarios|situations|cases)|"
    r"in (?:the )?following (?:scenarios|situations|cases)|"
    r"for the following (?:use )?cases|"
    r"in (?:scenarios|cases) such as|including|such as|for example)"
    r"\s*[:：]\s*",
    re.I,
)


def clean_functionality(text, limit=600):
    if not text:
        return ""
    out = []
    for raw in (l.strip() for l in text.splitlines()):
        if not raw:
            continue
        l = re.sub(r"^[-*]\s+", "", raw)
        l = re.sub(r"\*\*|__|`", "", l)
        l = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", l)
        l = re.sub(r"\s+", " ", l).strip()
        low = l.lower()
        if len(l) < 60 and any(low == p or low.startswith(p) for p in DROP_PREFIXES):
            continue
        if len(l) < 75 and l.endswith(":") and PREAMBLE.match(l):
            continue
        if l:
            out.append(l)

    joined = re.sub(r"\s+", " ", "；".join(out)).strip()
    # inline lead-ins carry real content after the prefix, so strip the prefix only
    prev = None
    while prev != joined:
        prev = joined
        joined = LEADIN.sub("", joined).strip()
    joined = LIST_LEADIN.sub("", joined)
    joined = re.sub(r"\s+([；;])", r"\1", joined)
    joined = re.sub(r"[；;]{2,}", "；", joined).strip("；; ")
    if joined and joined[0].islower():
        joined = joined[0].upper() + joined[1:]
    if len(joined) > limit:
        joined = joined[:limit].rstrip("；") + "…"
    return joined


def collect(src_skills):
    records = []
    for fpath in sorted(src_skills.rglob("SKILL.md")):
        d = fpath.parent
        rel = d.relative_to(src_skills)
        parts = rel.parts
        folder = parts[0] if len(parts) > 1 else ""
        skill_dir = parts[-1]
        text = fpath.read_text(encoding="utf-8", errors="replace")
        fm, body = parse_frontmatter(text)
        fm_cat = fm.get("category")
        category = fm_cat.strip() if isinstance(fm_cat, str) and fm_cat.strip() else (folder or "other")
        tags = fm.get("tags") or []
        func = clean_functionality(
            get_section(body, "when to use this skill", "when to use", "when to use vs alternatives",
                        "common use cases", "core capabilities", "core workflows", "common workflows")
        ) or clean_functionality(first_paragraph(body))
        name = fm.get("name") or skill_dir
        records.append({
            "name": name,
            "category": category,
            "description": re.sub(r"\s+", " ", (fm.get("description") or "")).strip(),
            "functionality": func,
            "license": fm.get("license") or "",
            "tags": [tags] if isinstance(tags, str) else tags,
            "version": fm.get("version") or "",
            "author": fm.get("author") or "",
            "path": f"skills/{category}/{name}",
            "source_folder": folder or "(root)",
            "_src": str(d),
        })
    records.sort(key=lambda r: (r["category"], r["name"]))
    return records


def main():
    ap = argparse.ArgumentParser(description="Rebuild skills/ and registry.json from an OpenScience checkout")
    ap.add_argument("--source", required=True, help="path to an OpenScience repository checkout")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent),
                    help="package root to write into (default: this package)")
    ap.add_argument("--no-copy", action="store_true", help="only rewrite registry.json, do not copy skill folders")
    a = ap.parse_args()

    src = Path(a.source).expanduser().resolve() / SRC_SUBPATH
    if not src.is_dir():
        print(f"[rebuild] not found: {src}", file=sys.stderr)
        print("[rebuild] --source must point at an OpenScience checkout (the repo containing backend/cli/skills)", file=sys.stderr)
        sys.exit(1)

    out = Path(a.out).expanduser().resolve()
    (out / "skills").mkdir(parents=True, exist_ok=True)

    records = collect(src)
    copied = 0
    for r in records:
        src_dir = r.pop("_src")
        if not a.no_copy:
            shutil.copytree(src_dir, out / r["path"], dirs_exist_ok=True)
            copied += 1

    (out / "registry.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[rebuild] source : {src}")
    print(f"[rebuild] skills : {len(records)} records, {copied} folders copied")
    counts = Counter(r["category"] for r in records)
    for k in sorted(counts, key=lambda x: (-counts[x], x)):
        print(f"  {counts[k]:>3}  {k}")
    print(f"[rebuild] wrote  : {out / 'registry.json'}")
    print("[rebuild] note   : mcp/catalog.json is a hand transcription of the upstream catalog.ts and is not rebuilt.")


if __name__ == "__main__":
    main()
