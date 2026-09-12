#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Regenerate the README figure gallery under ``docs/figures/``.

    python tools/make_demo_figures.py

Four panels come from the bundled ``meta-analysis-figures`` skill and reuse the
demo CSVs committed in its ``examples/`` directory:

    forest-plot.png          forest_plot.py
    funnel-plot.png          funnel_plot.py
    prisma-2020-flow.png     prisma_flow.py
    rob2-traffic-light.png   rob_traffic_light.py

The fifth panel is the Kaplan-Meier curve produced by the upstream
``clinical-decision-support`` script; its cohort is synthesised here with a
fixed seed so the figure is reproducible without shipping patient data.

The figures are **illustrative only** — the numbers are demo data, not the
result of any real study.

Dependencies: matplotlib, numpy, scipy, pandas, lifelines.
"""

from __future__ import annotations

import argparse
import csv
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "local-skills" / "visualization" / "meta-analysis-figures"
SURVIVAL = (ROOT / "skills" / "biology" / "clinical-decision-support"
            / "scripts" / "generate_survival_analysis.py")
FIGS = ROOT / "docs" / "figures"


def run(cmd: list[str]) -> None:
    print("  $", " ".join(str(c) for c in cmd[1:]))
    proc = subprocess.run([str(c) for c in cmd], cwd=str(ROOT),
                          capture_output=True, text=True)
    tail = (proc.stdout or "").strip().splitlines()[-3:]
    for line in tail:
        print("    " + line)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        raise SystemExit(f"failed: {cmd[1]}")


def make_meta_figures() -> None:
    """The four meta-analysis panels: CSV/counts in, publication figure out."""
    ex = META / "examples"
    for script in ("forest_plot", "funnel_plot", "prisma_flow", "rob_traffic_light"):
        if not (META / "scripts" / f"{script}.py").is_file():
            raise SystemExit(f"missing script: {script}.py")

    run([sys.executable, META / "scripts" / "forest_plot.py",
         "-i", ex / "demo_forest.csv",
         "-o", FIGS / "forest-plot",
         "--measure", "Hazard ratio", "--log",
         "--favours", "Favours metformin|Favours control",
         "--journal", "nature", "--span", "double",
         "--summary", FIGS / "forest-plot.json"])

    run([sys.executable, META / "scripts" / "funnel_plot.py",
         "-i", ex / "demo_funnel.csv",
         "-o", FIGS / "funnel-plot",
         "--measure", "log hazard ratio",
         "--journal", "nature", "--span", "single",
         "--summary", FIGS / "funnel-plot.json"])

    run([sys.executable, META / "scripts" / "prisma_flow.py",
         "--identified", "2148", "--duplicates", "586",
         "--excluded-abstract", "1424",
         "--assessed", "138", "--excluded-fulltext", "114",
         "--reason", "Wrong population=52",
         "--reason", "No cardiovascular outcome=38",
         "--reason", "Duplicate cohort=24",
         "--included", "24", "--in-meta", "18",
         "--databases", "PubMed, Embase, CENTRAL",
         "-o", FIGS / "prisma-2020-flow",
         "--journal", "nature", "--span", "single",
         "--summary", FIGS / "prisma-2020-flow.json"])

    run([sys.executable, META / "scripts" / "rob_traffic_light.py",
         "-i", ex / "demo_rob.csv",
         "-o", FIGS / "rob2-traffic-light",
         "--tool", "rob2",
         "--title", "Risk of bias (RoB 2)",
         "--journal", "nature", "--span", "onehalf",
         "--summary", FIGS / "rob2-traffic-light.json"])


# --- Kaplan-Meier demo cohort -------------------------------------------------
# Two-arm immunotherapy cohort. Exponential survival times, ~30% censoring,
# fixed seed so the figure and the README stay in sync.
KM_ARMS = {
    "PD-L1 high": {"n": 62, "median": 18.0, "hazard_scale": 1.0},
    "PD-L1 low":  {"n": 58, "median": 9.0,  "hazard_scale": 1.0},
}


def write_km_cohort(path: Path, seed: int = 20260912) -> None:
    rng = random.Random(seed)
    rows = []
    for arm, spec in KM_ARMS.items():
        lam = 0.693147 / spec["median"]          # ln(2)/median for exponential
        for i in range(spec["n"]):
            t = rng.expovariate(lam)
            # censoring: administrative at 36 months, plus a little loss to follow-up
            censored = t > 36.0 or rng.random() < 0.18
            rows.append({
                "patient_id": f"{arm[6:].upper()[:4]}{i + 1:03d}",
                "time": round(min(t, 36.0) if censored else min(t, 36.0), 1),
                "event": 0 if censored else 1,
                "group": arm,
            })
    rng.shuffle(rows)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["patient_id", "time", "event", "group"])
        writer.writeheader()
        writer.writerows(rows)


def make_km_figure() -> None:
    if not SURVIVAL.is_file():
        print("  ! survival script not bundled — skipping Kaplan-Meier panel")
        return
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        cohort = tmpd / "pfs-demo.csv"
        write_km_cohort(cohort)
        run([sys.executable, SURVIVAL, cohort, "-o", tmpd,
             "-t", "Progression-free survival by PD-L1 status",
             "-x", "Time (months)", "-y", "Progression-free survival"])
        produced = tmpd / "survival_kaplan_meier.png"
        if not produced.is_file():
            raise SystemExit("survival script produced no PNG")
        shutil.copyfile(produced, FIGS / "kaplan-meier.png")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skip-km", action="store_true",
                    help="skip the Kaplan-Meier panel (no lifelines needed)")
    args = ap.parse_args()

    FIGS.mkdir(parents=True, exist_ok=True)
    print(f"Writing figures to {FIGS}")
    print("[1/2] meta-analysis panels")
    make_meta_figures()
    if args.skip_km:
        print("[2/2] Kaplan-Meier panel skipped")
    else:
        print("[2/2] Kaplan-Meier panel")
        make_km_figure()

    print("\nDone:")
    for png in sorted(FIGS.glob("*.png")):
        print(f"  {png.name:26s} {png.stat().st_size / 1024:7.1f} KB")
    print("\nreminder: figures use demo data and are illustrative only.")


if __name__ == "__main__":
    main()
