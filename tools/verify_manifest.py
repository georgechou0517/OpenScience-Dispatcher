"""Verify manifest.json against both the worktree and the committed git blobs.

Run from the skill root. Exits non-zero on any mismatch.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # this script lives in tools/
MANIFEST = ROOT / "manifest.json"

m = json.loads(MANIFEST.read_text(encoding="utf-8"))
rows = [(s + "/" + f, n) for s, rr in m["skills"].items() for f, n in rr]
print("totals:", m["totals"])
print("manifest entries:", len(rows))

# 1) worktree bytes
bad_wt = [p for p, n in rows if len((ROOT / p).read_bytes()) != n]
print("worktree byte mismatch:", len(bad_wt))
for p in bad_wt[:8]:
    print("   -", p)

# 2) committed blob bytes (authoritative: this is what Gitee serves)
want = {p: n for p, n in rows}
out = subprocess.run(
    ["git", "ls-tree", "-r", "-l", "HEAD", "--", "skills/"],
    capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
).stdout
have = {}
for line in out.splitlines():
    meta, path = line.split("\t", 1)
    have[path] = int(meta.split()[3])

bad_blob = [(p, want[p], have[p]) for p in want if p in have and want[p] != have[p]]
missing = [p for p in want if p not in have]
extra = [p for p in have if p not in want]
print("HEAD skills/ files:", len(have))
print("blob byte mismatch:", len(bad_blob))
for p, w, h in bad_blob[:8]:
    print(f"   - {p}  manifest={w} blob={h}")
print("in manifest, not in HEAD:", len(missing))
for p in missing[:8]:
    print("   -", p)
print("in HEAD, not in manifest:", len(extra))
for p in extra[:8]:
    print("   -", p)

ok = not (bad_wt or bad_blob or missing or extra)
print("verdict:", "ALL CONSISTENT" if ok else "MISMATCH")
sys.exit(0 if ok else 1)
