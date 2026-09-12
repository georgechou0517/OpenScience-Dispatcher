#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""PRISMA 2020 流程图生成器：把各阶段计数渲染成规范的 flow diagram。

遵循 PRISMA 2020 的三栏结构：左侧阶段带（Identification / Screening /
Included）、中间主流程、右侧排除项。数字由调用方给出，本脚本只负责排版，
不做任何推断——推断错了比画错更危险。

用法：
  python prisma_flow.py --identified 2148 --duplicates 586 \\
      --excluded-abstract 1424 --assessed 138 --excluded-fulltext 114 \\
      --reason "Wrong population=52" --reason "No cardiovascular outcome=38" \\
      --reason "Duplicate cohort=24" --included 24 --in-meta 18 \\
      -o out/fig1-prisma --databases "PubMed, Embase, CENTRAL"

一致性校验：默认在计数自相矛盾时**拒绝出图**（如 included 大于
assessed - excluded-fulltext）。加 --allow-inconsistent 可强制出图。
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import C, apply_paper_style, save  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

X_PHASE = (0.05, 0.78)
X_MAIN = (1.05, 6.05)
X_RIGHT = (6.45, 9.95)
XMAX = 10.0
LINE_H = 0.34          # 每行文字占用的画布高度（x 单位）


def _wrap(text, width):
    """按字符数折行，保留原有的显式换行。"""
    out = []
    for line in str(text).split("\n"):
        if not line.strip():
            out.append("")
            continue
        out.extend(textwrap.wrap(line, width=max(12, int(width)), break_long_words=False)
                   or [line])
    return "\n".join(out)


def parse_reasons(items):
    out = []
    for it in items or []:
        if "=" in it:
            txt, n = it.rsplit("=", 1)
            try:
                out.append((txt.strip(), int(float(n.strip()))))
                continue
            except ValueError:
                pass
        out.append((it.strip(), None))
    return out


def validate(a):
    errs = []
    if a.duplicates > a.identified:
        errs.append(f"duplicates({a.duplicates}) > identified({a.identified})")
    if a.screened > a.identified - a.duplicates:
        errs.append(f"screened({a.screened}) > identified - duplicates({a.identified - a.duplicates})")
    if a.excluded_abstract > a.screened:
        errs.append(f"excluded_abstract({a.excluded_abstract}) > screened({a.screened})")
    if a.sought > a.screened - a.excluded_abstract:
        errs.append(f"sought({a.sought}) > screened - excluded({a.screened - a.excluded_abstract})")
    if a.not_retrieved > a.sought:
        errs.append(f"not_retrieved({a.not_retrieved}) > sought({a.sought})")
    if a.assessed > a.sought - a.not_retrieved:
        errs.append(f"assessed({a.assessed}) > sought - not_retrieved({a.sought - a.not_retrieved})")
    if a.excluded_fulltext > a.assessed:
        errs.append(f"excluded_fulltext({a.excluded_fulltext}) > assessed({a.assessed})")
    if a.included > a.assessed - a.excluded_fulltext:
        errs.append(
            f"included({a.included}) > assessed - excluded_fulltext"
            f"({a.assessed - a.excluded_fulltext})")
    if a.in_meta is not None and a.in_meta > a.included:
        errs.append(f"in_meta({a.in_meta}) > included({a.included})")
    known = sum(n for _, n in a.reasons if n is not None)
    if a.reasons and known and known != a.excluded_fulltext:
        errs.append(
            f"排除理由之和({known}) ≠ excluded_fulltext({a.excluded_fulltext})")
    return errs


def advisory(a):
    """非致命的一致性问题：值得提醒，但不足以拒绝出图。

    PRISMA 2020 允许「报告数 ≠ 研究数」（一份报告含多项研究，或多份报告对应
    同一项研究），所以 assessed ≠ included + excluded 本身不一定是错误；但如果
    没打算这样，就是漏了排除数，必须让用户看见。
    """
    notes = []
    accounted = a.included + a.excluded_fulltext
    if accounted != a.assessed:
        notes.append(
            f"included({a.included}) + 全文排除({a.excluded_fulltext}) = {accounted}"
            f"，而全文评估数为 {a.assessed}，相差 {a.assessed - accounted}。"
            f"若一份报告对应多项研究（或反之）属正常；否则请核对全文排除数")
    if a.excluded_abstract == 0 and a.screened > a.sought:
        notes.append(f"标题摘要筛排除数为 0，但 screened({a.screened}) > sought({a.sought})")
    return notes


