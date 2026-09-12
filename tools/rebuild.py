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

Two trees feed one registry:

    skills/        byte-for-byte upstream OpenScience skills, overwritten on every
                   rebuild — never hand-edit, use tools/patches/ instead
    local-skills/  this package's own skills, hand-maintained, never overwritten

`local-skills/` entries are merged into registry.json with `origin: local` so a
rebuild cannot silently drop them. `tools/aliases.json` then layers Chinese trigger
words onto skills whose upstream metadata is English-only, which is what makes those
skills reachable from a Chinese query.
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
LOCAL_DIRNAME = "local-skills"
ALIASES_FILE = Path(__file__).resolve().parent / "aliases.json"


def load_aliases():
    """Extra retrieval tags for skills whose upstream metadata is English-only.

    Upstream ships English descriptions and frequently no tags at all, so a Chinese
    query can never reach those skills: "科研绘图" cannot match a skill whose only
    words are "publication-ready figures". The overlay adds the Chinese trigger words
    (plus a few English synonyms) at build time, without hand-editing files that the
    next rebuild would overwrite. Keys starting with "_" are comments.
    """
    if not ALIASES_FILE.is_file():
        return {}
    try:
        data = json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
        print(f"[rebuild] WARNING: could not read {ALIASES_FILE.name} ({exc})", file=sys.stderr)
        return {}
    out = {}
    for name, extra in data.items():
        if name.startswith("_") or not isinstance(extra, list):
            continue
        out[name] = [str(t) for t in extra if str(t).strip()]
    return out


def parse_frontmatter(text):
    """Parse a simple YAML frontmatter block delimited by --- lines.

    Handles four shapes, which is everything the bundled skills actually use:
    inline `[a, b]` lists, `key:` followed by an indented `- item` block list,
    and plain or folded (`>-`) multi-line scalars. The last one matters: a
    `description:` wrapped over several lines used to be truncated at the first
    line break, which quietly gutted the search index for any skill that wrote
    its description that way.
    """
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}, text
    data = {}
    cur = None
    for line in m.group(1).split("\n"):
        if not line.strip():
            continue
        indented = line[:1] in (" ", "\t")
        body = line.strip()
        km = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", body)
        if km and not indented:
            key, val = km.group(1), km.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                items = re.findall(r"([^,\[\]]+)", val[1:-1])
                data[key] = [x.strip().strip('"').strip("'") for x in items if x.strip()]
                cur = None
            elif val in (">", "|", ">-", "|-", ">+", "|+"):
                data[key] = ""
                cur = key
            elif val == "":
                data[key] = None
                cur = key
            else:
                data[key] = val.strip().strip('"').strip("'")
                cur = key
        elif indented and cur is not None:
            if body.startswith("- ") and not isinstance(data.get(cur), str):
                if not isinstance(data.get(cur), list):
                    data[cur] = []
                data[cur].append(body[2:].strip().strip('"').strip("'"))
            elif isinstance(data.get(cur), str):
                data[cur] = (data[cur] + " " + body).strip()
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


def collect(src_skills, path_prefix="skills", origin="upstream"):
    """Scan a `<category>/<name>/SKILL.md` tree into registry records.

    `path_prefix` is where the tree lives relative to the package root; it is
    written into each record's `path` and is what `dispatch.py load` resolves.
    """
    records = []
    for fpath in sorted(Path(src_skills).rglob("SKILL.md")):
        d = fpath.parent
        rel = d.relative_to(src_skills)
        parts = rel.parts
        folder = parts[0] if len(parts) > 1 else ""
        skill_dir = parts[-1]
        text = fpath.read_text(encoding="utf-8", errors="replace")
        fm, body = parse_frontmatter(text)
        fm_cat = fm.get("category")
        category = fm_cat.strip() if isinstance(fm_cat, str) and fm_cat.strip() else (folder or "other")
        # `triggers:` plays the same retrieval role as `tags:` for skills written in the
        # Claude Code house style (which upstream OpenScience does not use). Falling back
        # to it is what lets those skills be found by their own trigger words.
        tags = fm.get("tags") or fm.get("triggers") or []
        func = clean_functionality(
            get_section(body, "when to use this skill", "when to use", "when to use vs alternatives",
                        "common use cases", "core capabilities", "core workflows", "common workflows")
        ) or clean_functionality(first_paragraph(body))
        name = fm.get("name") or skill_dir
        rec = {
            "name": name,
            "category": category,
            "description": re.sub(r"\s+", " ", (fm.get("description") or "")).strip(),
            "functionality": func,
            "license": fm.get("license") or "",
            "tags": [tags] if isinstance(tags, str) else tags,
            "version": fm.get("version") or "",
            "author": fm.get("author") or "",
            "path": f"{path_prefix}/{category}/{name}",
            "source_folder": folder or "(root)",
            "_src": str(d),
        }
        if origin != "upstream":
            rec["origin"] = origin
        records.append(rec)
    records.sort(key=lambda r: (r["category"], r["name"]))
    return records


