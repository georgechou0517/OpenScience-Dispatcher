#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""漏斗图（funnel plot）+ Egger 检验：从 CSV 产出发表偏倚诊断图。

CSV 列（表头大小写、空格不敏感，接受别名）：
  study  研究标签（可选，写了会在点旁标注）
  est    效应量（必需）
  se     标准误（必需；也接受 stderr / standard_error / 标准误）

用法：
  python funnel_plot.py -i studies.csv -o out/fig3-funnel --measure "log HR"

说明：
  · 汇总线默认用固定效应逆方差法现算；如已有合并值，用 --pooled 直接给。
  · 漏斗边界为 95% 伪置信区间（pooled ± 1.96·SE）。纳入研究 < 10 项时
    检验功效不足，图里会打印提示——这不是可以视而不见的技术细节。
  · Egger 检验需要 scipy 才能给出 p 值；缺 scipy 时只报告截距与 t 值。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import C, apply_paper_style, figure_width, save  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ALIASES = {
    "study": ("study", "name", "label", "trial", "id", "研究"),
    "est": ("est", "estimate", "effect", "es", "point", "hr", "or", "rr", "md", "smd", "效应量"),
    "se": ("se", "stderr", "standard_error", "sd", "std_err", "标准误"),
}
NULLS = {"", "na", "n/a", "nan", "none", "null", "-", "--", "—", "?"}


def _norm(h):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", (h or "").strip().lower()).strip("_")


def _num(v):
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in NULLS:
        return None
    try:
        return float(s)
    except ValueError:
        m = re.search(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s)
        return float(m.group(0)) if m else None


def load(path):
    rev = {alias: canon for canon, names in ALIASES.items() for alias in names}
    rows, unknown = [], set()
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for raw in csv.DictReader(fh):
            if not any((v or "").strip() for v in raw.values()):
                continue
            rec = {}
            for k, v in raw.items():
                if k is None:
                    continue
                canon = rev.get(_norm(k))
                if canon is None:
                    unknown.add(k.strip())
                else:
                    rec[canon] = v
            est, se = _num(rec.get("est")), _num(rec.get("se"))
            if est is None or se is None:
                continue
            rows.append({"study": (rec.get("study") or "").strip(), "est": est, "se": se})
    return rows, unknown


def fixed_effect_pooled(rows):
    """逆方差加权固定效应合并值。"""
    w = [1.0 / (r["se"] ** 2) for r in rows]
    return sum(wi * r["est"] for wi, r in zip(w, rows)) / sum(w)


def egger(rows):
    """Egger 回归：est/se 对 1/se 回归，检验截距是否为 0（发表偏倚）。"""
    n = len(rows)
    if n < 3:
        return {"ok": False, "note": "研究数 < 3，Egger 检验无法进行"}
    x = [1.0 / r["se"] for r in rows]
    y = [r["est"] / r["se"] for r in rows]
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    if sxx == 0:
        return {"ok": False, "note": "精确度无变异，Egger 检验无法进行"}
    slope = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / sxx
    intercept = my - slope * mx
    resid = [yi - (intercept + slope * xi) for xi, yi in zip(x, y)]
    dof = n - 2
    s2 = sum(e ** 2 for e in resid) / dof
    se_int = (s2 * (1.0 / n + mx ** 2 / sxx)) ** 0.5
    out = {"ok": True, "intercept": intercept, "slope": slope, "se_intercept": se_int, "dof": dof}
    if se_int > 0:
        t = intercept / se_int
        out["t"] = t
        try:
            from scipy import stats
            out["p"] = float(2 * stats.t.sf(abs(t), dof))
        except Exception:
            out["note"] = "未安装 scipy，只报告 t 值，不报告 p 值"
    return out