def rows_for(a):
    """构造各行：主流程高度 + 右侧排除框高度。"""
    removed = [f"Duplicate records (n = {a.duplicates})"]
    if a.removed_automation:
        removed.append(f"Records marked ineligible by automation (n = {a.removed_automation})")
    if a.removed_other:
        removed.append(f"Records removed for other reasons (n = {a.removed_other})")
    right1 = "Records removed before screening:\n" + "\n".join(removed)

    reason_lines = []
    for txt, n in a.reasons:
        reason_lines.append(f"{txt} (n = {n})" if n is not None else txt)
    if not reason_lines:
        reason_lines = ["Reports excluded"]
    right4 = "Reports excluded:\n" + "\n".join(reason_lines)

    rows = [
        dict(main=f"Records identified from:\n{a.databases}\n(n = {a.identified})",
             right=right1, h_main=1.30, gap=0.40, phase="Identification"),
        dict(main=f"Records screened\n(n = {a.screened})",
             right=f"Records excluded\n(n = {a.excluded_abstract})",
             h_main=0.85, gap=0.35, phase="Screening"),
        dict(main=f"Reports sought for retrieval\n(n = {a.sought})",
             right=f"Reports not retrieved\n(n = {a.not_retrieved})",
             h_main=0.85, gap=0.35, phase="Screening"),
        dict(main=f"Reports assessed for eligibility\n(n = {a.assessed})",
             right=right4, h_main=0.85, gap=0.45, phase="Included"),
        dict(main=f"Studies included in review\n(n = {a.included})",
             right=None, h_main=0.95, gap=0.30, phase="Included"),
    ]
    if a.in_meta is not None:
        rows.append(dict(
            main="Studies included in quantitative synthesis\n(meta-analysis)\n"
                 f"(n = {a.in_meta})",
            right=None, h_main=1.15, gap=0.0, phase="Included"))

    # 先折行，再按实际行数定高——否则长句子会顶出边框。
    for r in rows:
        r["main"] = _wrap(r["main"], a.wrap_main)
        if r["right"]:
            r["right"] = _wrap(r["right"], a.wrap_right)
        r["h_main"] = max(r["h_main"], LINE_H * (r["main"].count("\n") + 1) + 0.30)
        r["h_right"] = (max(r["h_main"], LINE_H * (r["right"].count("\n") + 1) + 0.30)
                        if r["right"] else 0.0)
    return rows


def draw(ax, rows, a):
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    def box(x0, x1, y_top, h, text, fc, ec, fs):
        ax.add_patch(FancyBboxPatch((x0, y_top - h), x1 - x0, h,
                                    boxstyle="round,pad=0.06,rounding_size=0.10",
                                    facecolor=fc, edgecolor=ec, lw=0.85))
        ax.text((x0 + x1) / 2.0, y_top - h / 2.0, text, ha="center", va="center",
                fontsize=fs, linespacing=1.35)

    def arrow(x0, y0, x1, y1, color):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                     mutation_scale=8, color=color, lw=0.85,
                                     shrinkA=0, shrinkB=0))

    y = 0.0
    slots = []
    for r in rows:
        h = max(r["h_main"], r["h_right"])
        slots.append((y, y - h, r))
        y -= h + r["gap"]
    total_h = -y + 0.35

    # 阶段带
    phase_span = {}
    for top, _bot, r in slots:
        phase_span.setdefault(r["phase"], [top, _bot])
        phase_span[r["phase"]][1] = _bot
    for name, (top, bot) in phase_span.items():
        mid = (top + bot) / 2.0
        ax.plot([(X_PHASE[0] + X_PHASE[1]) / 2.0] * 2, [bot, top],
                color=C["grid"], lw=3.2, solid_capstyle="butt", zorder=1)
        ax.text((X_PHASE[0] + X_PHASE[1]) / 2.0, mid, name, rotation=90,
                ha="center", va="center", fontsize=7.0, color=C["intervention"])

    fs = a.font_size
    for top, bot, r in slots:
        box(X_MAIN[0], X_MAIN[1], top, r["h_main"], r["main"], C["box"], C["intervention"], fs)
        if r["right"]:
            box(X_RIGHT[0], X_RIGHT[1], top, r["h_right"], r["right"],
                "#FBEEEA", C["control"], fs - 0.2)
            arrow(X_MAIN[1] + 0.02, top - r["h_main"] / 2.0, X_RIGHT[0] - 0.02,
                  top - r["h_main"] / 2.0, C["control"])

    # 主链向下箭头
    for i in range(len(slots) - 1):
        if rows[i]["gap"] <= 0:
            continue
        y0 = slots[i][1]
        y1 = slots[i + 1][0]
        arrow((X_MAIN[0] + X_MAIN[1]) / 2.0, y0, (X_MAIN[0] + X_MAIN[1]) / 2.0, y1, C["line"])

    ax.set_xlim(0, XMAX)
    ax.set_ylim(-total_h, 0.30)
    ax.set_aspect("equal")
    ax.axis("off")
    if a.title:
        ax.set_title(a.title, fontsize=fs + 2, loc="left", pad=2)
    return rows


