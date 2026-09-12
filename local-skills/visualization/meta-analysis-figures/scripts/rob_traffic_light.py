#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""偏倚风险红绿灯图（risk-of-bias traffic light）：Cochrane RoB 2 / ROBINS-I 通用。

CSV 列：第一列是研究标签，其余每列是一个评价域。列的**顺序**就是图的顺序。
默认域名为 RoB 2 的五个域，可用 --domain-labels 覆盖。

取值（大小写不敏感）：
  低风险  low | l | + | low risk | 低 | 低风险
  有些担忧 some | some concerns | concerns | unclear | ? | 中 | 有一些担忧
  高风险  high | h | - | high risk | 高 | 高风险
  未报告  na | n/a | ni | no information | x | 未报告 | 不清楚

用法：
  python rob_traffic_light.py -i rob.csv -o out/fig4-rob \\
      --domain-labels "Randomisation;Deviations;Missing data;Outcome measurement;Selective reporting"

  # ROBINS-I 七个域
  python rob_traffic_light.py -i rob.csv -o out/fig4-rob --tool robins-i
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

LEVELS = ["low", "some", "high", "na"]
LEVEL_COLOR = {"low": C["low"], "some": C["some"], "high": C["high"], "na": C["na"]}
LEVEL_LABEL = {"low": "Low risk", "some": "Some concerns", "high": "High risk", "na": "No information"}

VALUE_MAP = {
    "low": "low", "l": "low", "+": "low", "low risk": "low", "lowrisk": "low",
    "低": "low", "低风险": "low", "green": "low",
    "some": "some", "some concerns": "some", "concerns": "some", "unclear": "some",
    "?": "some", "中": "some", "有一些担忧": "some", "中等": "some", "medium": "some",
    "someconcerns": "some", "moderate": "some",
    "high": "high", "h": "high", "-": "high", "high risk": "high", "highrisk": "high",
    "高": "high", "高风险": "high", "red": "high",
    "na": "na", "n/a": "na", "ni": "na", "no information": "na", "x": "na",
    "未报告": "na", "不清楚": "na", "critical": "high", "serious": "high",
}

TOOL_DOMAINS = {
    "rob2": ["Randomisation process", "Deviations from intended interventions",
             "Missing outcome data", "Measurement of the outcome",
             "Selection of the reported result"],
    "robins-i": ["Confounding", "Selection of participants",
                 "Classification of interventions", "Deviations from intended interventions",
                 "Missing data", "Measurement of outcomes",
                 "Selection of the reported result"],
}


def norm(v):
    key = re.sub(r"\s+", " ", (v or "").strip().lower())
    if key in VALUE_MAP:
        return VALUE_MAP[key]
    key2 = key.replace("_", " ").replace("-", " ")
    if key2 in VALUE_MAP:
        return VALUE_MAP[key2]
    return None


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            return [], [], []
    header = [h.strip() for h in header]
    domains = header[1:] or [f"D{i}" for i in range(1, len(header))]
    studies, bad = [], []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            vals = [(raw.get(h) or "") for h in header]
            name = (vals[0] or "").strip() or f"Study {len(studies) + 1}"
            marks = []
            for dom, v in zip(domains, vals[1:]):
                lv = norm(v)
                if lv is None:
                    bad.append((name, dom, v))
                    lv = "na"
                marks.append(lv)
            studies.append({"study": name, "marks": marks})
    return studies, domains, bad


