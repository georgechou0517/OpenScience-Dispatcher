# Local patches

`skills/` is a byte-for-byte copy of the upstream OpenScience skill tree, produced
by `tools/rebuild.py` with `shutil.copytree(..., dirs_exist_ok=True)`. A fix written
directly under `skills/` is therefore **silently reverted** the next time the tree is
rebuilt from upstream source.

This directory mirrors the tree layout and carries two kinds of change, applied in this
order:

1. **Patches** — corrected copies of upstream files, laid back over the same relative path.
2. **Withholdings** — paths listed in [`remove.txt`](remove.txt), deleted *after* the
   copies so that a patch cannot resurrect one.

`rebuild.py` runs both as its final step; you can also run them by hand:

```bash
python tools/apply_patches.py
```

To add a patch: copy the corrected file to the same relative path under `tools/patches/`,
then re-run `apply_patches.py`. To stop shipping a file: add its path to `remove.txt` and
patch whatever still points at it. Keep the set small — prefer reporting an upstream bug
over maintaining a fork.

## Line endings matter

Write patch copies with **LF**. The repository stores LF (`* text=auto eol=lf` in
`.gitattributes`) and `manifest.json` records byte sizes, so a CRLF copy leaves the
manifest disagreeing with the blob Gitee actually serves and makes **every download of
that file fail its size check**. `apply_patches.py` prints a `WARN` when it sees one.

In Python that means `Path.write_text(..., newline="\n")` — the default is `os.linesep`,
which is CRLF on Windows and will silently corrupt a patch that way.

## Current patches

### `skills/biology/clinical-decision-support/scripts/generate_survival_analysis.py`

Kaplan-Meier report generator. Five defects fixed; without them the script either
crashes or emits numbers that would not survive peer review.

| # | Defect | Symptom | Fix |
|---|---|---|---|
| 1 | CI columns hard-coded as `KM_estimate_lower_0.95` | `KeyError` on every run — lifelines renames the columns to `<label>_lower_0.95` once `label=` is passed to `fit()` | resolve the columns dynamically by substring |
| 2 | Median-survival CI read from the **survival-probability** band | printed `16.7 months (95% CI 0.4-0.6)` — a probability interval labelled as months | Brookmeyer-Crowley limits: the times at which the S(t) confidence bands cross 0.5 |
| 3 | `generate_report()` hard-coded the title and dropped every CLI flag | `-t/-x/-y/--time-col/--event-col/--group-col` silently ignored | forward the arguments through `generate_report()` |
| 4 | Effect size computed as `(1 - hr)` for both directions | `Control has -48% increase in risk` for HR = 1.48 | split the branches: `(1-hr)` reduction when HR < 1, `(hr-1)` increase otherwise |
| 5 | Log-rank p-value drawn at `(0.02, 0.15)` | hidden behind the `lower left` legend | moved to `(0.02, 0.97)` |

Verified with `lifelines 0.30.3` / `matplotlib 3.11.2` on a 180-patient synthetic
two-arm dataset: the script completes, writes the PDF/PNG curve, the statistics
file, the LaTeX table and the number-at-risk CSV, and reports median survival with
a time-unit CI.

### `skills/biology/treatment-plans/` — `SKILL.md`, `README.md`, `scripts/generate_template.py`

The trailing half of the withholding below. Removing the template without these would
leave three dangling pointers, one of them fatal: `generate_template.py` looked the file
up by name, so `--type pain_management` would have raised `FileNotFoundError` from
`copy_template()`.

- `TEMPLATES` drops the `pain_management` entry (7 templates → 6), and the interactive
  prompt now counts the list instead of assuming `1-6`.
- Both prose lists drop their entry and say plainly that no pain template is bundled here.
- The `Example 5: Chronic Low Back Pain` walkthrough keeps its clinical content but no
  longer names a template that is not there.

## Withheld files

### `skills/biology/treatment-plans/assets/pain_management_plan.tex`

Withdrawn 2026-10-16. Concrete opioid prescribing tables — Oxycodone 5 mg q6h, MME
thresholds, naloxone co-prescribing — which Gitee's content-compliance filter refuses to
serve (`HTTP 451 Unavailable For Legal Reasons`). It could therefore be neither fetched on
demand nor redistributed, so it is gone from the repository rather than shipped broken.

Deliberately **not** worked around: the Gitee API would hand the blob over happily, but
routing around a platform's compliance decision is not this package's call to make. The
clean fix is subtraction, which is what this file records.
