---
name: meta-analysis-figures
description: 系统综述与 Meta 分析的投稿级图件生成器。用可复现脚本从 CSV / 计数直接产出森林图（forest plot，含亚组与汇总菱形、对数与线性轴、权重方块）、漏斗图（funnel plot，含固定效应合并线与 Egger 检验）、PRISMA 2020 流程图（三栏规范布局）与偏倚风险红绿灯图（Cochrane RoB 2 / ROBINS-I）。内置数值一致性校验：置信区间填反、点估计越界、计数自相矛盾时默认拒绝出图。当需要画森林图、漏斗图、PRISMA 流程图、偏倚风险图，或整理系统综述 / Meta 分析的图表时启用。
category: visualization
license: Apache-2.0
version: 1.0.0
author: GeorgeChou17
tags: [forest plot, funnel plot, PRISMA, risk of bias, meta-analysis, systematic review, publication figure, heterogeneity, publication bias, subgroup analysis, effect size, confidence interval, 森林图, 漏斗图, 偏倚风险, 红绿灯图, 异质性, 发表偏倚, 亚组分析, 效应量, 置信区间, 荟萃分析, 系统综述]
dependencies: ["matplotlib>=3.5", "numpy>=1.20"]
---

# Meta-Analysis Figures

## Overview

系统综述与 Meta 分析有**四张图是硬性要求或事实标准**，而通用绘图技能只提供底层
matplotlib 能力，不提供这些图的成品实现。本技能补上这一段：吃 CSV 或计数，吐投稿级图件。

| 脚本 | 产出 | 在论文中的位置 |
|---|---|---|
| `scripts/forest_plot.py` | 森林图 | 结果部分主图 |
| `scripts/funnel_plot.py` | 漏斗图 + Egger 检验 | 发表偏倚 |
| `scripts/prisma_flow.py` | PRISMA 2020 流程图 | 方法部分（多数期刊强制） |
| `scripts/rob_traffic_light.py` | 偏倚风险红绿灯图 | 质量评价 / 附录 |

## When to Use This Skill

- 手上有合并结果（效应量 + 95%CI），要画森林图，可能还要亚组分层。
- 要做发表偏倚评估，需要漏斗图与 Egger 检验。
- 要按 PRISMA 2020 交流程图，且各阶段计数已经数清楚。
- 做了 Cochrane RoB 2 或 ROBINS-I 评价，要把逐研究逐域的判定可视化。
- 在 `sci-paper` 工作流的 Stage 6（图表制作）阶段——这一阶段默认调用本技能。

## Quick Start Guide

先在 `scripts/` 目录下运行（或给脚本绝对路径）：

```bash
# 1) 森林图：对数轴 + 亚组 + 右侧数值列
python scripts/forest_plot.py -i studies.csv -o out/fig2-forest \
    --measure "Hazard ratio" --log --favours "Metformin|Control" \
    --journal nature --span double

# 2) 漏斗图 + Egger 检验
python scripts/funnel_plot.py -i studies.csv -o out/fig3-funnel --measure "log hazard ratio"

# 3) PRISMA 2020 流程图（计数自相矛盾时会拒绝出图）
python scripts/prisma_flow.py --identified 2148 --duplicates 586 \
    --excluded-abstract 1424 --assessed 138 --excluded-fulltext 114 \
    --reason "Wrong population=52" --reason "No cardiovascular outcome=38" \
    --reason "Duplicate cohort=24" --included 24 --in-meta 18 \
    -o out/fig1-prisma --databases "PubMed, Embase, CENTRAL"

# 4) 偏倚风险红绿灯（Cochrane RoB 2 五个域）
python scripts/rob_traffic_light.py -i rob.csv -o out/fig4-rob --tool rob2
```

`examples/` 下有可直接跑的示例数据：`demo_forest.csv`、`demo_funnel.csv`、`demo_rob.csv`。
先拿示例跑通，再换成自己的数据，能省掉大半排错时间。

## 输入格式

三个表格式脚本都用 stdlib `csv` 读，表头**大小写 / 空格 / 下划线不敏感**，并接受常用别名
（如 `est` / `estimate` / `hr` / `or` / `效应量` 都指同一列）。

**森林图**（`demo_forest.csv`）

