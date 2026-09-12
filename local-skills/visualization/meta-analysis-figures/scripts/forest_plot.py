#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""森林图（forest plot）生成器：从 CSV 直接产出投稿级森林图。

CSV 表头大小写、空格、下划线不敏感，并接受常用别名（见 ALIASES）。

列：
  study     研究标签（必需）
  est       效应量点估计（必需；kind=pooled 的行同样要填）
  lo / hi   95% 置信区间下限 / 上限（必需）
  weight    权重（可选；填了则方块面积正比于权重，不填则等大）
  subgroup  亚组标签（可选；相同标签的连续行视为一组，组间自动留空行）
  kind      study | pooled（可选，默认 study；pooled 渲染为菱形）

用法：
  python forest_plot.py -i studies.csv -o out/fig2-forest \\
      --measure "Hazard ratio" --log --journal nature --span double

  python forest_plot.py -i studies.csv -o out/fig2-forest \\
      --measure "Mean difference" --linear --null-value 0
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import C, apply_paper_style, check_numbers, figure_width, save  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ALIASES = {
    "study": ("study", "name", "label", "trial", "id", "研究", "研究名"),
    "est": ("est", "estimate", "effect", "es", "point", "hr", "or", "rr", "md", "smd", "效应量"),
    "lo": ("lo", "low", "lower", "lcl", "ci_low", "ci_lower", "ll", "下限"),
    "hi": ("hi", "high", "upper", "ucl", "ci_high", "ci_upper", "ul", "上限"),
    "weight": ("weight", "w", "wt", "weights", "权重"),
    "subgroup": ("subgroup", "group", "sub_group", "亚组"),
    "kind": ("kind", "type", "role", "row_type", "类型"),
}
NULLS = {"", "na", "n/a", "nan", "none", "null", "-", "--", "—", "?"}


def _norm(h):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", (h or "").strip().lower()).strip("_")


_HDR = {}


def _canon(h):
    key = _norm(h)
    if key in _HDR:
        return _HDR[key]
    for canon, names in ALIASES.items():
        if key in names:
            return canon
    return None


for _c, _names in ALIASES.items():
    for _n in _names:
        _HDR[_n] = _c


def _num(v):
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in NULLS:
        return None
    try:
        return float(s)
    except ValueError:
        # 容忍 "0.79 (0.71-0.88)" 这类整段粘贴：取第一个数
        m = re.search(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s)
        return float(m.group(0)) if m else None


def load(path):
    rows, unknown = [], set()
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            if not any((v or "").strip() for v in raw.values()):
                continue
            rec = {}
            for k, v in raw.items():
                if k is None:
                    continue
                canon = _canon(k)
                if canon is None:
                    unknown.add(k.strip())
                    continue
                rec[canon] = v
            rows.append({
                "study": (rec.get("study") or "").strip() or f"Study {len(rows) + 1}",
                "est": _num(rec.get("est")),
                "lo": _num(rec.get("lo")),
                "hi": _num(rec.get("hi")),
                "weight": _num(rec.get("weight")),
                "subgroup": (rec.get("subgroup") or "").strip(),
                "kind": (rec.get("kind") or "study").strip().lower() or "study",
            })
    return rows, unknown


def build(rows):
    """按顺序算 y 坐标；亚组切换时插入空行。"""
    out, y, prev = [], 0.0, None
    for r in rows:
        sg = r["subgroup"]
        if prev is not None and sg != prev:
            y -= 0.7
        out.append((y, r))
        y -= 1.0
        prev = sg
    return out


def fmt(v, nd=2):
    return "—" if v is None else f"{v:.{nd}f}"