def plot(rows, args, pooled):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_paper_style(font_size=args.font_size)
    width = figure_width(args.journal, args.span)
    fig, ax = plt.subplots(figsize=(width, width * 0.92))

    ses = [r["se"] for r in rows]
    smax = max(ses) * 1.08
    ests = [r["est"] for r in rows]
    lo = min(min(ests), pooled - 1.96 * smax)
    hi = max(max(ests), pooled + 1.96 * smax)
    pad = 0.06 * (hi - lo)
    lo, hi = lo - pad, hi + pad

    # 95% 伪置信区间边界
    yy = [0.0, smax]
    for sign in (-1, 1):
        ax.plot([pooled + sign * 1.96 * 0.0, pooled + sign * 1.96 * smax], yy,
                color=C["line"], lw=0.8, ls="--", zorder=1)
    ax.axvline(pooled, color=C["line"], lw=0.9, zorder=1)

    ax.scatter(ests, ses, s=args.marker_size, marker="o",
               facecolor=C["intervention"], edgecolor="white", linewidth=0.4, zorder=3)
    if args.label_studies:
        for r in rows:
            ax.annotate(r["study"], (r["est"], r["se"]), textcoords="offset points",
                        xytext=(4, 3), fontsize=args.font_size - 1.5, color=C["neutral"])

    ax.set_xlim(lo, hi)
    ax.set_ylim(smax, 0)          # 标准误向下增大，与惯例一致
    ax.set_xlabel(args.measure, fontsize=args.font_size + 0.5)
    ax.set_ylabel("Standard error", fontsize=args.font_size + 0.5)
    if args.title:
        ax.set_title(args.title, fontsize=args.font_size + 1.5, loc="left")

    notes = [f"k = {len(rows)}", f"pooled = {pooled:.3g}"]
    if args.egger and args.egger.get("ok"):
        if "p" in args.egger:
            notes.append(f"Egger p = {args.egger['p']:.3f}")
        else:
            notes.append(f"Egger intercept = {args.egger['intercept']:.3g}")
    # 白底文本框，避免落在数据点上时看不清
    pad = dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.6)
    ax.text(0.985, 0.965, "   ".join(notes), transform=ax.transAxes, ha="right",
            va="top", fontsize=args.font_size - 1, color=C["neutral"], bbox=pad)
    if len(rows) < 10:
        ax.text(0.015, 0.03, "k < 10: underpowered for asymmetry tests",
                transform=ax.transAxes, ha="left", va="bottom",
                fontsize=args.font_size - 1, color=C["control"], bbox=pad)
    fig.tight_layout()
    return fig


def main():
    ap = argparse.ArgumentParser(description="生成漏斗图并做 Egger 检验")
    ap.add_argument("-i", "--input", required=True)
    ap.add_argument("-o", "--output", required=True, help="输出文件名前缀")
    ap.add_argument("--measure", default="Effect estimate", help="x 轴标签，如 'log HR'")
    ap.add_argument("--pooled", type=float, help="合并效应量；默认用固定效应逆方差法现算")
    ap.add_argument("--title")
    ap.add_argument("--label-studies", action="store_true", help="在点旁标注研究名")
    ap.add_argument("--no-egger", action="store_true", help="跳过 Egger 检验")
    ap.add_argument("--marker-size", type=float, default=26.0)
    ap.add_argument("--journal", default="generic")
    ap.add_argument("--span", default="single")
    ap.add_argument("--font-size", type=float, default=7.0)
    ap.add_argument("--formats", default="pdf,png")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--summary", help="把结果摘要写成 JSON")
    args = ap.parse_args()

    rows, unknown = load(args.input)
    if len(rows) < 2:
        print(f"[funnel] 至少需要 2 行有效数据（est + se），实际 {len(rows)} 行", file=sys.stderr)
        return 2
    if unknown:
        print(f"[funnel] 忽略无法识别的列: {', '.join(sorted(unknown))}", file=sys.stderr)
    if any(r["se"] <= 0 for r in rows):
        print("[funnel] 标准误必须 > 0，请检查 se 列", file=sys.stderr)
        return 1

    pooled = args.pooled if args.pooled is not None else fixed_effect_pooled(rows)
    args.egger = {"ok": False} if args.no_egger else egger(rows)

    fig = plot(rows, args, pooled)
    written = save(fig, args.output, formats=args.formats.split(","), dpi=args.dpi)
    import matplotlib.pyplot as plt
    plt.close(fig)

    summary = {
        "input": str(args.input),
        "k": len(rows),
        "pooled_fixed_effect": pooled,
        "egger": args.egger,
        "outputs": written,
    }
    if args.summary:
        Path(args.summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[funnel] k = {len(rows)}，固定效应合并 = {pooled:.4g}")
    if args.egger.get("ok"):
        if "p" in args.egger:
            print(f"[funnel] Egger 截距 = {args.egger['intercept']:.4g}，p = {args.egger['p']:.4f}")
        else:
            print(f"[funnel] Egger 截距 = {args.egger['intercept']:.4g}（{args.egger.get('note', '')}）")
    elif not args.no_egger:
        print(f"[funnel] 未做 Egger 检验：{args.egger.get('note', '')}")
    for p in written:
        print(f"[funnel] 写出 {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