| 列 | 必需 | 说明 |
|---|---|---|
| `study` | ✅ | 研究标签 |
| `est` `lo` `hi` | ✅ | 点估计与 95%CI 上下限 |
| `weight` | | 有则方块面积正比于权重，无则等大 |
| `subgroup` | | 相同标签的**连续**行视为一组，组间自动留空 |
| `kind` | | `study`（默认）或 `pooled`（渲染成菱形） |

> 汇总行要自己算好再放进 CSV——本技能**不替你算合并效应量**。算合并效应量用
> `statistical-analysis` 或直接写脚本，结果写进 `05-results.json`，再把数字填进 CSV。
> 这样稿子里的每个数字都能回溯，符合 `sci-paper` 的铁律 R2。

**漏斗图**：`study`（可选）、`est`、`se`。
**红绿灯图**：第一列研究名，其余每列一个评价域，列的**顺序就是图的顺序**。

## Core Principles

### 1. 程序化生成，不许手绘

图必须由数据文件经脚本产出。凡是要进稿的图，都要留下生成脚本与输入 CSV，
`dispatch.py workflow show sci-paper` 的 Stage 6 门控就是查这一条。

### 2. 数值自相矛盾时不出图

`forest_plot.py` 与 `prisma_flow.py` 默认做一致性校验，发现下面这些情况会**直接拒绝出图**
并以非 0 退出码返回：

- CI 下限大于上限（十有八九是列填反了）
- 点估计不在 `[lo, hi]` 区间内
- CI 端点 ≤ 0 却要求对数轴
- PRISMA 各阶段计数前后矛盾（如纳入数大于全文评估数）

确需先看一眼效果，加 `--allow-inconsistent`。**但不要用它把问题糊过去**：一张与数据
矛盾的森林图，比没有图更糟。

### 3. 小样本的发表偏倚检验要说实话

纳入研究 < 10 项时，漏斗图的不对称性检验功效不足，脚本会在图上打出
`k < 10: underpowered for asymmetry tests`。这句话必须保留，并在正文里如实说明。
Egger 检验只报告数字、不下结论；`p` 值依赖 scipy，没装 scipy 时只报告截距与 t 值。

### 4. 图件规范以目标期刊为准

`--journal` / `--span` 会把图宽设到该刊的栏宽近似值。这些数字按各刊 Author Guidelines
整理，投稿前**必须以目标期刊最新指南复核**。更完整的期刊尺寸、字号、配色规范见上游
`scientific-visualization` 技能（含 Nature / Science / Cell / PLOS / ACS 细则与色盲友好
调色板）。

## 与相邻技能的分工

| 需要什么 | 用哪个技能 |
|---|---|
| 森林图 / 漏斗图 / PRISMA / RoB 图 | **本技能** |
| 期刊尺寸字号配色、通用多面板排版、导出格式 | `scientific-visualization`（上游） |
| Kaplan-Meier 生存曲线与生存统计 | `clinical-decision-support`（上游，含 `generate_survival_analysis.py`） |
| 机制示意图、流程图（非 PRISMA） | `scientific-schematics`（上游） |
| 合并效应量怎么算、异质性怎么判 | `statistical-analysis`（上游） |

本技能自带 `scripts/_style.py`，只做最小样式设置（出版级 rcParams + Okabe-Ito 配色），
刻意**不**跨目录 import 上游样式脚本——技能装到不同 `<category>/<name>/` 后相对路径并不可靠，
一旦解析失败整张图就出不来。需要上游的完整样式时，先 `apply_paper_style()` 再叠加。

## Common Issues

| 现象 | 原因与处理 |
|---|---|
| `森林图` 报"下限大于上限" | CI 两列填反，或把 `se` 当成 `hi` 填了 |
| 右侧数值列被裁掉 | 用 `--width-override` 或 `--span double` 加宽；导出用 PDF |
| PRISMA 框里文字溢出 | 调小 `--wrap-main` / `--wrap-right`，或加大 `--width-override` |
| RoB 域标签互相压住 | 调小 `--wrap-domain`（默认 20），图宽会自动跟随最长标签 |
| 漏斗图提示 k < 10 | 不是错误，是功效不足的提醒；正文必须如实交代 |
| 中文字体缺失 | 脚本默认 Arial/Helvetica/DejaVu Sans；中文可自行 `font.sans-serif` 追加思源黑体 |

## 参考

- `references/meta-analysis-figure-guide.md`：PRISMA 2020 计数逻辑、森林图必备要素清单、
  漏斗图与 Egger 检验的解读边界、RoB 2 / ROBINS-I 各域含义。