def plot(studies, labels, args):
    import textwrap

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    apply_paper_style(font_size=args.font_size)

    # 域标签折行后置于网格**上方**——旋转 40° 放在底部会和数据方块打架。
    wrapped = [textwrap.wrap(l, args.wrap_domain) or [l] for l in labels]
    max_lines = max(len(w) for w in wrapped)
    max_chars = max((len(x) for w in wrapped for x in w), default=10)

    # 让图宽自适应最长标签，否则相邻域标签会横向叠在一起。
    n_dom = len(labels)
    left_frac = 0.24
    need_axes = n_dom * (0.047 * max_chars + 0.12)
    width = (args.width_override
             or max(figure_width(args.journal, args.span), need_axes / (1.0 - left_frac), 4.6))
    height = args.height_override or max(1.7, 0.21 * len(studies) + 1.20)
    fig, ax = plt.subplots(figsize=(width, height))

    top_in = 0.12 + 0.105 * max_lines
    top_frac = max(0.45, 1.0 - top_in / height)

    for yi, st in enumerate(studies):
        for xi, lv in enumerate(st["marks"]):
            ax.scatter([xi], [yi], s=args.marker_size, marker="s",
                       facecolor=LEVEL_COLOR[lv], edgecolor="#7F7F7F", linewidth=0.4, zorder=3)
    ax.set_xlim(-0.6, n_dom - 0.4)
    ax.set_ylim(len(studies) - 0.5, -0.5)

    ax.set_xticks(range(n_dom))
    ax.set_xticklabels(["\n".join(w) for w in wrapped], fontsize=args.font_size - 1.0,
                       linespacing=1.25)
    ax.xaxis.set_ticks_position("top")
    ax.tick_params(axis="x", length=0, pad=4)
    ax.set_yticks(range(len(studies)))
    ax.set_yticklabels([s["study"] for s in studies], fontsize=args.font_size)
    ax.tick_params(axis="y", length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    if args.title:
        fig.suptitle(args.title, fontsize=args.font_size + 2, x=0.02, ha="left", y=0.985)

    handles = [Line2D([], [], marker="s", linestyle="none", markersize=5.5,
                      markerfacecolor=LEVEL_COLOR[lv], markeredgecolor="#7F7F7F",
                      label=LEVEL_LABEL[lv]) for lv in LEVELS]
    fig.legend(handles=handles, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 0.005),
               fontsize=args.font_size - 1.0, handletextpad=0.4, columnspacing=1.2)
    fig.subplots_adjust(left=left_frac, right=0.99, top=top_frac, bottom=0.11)
    return fig


def main():
    ap = argparse.ArgumentParser(description="生成偏倚风险红绿灯图")
    ap.add_argument("-i", "--input", required=True, help="输入 CSV：研究 + 若干评价域列")
    ap.add_argument("-o", "--output", required=True, help="输出文件名前缀")
    ap.add_argument("--tool", choices=sorted(TOOL_DOMAINS), help="按工具给出默认域名")
    ap.add_argument("--domain-labels", help="分号分隔的域名，覆盖 CSV 表头")
    ap.add_argument("--title", default="Risk of bias summary")
    ap.add_argument("--journal", default="generic")
    ap.add_argument("--span", default="onehalf")
    ap.add_argument("--font-size", type=float, default=7.0)
    ap.add_argument("--wrap-domain", type=int, default=20, help="域标签每行最大字符数")
    ap.add_argument("--marker-size", type=float, default=58.0, help="方块大小（points²）")
    ap.add_argument("--width-override", type=float)
    ap.add_argument("--height-override", type=float)
    ap.add_argument("--formats", default="pdf,png")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--summary", help="把结果摘要写成 JSON")
    args = ap.parse_args()

    studies, domains, bad = load(args.input)
    if not studies:
        print(f"[rob] 没有读到任何研究行：{args.input}", file=sys.stderr)
        return 2
    for name, dom, v in bad[:10]:
        print(f"[rob] 警告: {name} / {dom} 的取值 '{v}' 无法识别，已记为 No information", file=sys.stderr)
    if len(bad) > 10:
        print(f"[rob] 另有 {len(bad) - 10} 处同类警告", file=sys.stderr)

    if args.domain_labels:
        labels = [x.strip() for x in args.domain_labels.split(";") if x.strip()]
    elif args.tool:
        labels = TOOL_DOMAINS[args.tool]
    else:
        labels = domains
    if len(labels) != len(domains):
        print(f"[rob] 域名数({len(labels)}) 与 CSV 列数({len(domains)}) 不一致，改用表头", file=sys.stderr)
        labels = domains

    fig = plot(studies, labels, args)
    written = save(fig, args.output, formats=args.formats.split(","), dpi=args.dpi)
    import matplotlib.pyplot as plt
    plt.close(fig)

    tally = {lv: 0 for lv in LEVELS}
    per_domain = []
    for xi, dom in enumerate(labels):
        c = {lv: 0 for lv in LEVELS}
        for st in studies:
            c[st["marks"][xi]] += 1
            tally[st["marks"][xi]] += 1
        per_domain.append({"domain": dom, **c})

    print(f"[rob] {len(studies)} 项研究 × {len(labels)} 个域")
    for row in per_domain:
        print(f"  {row['domain']:<42} low={row['low']:<3} some={row['some']:<3} "
              f"high={row['high']:<3} na={row['na']}")
    print(f"  合计: low={tally['low']} some={tally['some']} high={tally['high']} na={tally['na']}")
    for p in written:
        print(f"[rob] 写出 {p}")

    if args.summary:
        Path(args.summary).write_text(json.dumps(
            {"studies": len(studies), "domains": labels, "per_domain": per_domain,
             "tally": tally, "unrecognised_values": len(bad), "outputs": written},
            ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