def main():
    ap = argparse.ArgumentParser(description="生成 PRISMA 2020 流程图")
    ap.add_argument("--identified", type=int, required=True, help="检索命中的记录总数")
    ap.add_argument("--duplicates", type=int, default=0, help="去重删除数")
    ap.add_argument("--screened", type=int, help="进入标题摘要筛的记录数，默认 identified - duplicates")
    ap.add_argument("--excluded-abstract", type=int, default=0, help="标题摘要筛排除数")
    ap.add_argument("--sought", type=int, help="全文索取数，默认 screened - excluded-abstract")
    ap.add_argument("--not-retrieved", type=int, default=0, help="未获取到全文数")
    ap.add_argument("--assessed", type=int, help="全文评估数，默认 sought - not-retrieved")
    ap.add_argument("--excluded-fulltext", type=int, default=0, help="全文排除数")
    ap.add_argument("--reason", action="append", default=[],
                    help="全文排除理由，格式 \"理由=n\"，可重复")
    ap.add_argument("--included", type=int, required=True, help="最终纳入研究数")
    ap.add_argument("--in-meta", type=int, help="进入定量合并（Meta 分析）的研究数")
    ap.add_argument("--databases", default="PubMed, Embase, CENTRAL", help="检索来源")
    ap.add_argument("--removed-automation", type=int, default=0)
    ap.add_argument("--removed-other", type=int, default=0)
    ap.add_argument("--title", default="PRISMA 2020 flow diagram")
    ap.add_argument("-o", "--output", required=True, help="输出文件名前缀")
    ap.add_argument("--journal", default="generic")
    ap.add_argument("--span", default="single")
    ap.add_argument("--font-size", type=float, default=7.2)
    ap.add_argument("--wrap-main", type=int, default=42, help="中间框每行最大字符数")
    ap.add_argument("--wrap-right", type=int, default=30, help="右侧排除框每行最大字符数")
    ap.add_argument("--formats", default="pdf,png")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--allow-inconsistent", action="store_true",
                    help="计数自相矛盾时仍出图（默认拒绝）")
    ap.add_argument("--width-override", type=float, help="直接指定图宽（英寸）")
    ap.add_argument("--summary", help="把结果摘要写成 JSON")
    a = ap.parse_args()

    if a.screened is None:
        a.screened = a.identified - a.duplicates
    if a.sought is None:
        a.sought = a.screened - a.excluded_abstract
    if a.assessed is None:
        a.assessed = a.sought - a.not_retrieved
    a.reasons = parse_reasons(a.reason)

    errs = validate(a)
    if errs:
        for e in errs:
            print(f"[prisma] 计数矛盾: {e}", file=sys.stderr)
        if not a.allow_inconsistent:
            print("[prisma] 拒绝出图。修正计数，或加 --allow-inconsistent 先出一版。", file=sys.stderr)
            return 1
        print("[prisma] --allow-inconsistent 已启用，继续出图。", file=sys.stderr)

    notes = advisory(a)
    for n in notes:
        print(f"[prisma] 提醒: {n}", file=sys.stderr)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_paper_style(font_size=a.font_size)
    rows = rows_for(a)
    total_h = sum(max(r["h_main"], r["h_right"]) + r["gap"] for r in rows) + 0.65
    from _style import figure_width
    width = a.width_override or max(figure_width(a.journal, a.span), 6.2)
    fig, ax = plt.subplots(figsize=(width, width * total_h / XMAX))
    draw(ax, rows, a)
    written = save(fig, a.output, formats=a.formats.split(","), dpi=a.dpi)
    plt.close(fig)

    summary = {
        "identified": a.identified, "duplicates": a.duplicates, "screened": a.screened,
        "excluded_abstract": a.excluded_abstract, "sought": a.sought,
        "not_retrieved": a.not_retrieved, "assessed": a.assessed,
        "excluded_fulltext": a.excluded_fulltext,
        "reasons": [{"reason": t, "n": n} for t, n in a.reasons],
        "included": a.included, "in_meta": a.in_meta,
        "inconsistencies": errs,
        "advisories": notes,
        "outputs": written,
    }
    if a.summary:
        Path(a.summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[prisma] {a.identified} → 去重 {a.screened} → 全文 {a.assessed} → 纳入 {a.included}"
          + (f" → 合并 {a.in_meta}" if a.in_meta is not None else ""))
    for p in written:
        print(f"[prisma] 写出 {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