def main():
    ap = argparse.ArgumentParser(description="Rebuild skills/ and registry.json from an OpenScience checkout")
    ap.add_argument("--source", required=True, help="path to an OpenScience repository checkout")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent),
                    help="package root to write into (default: this package)")
    ap.add_argument("--no-copy", action="store_true", help="only rewrite registry.json, do not copy skill folders")
    ap.add_argument("--no-local", action="store_true",
                    help=f"do not merge {LOCAL_DIRNAME}/ into registry.json")
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

    # Locally authored skills are merged into the registry but never copied over:
    # `local-skills/` already holds their files and is the source of truth here.
    local_dir = out / LOCAL_DIRNAME
    local_records = []
    if local_dir.is_dir() and not a.no_local:
        upstream_names = {r["name"] for r in records}
        for r in collect(local_dir, path_prefix=LOCAL_DIRNAME, origin="local"):
            r.pop("_src", None)
            if r["name"] in upstream_names:
                print(f"[rebuild] WARNING: {LOCAL_DIRNAME}/{r['name']} shadows an upstream skill; skipped",
                      file=sys.stderr)
                continue
            local_records.append(r)
        records.extend(local_records)
        records.sort(key=lambda r: (r["category"], r["name"]))

    # English-only upstream metadata is bridged with Chinese trigger words here, so the
    # fix lives in tools/aliases.json instead of inside folders a rebuild overwrites.
    aliases = load_aliases()
    if aliases:
        by_name = {r["name"]: r for r in records}
        applied, missing = 0, []
        for name, extra in aliases.items():
            rec = by_name.get(name)
            if rec is None:
                missing.append(name)
                continue
            tags = list(rec.get("tags") or [])
            for t in extra:
                if t not in tags:
                    tags.append(t)
            rec["tags"] = tags
            applied += 1
        print(f"[rebuild] aliases: {applied} skill(s) augmented from {ALIASES_FILE.name}")
        if missing:
            print(f"[rebuild] WARNING: alias target(s) not found: {', '.join(missing)}", file=sys.stderr)

    (out / "registry.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[rebuild] source : {src}")
    print(f"[rebuild] skills : {len(records)} records, {copied} folders copied")
    if local_records:
        print(f"[rebuild] local  : {len(local_records)} record(s) merged from {LOCAL_DIRNAME}/")
    elif local_dir.is_dir():
        print(f"[rebuild] local  : {LOCAL_DIRNAME}/ present but empty or skipped")
    counts = Counter(r["category"] for r in records)
    for k in sorted(counts, key=lambda x: (-counts[x], x)):
        print(f"  {counts[k]:>3}  {k}")
    print(f"[rebuild] wrote  : {out / 'registry.json'}")
    print("[rebuild] note   : mcp/catalog.json is a hand transcription of the upstream catalog.ts and is not rebuilt.")

    # The copy above overwrites the tree with pristine upstream files, so any fix
    # kept in tools/patches/ has to be laid back down on top of it.
    if not a.no_copy:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            from apply_patches import apply as apply_local_patches
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[rebuild] WARNING: could not load apply_patches ({exc}); tree left unpatched", file=sys.stderr)
        else:
            print("[rebuild] local patches:")
            _applied, _skipped = apply_local_patches()
            if _skipped:
                print(f"[rebuild] WARNING: {len(_skipped)} patch(es) had no target", file=sys.stderr)


if __name__ == "__main__":
    main()
