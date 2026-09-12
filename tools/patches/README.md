# Local patches

`skills/` is a byte-for-byte copy of the upstream OpenScience skill tree, produced
by `tools/rebuild.py` with `shutil.copytree(..., dirs_exist_ok=True)`. A fix written
directly under `skills/` is therefore **silently reverted** the next time the tree is
rebuilt from upstream source.

This directory mirrors the tree layout and holds the corrected copies. `rebuild.py`
re-applies them as its final step; you can also run it by hand:

```bash
python tools/apply_patches.py
```

To add a patch: copy the corrected file to the same relative path under
`tools/patches/`, then re-run `apply_patches.py`. Keep the set small — prefer
reporting an upstream bug over maintaining a fork.

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