def plot(rows, args):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, FuncFormatter

    apply_paper_style(font_size=args.font_size)
    placed = build(rows)
    ys = [y for y, _ in placed]
    top, bot = max(ys) + 1.0, min(ys) - 1.0

    n_study = sum(1 for _, r in placed if r["kind"] != "pooled")
    width = figure_width(args.journal, args.span)
    height = max(1.6, min(11.0, 0.30 * len(placed) + 1.5))
    if args.width_override:
        width = args.width_override
    if args.height_override:
        height = args.height_override

    fig, ax = plt.subplots(figsize=(width, height))
    null = args.null_value
    if args.scale == "log":
        ax.set_xscale("log")

    # 无效线
    ax.axvline(null, color=C["line"], lw=0.8, ls="--", zorder=1)

    weights = [r["weight"] for _, r in placed if r["kind"] != "pooled" and r["weight"]]
    wmax = max(weights) if weights else None

    for y, r in placed:
        est, lo, hi = r["est"], r["lo"], r["hi"]
        if est is None:
            continue
        if r["kind"] == "pooled":
            half = 0.30
            lo_ = lo if lo is not None else est
            hi_ = hi if hi is not None else est
            ax.add_patch(plt.Polygon(
                [[lo_, y], [est, y + half], [hi_, y], [est, y - half]],
                closed=True, facecolor=C["pooled"], edgecolor=C["pooled"], zorder=3))
            continue
        if lo is not None and hi is not None:
            ax.plot([lo, hi], [y, y], color=C["line"], lw=1.0, zorder=2,
                    solid_capstyle="butt")
            for xx in (lo, hi):
                ax.plot([xx, xx], [y - 0.13, y + 0.13], color=C["line"], lw=1.0, zorder=2)
        if wmax and r["weight"]:
            area = 12.0 + 98.0 * (r["weight"] / wmax)
        else:
            area = 42.0
        ax.scatter([est], [y], s=area, marker="s",
                   facecolor=C["intervention"], edgecolor="white", linewidth=0.4, zorder=3)

    # 右侧数值列
    if not args.no_text_column:
        txt_x = 1.02
        ax.text(txt_x, top - 0.35, f"{args.measure} (95% CI)", transform=ax.get_yaxis_transform(),
                ha="left", va="center", fontsize=args.font_size - 0.5, color=C["neutral"])
        for y, r in placed:
            if r["est"] is None:
                continue
            line = f"{fmt(r['est'], args.decimals)} ({fmt(r['lo'], args.decimals)}–{fmt(r['hi'], args.decimals)})"
            ax.text(txt_x, y, line, transform=ax.get_yaxis_transform(),
                    ha="left", va="center", fontsize=args.font_size - 0.5)

    labels = []
    for y, r in placed:
        sg = r["subgroup"]
        lab = r["study"]
        if r["kind"] == "pooled" and args.pooled_label:
            lab = args.pooled_label if lab.lower() in ("pooled", "overall", "total", "") else lab
        labels.append(lab)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=args.font_size)
    for tick, (y, r) in zip(ax.get_yticklabels(), placed):
        if r["kind"] == "pooled":
            tick.set_fontweight("bold")
    ax.set_ylim(bot, top)
    ax.set_xlabel(args.xlabel or args.measure, fontsize=args.font_size + 0.5)
    if args.title:
        ax.set_title(args.title, fontsize=args.font_size + 1.5, loc="left")

    # x 轴刻度
    vals = [v for _, r in placed for v in (r["lo"], r["hi"], r["est"]) if v]
    if vals:
        lo_, hi_ = min(vals), max(vals)
        if args.xticks:
            ticks = [float(t) for t in args.xticks.split(",") if t.strip()]
        elif args.scale == "log":
            ticks = _log_ticks(lo_, hi_, null)
        else:
            ticks = _lin_ticks(lo_, hi_)
        pad = 0.06 * (hi_ - lo_) if hi_ > lo_ else 0.1
        ax.set_xlim(max(lo_ - pad, 0.001) if args.scale == "log" else lo_ - pad, hi_ + pad)
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_locator(FixedLocator([]))
        ax.tick_params(axis="x", which="minor", bottom=False)

    # 利于哪一侧
    if args.favours:
        parts = [p.strip() for p in args.favours.split("|")]
        if len(parts) == 2:
            ax.text(0.02, -0.16, f"← Favours {parts[0]}", transform=ax.transAxes,
                    ha="left", fontsize=args.font_size - 1, color=C["intervention"])
            ax.text(0.98, -0.16, f"Favours {parts[1]} →", transform=ax.transAxes,
                    ha="right", fontsize=args.font_size - 1, color=C["control"])

    if not args.no_text_column:
        fig.subplots_adjust(left=0.30, right=0.68, top=0.96, bottom=0.12)
    else:
        fig.tight_layout()
    return fig


def _log_ticks(lo, hi, null):
    cand = [0.1, 0.2, 0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 10]
    inrange = [c for c in cand if lo * 0.9 <= c <= hi * 1.1]
    if null not in inrange:
        inrange.append(null)
    return sorted(set(inrange))[:8] or [lo, null, hi]


def _lin_ticks(lo, hi):
    span = hi - lo
    if span <= 0:
        return [lo]
    raw = span / 4.0
    mag = 10 ** math.floor(math.log10(raw))
    step = min([1, 2, 2.5, 5, 10], key=lambda m: abs(m * mag - raw)) * mag
    start = math.floor(lo / step) * step
    ticks, v = [], start
    while v <= hi * 1.05 and len(ticks) < 12:
        ticks.append(round(v, 10))
        v += step
    return ticks


