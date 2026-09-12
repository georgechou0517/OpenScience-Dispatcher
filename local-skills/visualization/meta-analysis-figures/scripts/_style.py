# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""meta-analysis-figures 共享样式层。

只依赖 matplotlib 与 numpy。这里刻意不 import 上游
`scientific-visualization/scripts/style_presets.py`：技能被安装到不同的
`<category>/<name>/` 目录后，跨技能相对路径并不可靠，一旦解析失败整张图就出不来。
需要更完整的期刊样式时，先调用本模块的 `apply_paper_style()`，再叠加上游样式即可。
"""
from __future__ import annotations

MM_PER_INCH = 25.4

# 色盲友好配色，与上游 scientific-visualization 同源（Okabe-Ito / Paul Tol）
OKABE_ITO = ["#E69F00", "#56B4E9", "#009E73", "#F0E442",
             "#0072B2", "#D55E00", "#CC79A7", "#000000"]
TOL_BRIGHT = ["#4477AA", "#EE6677", "#228833", "#CCBB44",
              "#66CCEE", "#AA3377", "#BBBBBB"]

# 效应方向用色。注意：这里表达的是「利于干预组 / 利于对照组」，
# 与股票涨跌的红绿约定无关，不要套用。
C = {
    "intervention": "#0072B2",
    "control": "#D55E00",
    "neutral": "#4D4D4D",
    "line": "#333333",
    "grid": "#D9D9D9",
    "pooled": "#B2182B",
    "low": "#1B7837",
    "some": "#F0E442",
    "high": "#C0392B",
    "na": "#BFBFBF",
    "box": "#EFF3F8",
}

# 栏宽近似值（mm）。数值按各刊 Author Guidelines 整理；投稿前必须以
# 目标期刊**最新**的作者指南为准，这里只用于先把图做到合理比例。
JOURNAL_SIZES = {
    "nature":  {"single": 89, "onehalf": 120, "double": 183},
    "science": {"single": 55, "onehalf": 120, "double": 175},
    "cell":    {"single": 85, "onehalf": 114, "double": 178},
    "plos":    {"single": 83, "onehalf": 114, "double": 173},
    "lancet":  {"single": 80, "onehalf": 105, "double": 165},
    "nejm":    {"single": 82, "onehalf": 121, "double": 173},
    "jama":    {"single": 82, "onehalf": 121, "double": 173},
    "generic": {"single": 85, "onehalf": 120, "double": 170},
}

_SPAN_ALIASES = {
    "single": "single", "1col": "single", "1": "single",
    "onehalf": "onehalf", "1.5": "onehalf", "1.5col": "onehalf", "half": "onehalf",
    "double": "double", "2col": "double", "2": "double", "full": "double",
}


def figure_width(journal="generic", span="single"):
    """按期刊与栏数返回**英寸**宽度。"""
    key = _SPAN_ALIASES.get(str(span).strip().lower(), "single")
    sizes = JOURNAL_SIZES.get(str(journal).strip().lower(), JOURNAL_SIZES["generic"])
    return sizes.get(key, sizes["single"]) / MM_PER_INCH


def apply_paper_style(font_size=7.0, font_family="sans-serif", dpi=300):
    """设定出版级 rcParams。字号默认 7pt，接近多数期刊正文图件的最终字号。"""
    import matplotlib as mpl

    mpl.rcParams.update({
        "figure.dpi": 120,
        "savefig.dpi": dpi,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.family": font_family,
        # 逐个回退，避免缺字体时刷屏警告
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": font_size,
        "axes.titlesize": font_size + 1.0,
        "axes.labelsize": font_size,
        "xtick.labelsize": font_size - 0.5,
        "ytick.labelsize": font_size - 0.5,
        "legend.fontsize": font_size - 0.5,
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.4,
        "ytick.major.size": 2.4,
        "lines.linewidth": 0.9,
        "lines.markersize": 3.5,
        "legend.frameon": False,
        # 42 = TrueType；期刊排版常见「字体未嵌入」退稿原因
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    })


def save(fig, stem, formats=("pdf", "png"), dpi=300):
    """按多种格式导出，返回写出的文件路径列表。"""
    written = []
    for fmt in formats:
        f = str(fmt).strip().lstrip(".").lower()
        if not f:
            continue
        path = f"{stem}.{f}"
        fig.savefig(path, dpi=dpi, facecolor="white")
        written.append(path)
    return written


def check_numbers(rows, label="行", strict=True):
    """森林图/漏斗图的通用数值体检。

    返回 (errors, warnings)。`strict=False` 时把错误降级为警告（用于
    --allow-inconsistent，让用户明知有问题也先出图看一眼）。
    """
    errors, warnings = [], []
    for i, r in enumerate(rows, 1):
        est, lo, hi = r.get("est"), r.get("lo"), r.get("hi")
        if est is None or lo is None or hi is None:
            errors.append(f"{label} {i}（{r.get('study', '?')}）：est/lo/hi 有空值")
            continue
        if lo > hi:
            errors.append(f"{label} {i}（{r.get('study', '?')}）：下限 {lo} 大于上限 {hi}，疑似列填反")
        elif not (lo <= est <= hi):
            errors.append(f"{label} {i}（{r.get('study', '?')}）：点估计 {est} 不在 [{lo}, {hi}] 内")
        if lo <= 0:
            errors.append(f"{label} {i}（{r.get('study', '?')}）：下限 {lo} ≤ 0，对数轴无法绘制")
        if hi <= 0:
            errors.append(f"{label} {i}（{r.get('study', '?')}）：上限 {hi} ≤ 0，对数轴无法绘制")
        w = r.get("weight")
        if w is not None and w <= 0:
            warnings.append(f"{label} {i}（{r.get('study', '?')}）：权重 {w} ≤ 0，已按等权处理")
    if not strict:
        warnings.extend(errors)
        errors = []
    return errors, warnings