def main():
    ap = argparse.ArgumentParser(description="从 CSV 生成投稿级森林图")
    ap.add_argument("-i", "--input", required=True, help="输入 CSV")
    ap.add_argument("-o", "--output", required=True, help="输出文件名前缀，如 out/fig2-forest")
    ap.add_argument("--measure", default="Effect estimate", help="效应量名称，如 'Hazard ratio'")
    ap.add_argument("--xlabel", help="x 轴标签，默认与 --measure 相同")
    ap.add_argument("--title")
    ap.add_argument("--scale", choices=["log", "linear"], default=None, help="默认按数值自动判断")
    ap.add_argument("--log", action="store_true",
                    help="对数轴（比值类效应量：HR / OR / RR）")
    ap.add_argument("--linear", action="store_true",
                    help="线性轴（差值类效应量：MD / SMD / WMD）")
    ap.add_argument("--null-value", type=float, help="无效线位置；比值类默认 1，差值类默认 0")
    ap.add_argument("--favours", help="两侧标注，如 'Metformin|Control'")
    ap.add_argument("--pooled-label", default="Pooled", help="汇总行标签")
    ap.add_argument("--xticks", help="自定义刻度，逗号分隔，如 '0.5,0.75,1,1.5'")
    ap.add_argument("--journal", default="generic", help="期刊预设，见 _style.JOURNAL_SIZES")
    ap.add_argument("--span", default="single", help="single | onehalf | double")
    ap.add_argument("--width-override", type=float, help="直接指定图宽（英寸）")
    ap.add_argument("--height-override", type=float, help="直接指定图高（英寸）")
    ap.add_argument("--font-size", type=float, default=7.0)
    ap.add_argument("--decimals", type=int, default=2)
    ap.add_argument("--no-text-column", action="store_true", help="不画右侧数值列")
    ap.add_argument("--allow-inconsistent", action="store_true",
                    help="数值不一致时仍出图（降级为警告）。默认拒绝出图")
    ap.add_argument("--formats", default="pdf,png", help="导出格式，逗号分隔")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--summary", help="把结果摘要写成 JSON")
    args = ap.parse_args()

    if args.log and args.linear:
        ap.error("--log 与 --linear 不能同时使用")
    if args.log:
        args.scale = "log"
    elif args.linear:
        args.scale = "linear"

    rows, unknown = load(args.input)
    if not rows:
        print(f"[forest] 输入为空：{args.input}", file=sys.stderr)
        return 2

    errs, warns = check_numbers(rows, strict=not args.allow_inconsistent)
    for w in warns:
        print(f"[forest] 警告: {w}", file=sys.stderr)
    if errs:
        print(f"[forest] 拒绝出图，共 {len(errs)} 处数值问题：", file=sys.stderr)
        for e in errs:
            print(f"  · {e}", file=sys.stderr)
        print("[forest] 修正 CSV，或加 --allow-inconsistent 先出一版看效果。", file=sys.stderr)
        return 1
    if unknown:
        print(f"[forest] 忽略无法识别的列: {', '.join(sorted(unknown))}", file=sys.stderr)

    studies = [r for r in rows if r["kind"] != "pooled"]
    for r in studies:
        r["log_se"] = None
    pooled = [r for r in rows if r["kind"] == "pooled"]

    log_vals = [v for r in rows for v in (r["lo"], r["hi"]) if v]
    if args.scale is None:
        use_log = all(v > 0 for v in log_vals) and (
            args.null_value == 1.0 or max(log_vals) / max(min(log_vals), 1e-9) > 2.5)
    else:
        use_log = args.scale == "log"
    args.scale = "log" if use_log else "linear"
    if args.null_value is None:
        args.null_value = 1.0 if args.scale == "log" else 0.0
    if args.scale == "log" and any(v <= 0 for v in log_vals):
        print("[forest] 对数轴要求所有 CI 端点 > 0；改用 --scale linear", file=sys.stderr)
        return 1

    fig = plot(rows, args)
    written = save(fig, args.output, formats=args.formats.split(","), dpi=args.dpi)
    import matplotlib.pyplot as plt
    plt.close(fig)

    summary = {
        "input": str(args.input),
        "n_studies": len(studies),
        "n_pooled_rows": len(pooled),
        "scale": args.scale,
        "null_value": args.null_value,
        "subgroups": sorted({r["subgroup"] for r in rows if r["subgroup"]}),
        "outputs": written,
        "warnings": warns,
    }
    if args.summary:
        Path(args.summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[forest] {len(studies)} 项研究 / {len(pooled)} 个汇总 / {args.scale} 轴")
    for p in written:
        print(f"[forest] 写出 {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
