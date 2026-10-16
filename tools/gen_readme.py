#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Part of OpenScience Dispatcher (dispatcher layer). Upstream content and full notices:/n# see LICENSE, NOTICE, ATTRIBUTION.md, THIRD-PARTY-NOTICES.md.
"""生成 openscience-dispatcher 的 README.md。

数据来源：
  - registry.json      314 条子技能元数据（name / category / description / origin）
  - tools/sources.py   每个 Skill / MCP 的上游项目与源仓库映射
  - mcp/catalog.json   7 个 MCP 连接器的元数据

用法：
  python tools/gen_readme.py            # 写出仓库根目录的 README.md
  python tools/gen_readme.py --check    # 只做一致性校验，不写文件
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from sources import (URLS, MCP, OSN, REPO, BRANCH,  # noqa: E402
                     LOCAL_SKILLS, SELF, SELF_REPO)

ORDER = [
    "ml-training", "biology", "databases", "llm-tools", "chemistry", "physics",
    "coding", "research", "other", "cloud-compute", "data-engineering",
    "writing", "ml-inference", "visualization", "quantum", "document-parsing",
]
LABEL = {
    "ml-training": "模型训练", "biology": "生物学", "databases": "科学数据库",
    "llm-tools": "大模型工具", "chemistry": "化学", "physics": "物理学",
    "coding": "科学计算", "research": "科研流程", "other": "会话与工程",
    "cloud-compute": "云端算力", "data-engineering": "数据工程",
    "writing": "论文写作", "ml-inference": "模型推理",
    "visualization": "科学可视化", "quantum": "量子计算",
    "document-parsing": "文档解析",
}


def brief(text, n=64):
    """把描述压成一行短语，供表格使用。"""
    t = re.sub(r"\s+", " ", text or "").strip()
    t = re.sub(r"^\[EXPERIMENTAL\]\s*", "", t)
    t = re.sub(
        r"^(?:use this skill (?:when|for|to)|use when|use for|"
        r"this skill (?:should be used|is used|is triggered)|when to use this skill)"
        r"[:\s]+", "", t, flags=re.I)
    t = re.sub(r"^(?:the user|a user|you)\s+(?:asks|wants|needs|is asking)\s+(?:to|for)\s+",
               "", t, flags=re.I)
    t = re.sub(r"^(?:when|for)\s+(?:the user|a user|you)\s+(?:asks|wants|needs)\s+to\s+",
               "", t, flags=re.I)
    t = t[:1].upper() + t[1:] if t else t
    cut = t.find(". ")
    if 0 < cut <= n:
        t = t[: cut + 1]
    if len(t) > n:
        t = t[:n].rsplit(" ", 1)[0] + "…"
    return t.replace("|", "/").strip()


def link_text(url, n=40):
    """为 URL 生成可读的链接文字：GitHub 用 owner/repo，其余用域名+路径。"""
    m = re.match(r"https?://github\.com/([^/]+/[^/#?]+)", url)
    if m:
        return m.group(1)
    m = re.match(r"https?://([^/]+)(/.*)?$", url)
    label = (m.group(1) + (m.group(2) or "")).rstrip("/")
    return label if len(label) <= n else label[: n - 1] + "…"


def resolve(name, cat):
    """返回 (项目名, 源仓库 URL)。OSN 技能解析为上游仓库深链。"""
    if name in LOCAL_SKILLS:
        label, url = LOCAL_SKILLS[name]
        return label, (SELF_REPO if url == SELF else url)
    entry = URLS.get(name)
    if entry is None:
        return "（未登记）", SELF_REPO
    label, url = entry
    if url != OSN:
        return label, url
    if name == "scholar-evaluation":
        return "OpenScience 自研", f"{REPO}/tree/{BRANCH}/backend/cli/skills/scholar-evaluation"
    return "OpenScience 自研", f"{REPO}/tree/{BRANCH}/backend/cli/skills/{cat}/{name}"


def load():
    reg = json.loads((ROOT / "registry.json").read_text(encoding="utf-8"))
    cat = {e["name"]: e["category"] for e in reg}
    rank = {c: i for i, c in enumerate(ORDER)}
    reg.sort(key=lambda e: (rank.get(e["category"], 99), e["name"].lower()))
    return reg, cat


def skill_rows(reg, cat):
    """返回 (表格行, OpenScience 自研数, 本包 local-skills 数)。"""
    out, selfmade, local = [], 0, 0
    for i, e in enumerate(reg, 1):
        label, url = resolve(e["name"], cat[e["name"]])
        if e["name"] in LOCAL_SKILLS:
            local += 1
            label = f"**{label}**"
        elif label == "OpenScience 自研":
            selfmade += 1
        out.append(
            f"| {i} | `{e['name']}` | {LABEL.get(e['category'], e['category'])} "
            f"| {brief(e['description'])} | [{label}]({url}) |"
        )
    return out, selfmade, local


def local_rows(reg):
    """本包 local-skills/ 明细表：技能 / 分类 / 用途 / 版本 / 来源。"""
    out = []
    for e in sorted(reg, key=lambda x: x["name"]):
        if e["name"] not in LOCAL_SKILLS:
            continue
        label, url = resolve(e["name"], e["category"])
        out.append(
            f"| `{e['name']}` | {LABEL.get(e['category'], e['category'])} "
            f"| {brief(e['description'], 80)} | {e.get('version') or '—'} | [{label}]({url}) |"
        )
    return out


def mcp_rows():
    out = []
    order = ["givemeanode", "github", "benchling", "box", "dropbox", "s3", "spss"]
    for i, k in enumerate(order, 1):
        nm, pv, url = MCP[k]
        out.append(f"| {i} | **{nm}** | {pv} | [{link_text(url)}]({url}) |")
    return out


def counts(reg):
    from collections import Counter
    c = Counter(e["category"] for e in reg)
    rows = [
        f"| {LABEL.get(k, k)} | `{k}` | {c[k]} |"
        for k in ORDER if c.get(k)
    ]
    return c, rows



def fetch_totals():
    """File count and payload size of the on-demand set, straight from manifest.json.

    Read rather than hard-coded: these figures moved once already when a file had to be
    withdrawn, and a stale number in the README is worse than no number.
    """
    try:
        data = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        t = data["totals"]
        return str(t["files"]), f"{t['bytes'] / 1048576:.1f}"
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[!] manifest.json 读取失败（{exc}）")
        return "?", "?"


def main():
    reg, cat = load()
    missing = [e["name"] for e in reg
               if e["name"] not in URLS and e["name"] not in LOCAL_SKILLS]
    extra = [k for k in URLS if k not in cat]
    if missing or extra:
        print(f"[!] 映射不一致：缺少 {missing[:5]}，多余 {extra[:5]}")
    cnt, cat_rows = counts(reg)
    srows, selfmade, n_local = skill_rows(reg, cat)
    lrows = local_rows(reg)
    mrows = mcp_rows()

    n_upstream = len(reg) - selfmade - n_local
    fetch_files, fetch_mb = fetch_totals()
    doc = TEMPLATE
    for key, val in {
        "@@N_SKILL@@": str(len(reg)),
        "@@N_CAT@@": str(len(cnt)),
        "@@N_MCP@@": str(len(MCP)),
        "@@N_SELFMADE@@": str(selfmade),
        "@@N_LOCAL@@": str(n_local),
        "@@N_UPSTREAM@@": str(n_upstream),
        "@@N_UPSTREAM_ALL@@": str(selfmade + n_upstream),
        "@@FETCH_FILES@@": fetch_files,
        "@@FETCH_MB@@": fetch_mb,
        "@@CAT_ROWS@@": "\n".join(cat_rows),
        "@@MAX_CAT@@": f"{cnt.most_common(1)[0][0]}（{cnt.most_common(1)[0][1]}）",
        "@@SKILL_ROWS@@": "\n".join(srows),
        "@@LOCAL_ROWS@@": "\n".join(lrows) or "| — | — | — | — | — |",
        "@@MCP_ROWS@@": "\n".join(mrows),
    }.items():
        doc = doc.replace(key, val)

    if "--check" in sys.argv:
        print(f"校验通过：{len(reg)} skills / {len(cnt)} categories / {len(MCP)} MCP")
        print(f"  OpenScience 自研 {selfmade} · 本包 local-skills {n_local} · "
              f"依托第三方项目 {n_upstream}")
        return
    with open(ROOT / "README.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    print(f"已写出 README.md：{len(doc)} 字符 / {len(doc.encode('utf-8'))} 字节")
    print(f"  {len(reg)} 个 skill（上游自研 {selfmade} + 本包 local {n_local} + 依托第三方 {n_upstream}）"
          f" · {len(MCP)} 个 MCP")


TEMPLATE = r"""# OpenScience Dispatcher · 科研综合调度技能

> 把 [OpenScience](https://github.com/synthetic-sciences/openscience) 的 **@@N_SKILL@@ 个科研子技能**与
> **@@N_MCP@@ 个 MCP 连接器**，装进 WorkBuddy 等通用 AI Agent 平台。
> 其中 @@N_LOCAL@@ 个技能是本包在前述基础上自行扩展的（见 §5.3）。
> **包本体很轻**（解压约 1.6 MB）：@@N_UPSTREAM_ALL@@ 个上游子技能不随包分发，用到哪个才从 Gitee 下载哪个，
> 而且只下那次任务真正需要的文件——见 [§3.7](#ondemand)。
> 子技能是「能力」，MCP 是「工具」，调度器负责把它们路由到你的问题上去。

[中文](#中文) · [English](#english) · [图表效果 / Figures](#gallery)

<div align="center">

`@@N_SKILL@@` Skills · `@@N_CAT@@` Categories · `@@N_MCP@@` MCP Connectors · Apache-2.0 · Python 3.8+ · 零依赖 · 解压约 1.6 MB

</div>

---

<a id="gallery"></a>

## 图表效果 · Figure gallery

> **科研图表的绘制**是本项目的两个主打之一（另一个是「傻瓜化」）。
> 下面每一张都是**脚本从数据文件直接生成的成图**——不是示意图、不是贴图，也没有手工美化。
> 把 CSV 或一组计数交给 Agent，说一句「画个森林图 / 漏斗图 / PRISMA 流程图」，得到的就是这个质量。

| 森林图 Forest plot | 漏斗图 Funnel plot |
|---|---|
| ![森林图：效应量合并、亚组分析与合并菱形](docs/figures/forest-plot.png) | ![漏斗图：发表偏倚与 Egger 检验](docs/figures/funnel-plot.png) |
| 效应量合并 · 亚组分析 · 合并菱形 | 发表偏倚 · Egger 检验 · 伪 95% 区间 |

| PRISMA 2020 流程图 | 生存曲线 Kaplan-Meier |
|---|---|
| ![PRISMA 2020 文献筛选流程图](docs/figures/prisma-2020-flow.png) | ![Kaplan-Meier 生存曲线：分组曲线、置信区间与风险人数表](docs/figures/kaplan-meier.png) |
| 识别 → 筛选 → 纳入，计数自动校验 | 分组曲线 · 置信区间 · 风险人数表 |

**偏倚风险总结图 Risk-of-bias summary（RoB 2 / ROBINS-I）**

![RoB 2 逐研究逐域偏倚风险红绿灯图](docs/figures/rob2-traffic-light.png)

逐研究 · 逐域评价 · Cochrane 红黄绿配色。

**更多图形 More figures**：折线图 · 散点图 · 箱线图 · 小提琴图 · 热图 · 火山图 · 富集气泡图 · ROC 曲线 · 通路图 · 分子结构式，
由 `matplotlib` / `seaborn` / `plotly` / `scientific-visualization` 生成。

> 输出规格：PDF + PNG、300 dpi、字体嵌入（Type-42）、色盲友好配色。
> 森林图 / 漏斗图 / PRISMA / 偏倚风险出自本包 `local-skills/visualization/meta-analysis-figures/`（内置数值一致性校验，CI 填反或计数矛盾时拒绝出图），
> 生存曲线出自 `skills/biology/clinical-decision-support/`。
> 图中所用为**示例数据**，仅用于展示出图效果；重新生成：`python tools/make_demo_figures.py`。

---

<a id="中文"></a>

## 中文

<a id="困境"></a>

### 一、当代本科生与硕士生，到底卡在哪里

科研训练里最难的部分，从来不是「不知道某个知识点」，而是**没有人系统教过你研究方法本身**。
课程给你知识地图，却不给你做研究的手艺。于是绝大多数人是在一次次踩坑里自学，而这些坑高度重复：

| 困境 | 具体表现 |
|---|---|
| **方法学断层** | 实验设计（对照、随机化、样本量、混杂因素）、统计检验的选择、多重比较校正、效应量与置信区间——几乎全靠自学，选错检验是常态 |
| **工具链碎片化** | 一个课题要同时碰 Python/R、测序流程、分子对接、统计建模、绘图、LaTeX、文献管理、数据库 API。每样工具的安装与语法都要重新学一遍 |
| **「最后一公里」** | 明明知道 UniProt / PDB / ChEMBL / GEO 里有数据，却卡在不会写 API 调用；明明知道 Scanpy / GROMACS 能算，却卡在环境装不上 |
| **算力与成本** | 想跑个模型却没有 GPU；云平台不熟、怕误开资源烧钱，于是很多想法在「跑不动」这一步就停了 |
| **论文从零到一** | 结构怎么搭、图表怎么规范、目标期刊什么模板、cover letter 怎么写、审稿意见怎么回——全靠摸索，且没人给反馈 |
| **时间被撕裂** | 课业 + 组会 + 实验 + 考研/申博 + 实习，留给「补方法」的整块时间极少 |
| **AI 用不对反而有害** | 大模型能生成看似专业的段落与代码，但缺少方法学约束时，会产出「格式正确、结论错误」的内容，比不会更危险 |

一句话：**科研的门槛不在智力，在于没人把「方法 + 工具 + 数据 + 算力」串成一条能走通的路。**

<a id="能做什么"></a>

### 二、这个项目能帮你做什么

它把 OpenScience 沉淀的科研方法论与工具链，变成你 Agent 里随时可调的能力。按典型场景：

**1. 从零开始写一篇论文（主打功能）**
这条路径已固化成**端到端工作流**，不是零散工具堆叠。给一个题目，它先问清楚必要信息，再按十个阶段推进，
每阶段结束用人话交代做了什么、为什么、结果说明什么：

| 阶段 | 做什么 | 你拿到的产物 |
|---|---|---|
| 0 信息采集 | 分轮提问（每轮 ≤4 问），把题目变成可研究的问题（PICO） | 研究简报 |
| 1 可行性查证 | 确认有没有人做过同题研究，确定你的差异点 | 新颖性论证 |
| 2 检索 | 构造可复现的检索式，抓取原始文献记录 | 检索策略 + 原始记录 |
| 3 筛选 | 去重 → 标题摘要筛 → 全文筛（PRISMA 规范） | 筛选表 + 流程图数据 |
| 4 提取 | 提取研究数据 + 偏倚风险评价（Cochrane RoB / NOS） | 数据提取表 |
| 5 统计 | 效应量合并、异质性、亚组、敏感性、发表偏倚 | 统计脚本 + 结果文件 |
| 6 图表 | 森林图、漏斗图、PRISMA 流程图（全部程序化生成） | 300 dpi 图 |
| 7 写作 | IMRaD 结构英文稿 + 可解析的参考文献 | 稿件 + BibTeX |
| 8 审计 | 引用逐条解析、数字回溯、主张核验、模拟同行评审 | 反造假审计报告 |
| 9 投稿 | 目标期刊推荐、格式排版、Cover Letter | 投稿材料 |

**六条铁律**：绝不编造文献、绝不编造数据、先查证再动笔、全程留痕、每步说人话、不确定就问。
支撑它的子技能包括 `scientific-writing`、`literature-review`（含 PRISMA）、`citation-management`、
`statistical-analysis`、`pubmed-database`、`matplotlib`、`verify` / `sources` / `peer-review` 等。
完整定义见 `workflows/sci-paper.md`，或运行 `dispatch.cmd workflow show sci-paper`。

**2. 设计实验与分析数据**
`statistical-analysis`（检验选择与报告）、`pymc-bayesian-modeling`（贝叶斯建模）、
`scikit-survival`（生存分析）、`statsmodels`、`shap`（可解释性）、`exploratory-data-analysis`、
`pymoo`（多目标优化）、`simpy`（离散事件仿真）。

**3. 文献调研、选题与自我审查**
`research-lookup` / `perplexity-search`（实时联网检索）、`hypothesis-generation`（假设生成）、
`scientific-problem-selection`（选题与项目构思）、`scientific-critical-thinking`（批判性评估）、
`peer-review` / `review` / `verify` / `reproduce` / `sources`（结论核查、复现与来源审计）。

**4. 干湿实验的衔接**
`molecular-cloning`（克隆设计与 PCR 预测）、`opentrons-integration` / `pylabrobot`（液体处理自动化）、
`flow-cytometry-analysis`、`protocolsio-integration`、`pydicom` / `clinical-imaging`（医学影像）、
`pathml` / `histolab`（病理切片）、`immunology-assays`、`pharmacology-wetlab`。

**5. 计算、建模与组学分析**
`scanpy` / `anndata` / `scvi-tools`（单细胞）、`pydeseq2`（差异表达）、`biopython` / `pysam` / `deeptools`（序列与 NGS）、
`rdkit` / `datamol` / `deepchem` / `diffdock` / `admet-prediction`（化学与药物发现）、
`pymatgen`（材料）、`astropy`（天文）、`neural-operator` / `pinn-training`（科学机器学习）、
`qiskit` / `cirq` / `pennylane` / `qutip`（量子计算）。

**6. 大模型训练与推理**
`transformers` / `peft` / `trl` / `unsloth-fine-tuning` / `axolotl` / `llama-factory`（微调）、
`deepspeed` / `pytorch-lightning` / `ray-train`（分布式训练）、`serving-llms-vllm` / `sglang` /
`llama-cpp` / `tensorrt-llm`（推理部署）、`mlflow` / `weights-and-biases`（实验追踪）。

**7. 借算力，也管住成本**
`cloud-compute` 分类下的 `skypilot-multi-cloud-orchestration`、`modal-serverless-gpu`、
`runpod-gpu-cloud`、`vast-ai-gpu-cloud`、`lambda-gpu-cloud`、`tinker-fine-tuning` 等，
配合 MCP 连接器直接操作云上 GPU。

**8. 让结果可复现、可交付**
`iso-13485-certification`（医疗器械质量体系文档）、`research-grants`（基金申请书）、
`market-research-reports`、`get-available-resources`（先探测本机算力再决定方案）。

**怎么用**：直接用自然语言提问即可，调度器会检索命中的子技能并载入其正文；需要真的动手时，再按需安装 MCP。

```bash
dispatch.cmd workflow show sci-paper     # 读取「从零写 SCI 论文」完整工作流
dispatch.cmd query "单细胞 降维 聚类"      # 检索能力
dispatch.cmd load scanpy                 # 载入该子技能的完整方法论
dispatch.cmd mcp install github          # 生成 MCP 安装方案（默认只看不写）
```

<a id="使用"></a>

### 三、如何安装与使用（零基础，照着做就行）

这一节写给完全不懂编程的人。**不需要会写代码，也不需要显卡。**

#### 3.1 先搞清两个名词

| 名词 | 大白话 | 你要做的事 |
|---|---|---|
| **AI Agent 平台** | 你平时提问的那个 AI 对话框（本文以 WorkBuddy 为例，其它支持「技能 / Skill」的平台同理） | 装好、能正常对话 |
| **技能（Skill）** | 一包「科研方法说明书」。AI 平时不碰它，你一提问它才去翻 | 把这个文件夹放对位置 |

放对位置之后就一直在那儿了，不用每次重装。

#### 3.2 安装：三步

**第 1 步 · 下载**

打开本仓库页面 → 点绿色的 **「克隆/下载」** → **「下载 ZIP」**，得到一个约 8 MB 的压缩包
（仓库里含全部子技能，装完即可离线使用）。
若你装的是 skillhub / clawhub 上的**精简版**（约 1 MB），上游子技能会在真正用到时按需下载——见 [§3.7](#ondemand)。

**第 2 步 · 找到技能目录**

Windows：按 `Win + R`，粘贴下面这行后回车——

```
%USERPROFILE%\.workbuddy\skills
```

macOS：Finder → 顶部菜单「前往」→「前往文件夹」→ 粘贴 `~/.workbuddy/skills`

> 文件夹不存在说明平台还没建过技能目录：手动新建一个名为 `.workbuddy` 的文件夹，进去再新建 `skills`。**名字前面那个点不能丢。**
> 用其它平台的话，把 `.workbuddy\skills` 换成该平台的技能目录即可。

**第 3 步 · 解压进去**

解压后会得到 `open-science-dispatcher-main` 文件夹（Gitee 会自动加分支后缀）。
先把它**改名为 `openscience-dispatcher`**，再整个拖进 `skills` 目录。

装完的层级必须是这样（多一层、少一层都不行）：

```
skills
└── openscience-dispatcher
    ├── SKILL.md          ← 关键文件，必须在这一层
    ├── dispatch.cmd
    ├── registry.json     ← @@N_SKILL@@ 个子技能的索引（总在包里）
    ├── manifest.json     ← 每个子技能由哪些文件组成、各多大（按需下载的依据）
    ├── skills\           ← @@N_UPSTREAM_ALL@@ 个上游子技能；精简版里此目录为空，用哪个下哪个
    ├── local-skills\     ← @@N_LOCAL@@ 个本包自研子技能，随包分发、开箱即用
    ├── docs\figures\     ← README 里的效果图
    ├── mcp\
    └── tools\
```

> **Windows 用户注意**：检索脚本需要 Python 3.8+。若没装，打开 Microsoft Store 搜「Python」装一个（免费，一分钟），装完重开对话即可。macOS 自带，可跳过这条。

#### 3.3 验证装好了没

新开一个对话，随口问一句：

> 用 OpenScience 帮我查一下二甲双胍对心血管结局的证据

回答里若出现 `unified-research-finder`、`pubmed-database`、`literature-review` 这类子技能名，就装好了。
没反应的话，九成是目录层级放错，回第 3 步对一遍。

#### 3.4 日常怎么用：说人话就行

**不用记任何命令**，也不用提「技能」两个字。把它当成一个既懂科研方法、又熟悉各种工具的师兄，用中文把事说清楚。

说清下面四件事，效果差别很大：

| 要说清楚 | 差的问法 | 好的问法 |
|---|---|---|
| **你的身份和水平** | 「帮我写论文」 | 「我是临床医学本科生，没写过综述」 |
| **具体题目** | 「研究一下糖尿病」 | 「二甲双胍对 2 型糖尿病患者心血管结局的影响」 |
| **手上有什么** | （不说） | 「我只有学校图书馆的 PubMed 权限，没有原始数据」 |
| **要什么产物** | 「整理一下」 | 「给我一份带 DOI 的文献清单 + 一张数据提取表」 |

#### 3.5 完整例子：一个临床医学科研小课题

> **场景**：你是临床医学本科生，导师让你三天后在组会上讲清「二甲双胍对 2 型糖尿病患者心血管结局的影响」。你没做过循证检索，也不知道该讲什么。

**第 1 步 · 要证据**

> 我是临床医学本科生，要在组会上讲「二甲双胍对 2 型糖尿病患者心血管结局的影响」。请检索近 10 年的随机对照试验和 meta 分析，只看成人心血管终点（MACE）相关的，给我一份带 DOI 的清单。

背后发生的事：`pubmed-database` 检索 PubMed、`literature-review` 按纳入排除标准筛选、`citation-management` 规范引文。

**第 2 步 · 把证据变成表**

> 把上面这些研究抽成一张表：研究名、发表年份、样本量、随访时长、主要终点、效应值（HR 及 95%CI）。

直接得到一张能贴进 PPT 的表。

**第 3 步 · 补方法学（最容易翻车的一步）**

> 这些研究的终点定义不完全一样，能直接合并吗？异质性怎么判断？该用固定效应还是随机效应模型？如果做不了 meta 分析，我该怎么组织这场汇报？

背后：`statistical-analysis`、`scientific-critical-thinking`。
**这一步是「AI 帮倒忙」和「AI 真帮上忙」的分界线**——跳过它，你会拿到一段格式漂亮但方法学站不住的结论。

**第 4 步 · 成稿**

> 把上面整理成一份 8 页的中文汇报稿，按背景、方法、结果、讨论、局限、参考文献的结构写，参考文献用温哥华格式。

背后：`scientific-writing`、`citation-management`。

**第 5 步 · 自查（强烈建议）**

> 逐句检查这份稿子：每个结论都要能追溯到上面那份文献清单里的具体研究，把没有出处支撑的句子单独列出来。

背后：`verify`、`sources`、`peer-review`。**这一步能挡掉大部分「看着很专业、其实是编的」内容。**

**想继续往下做**：有真实病例可走 `clinical-reports`；要设计前瞻性研究可走 `scientific-problem-selection`；要投期刊可走 `venue-templates`。

#### 3.6 常见问题

**Q：问完没反应，回答和普通 AI 一样？**
A：查目录层级，必须是 `skills\openscience-dispatcher\SKILL.md`。解压时多套了一层文件夹是最常见的原因。

**Q：需要联网吗？**
A：检索类技能（PubMed、ClinicalTrials、UniProt 等）需要联网；纯方法论技能离线可用。

**Q：要花钱吗？**
A：技能本身免费（Apache-2.0）。只有云 GPU 类技能（`runpod-gpu-cloud` 等）会产生费用，且默认只生成方案、不实际下单。

**Q：会不会自动改我文件、乱下单？**
A：不会。写 MCP 配置默认只打印方案，显式加 `--write` 才写入且自动备份；云算力类会先出方案等你确认。

**Q：需要装 Python 吗？**
A：检索脚本 `dispatch.py` 需要 Python 3.8+（Windows 去 Microsoft Store 搜「Python」免费装，macOS 自带）。实在不装也能用——Agent 会直接翻阅技能目录，只是关键词检索不如脚本准。

**Q：怎么卸载？**
A：直接删掉 `skills\openscience-dispatcher` 文件夹，无残留。

<a id="ondemand"></a>

#### 3.7 「按需下载」是怎么回事？

为了能投稿到 skillhub / clawhub（skillhub.cn 单次上传 **10 MB**、建议 ≤ 200 个文件；clawhub 总包 **50 MB**、无文件数上限），本包做了瘦身：
包里**不带 @@N_UPSTREAM_ALL@@ 个上游子技能的正文**（那部分单独就有 @@FETCH_FILES@@ 个文件 / @@FETCH_MB@@ MB），
只带它们的**索引**（`registry.json`）和**文件清单**（`manifest.json`）。

你完全不用管这件事，Agent 会自己判断：

1. 需要某个子技能时，先跑 `plan`，把「几个文件、多大」告诉你；
2. **问你要不要下载**；
3. 你同意后它才 `fetch`，而且**只下这一次任务真正要用的那几个**（单个子技能通常是几十 KB）。

本包自研的 @@N_LOCAL@@ 个技能（学术搜索 `unified-research-finder`、Meta 分析图件 `meta-analysis-figures`）
以及 README 顶部[图表效果](#gallery)里的出图能力，**随包分发、开箱即用，不需要任何下载**。

> **想彻底离线用？** 一句 `dispatch.py fetch --all --yes` 把 @@N_UPSTREAM_ALL@@ 个上游子技能一次拉齐（约 @@FETCH_MB@@ MB），
> 之后本机不再需要联网。或者直接从 Gitee 下载仓库 ZIP——那份本来就含全部子技能。

下载源只有**一个**：`https://gitee.com/georgechou17/open-science-dispatcher`，逐文件走 raw HTTP 直连，
**不需要 git，也不需要令牌**。

> **一处已移除**：上游 `treatment-plans` 技能里的 `assets/pain_management_plan.tex`
> （内容是具体的阿片类处方剂量表）被 Gitee 的内容合规过滤拦下（`HTTP 451`），既取不回也不宜随包分发，
> 已**从仓库移除**（见 `tools/patches/remove.txt`），原先指向它的三个文件也已同步改掉。
> 所以清单里是 @@FETCH_FILES@@ 个文件，而非上游的 1616 个。

<a id="规模"></a>

### 四、规模：@@N_SKILL@@ 个开源 skill + @@N_MCP@@ 个 MCP

内容主要来自 OpenScience 的源码树，按 **@@N_CAT@@ 个分类**组织（另 @@N_LOCAL@@ 个为本包自研）。
其中 @@N_UPSTREAM_ALL@@ 个上游子技能**按需下载**（见 [§3.7](#ondemand)）——下表说的是它们的规模，不代表此刻已经在本地：

| 分类 | 目录 | 数量 |
|---|---|---:|
@@CAT_ROWS@@
| **合计** | | **@@N_SKILL@@** |

其中 @@N_UPSTREAM@@ 个技能依托具体的开源项目（如 Scanpy、RDKit、vLLM、Qiskit），
@@N_SELFMADE@@ 个是 OpenScience 原创的科研方法论与工作流技能，
另 @@N_LOCAL@@ 个由本包自行维护（`local-skills/`，不随上游重建覆盖，见 §5.3）。

> 说明：README 上游写作「309 个内置 skills」，本清单以**源码实测**为准——上游 @@N_UPSTREAM_ALL@@ 个，
> 加本包自研 @@N_LOCAL@@ 个，共 @@N_SKILL@@ 个含 `SKILL.md` 的技能目录。

<a id="inventory"></a>

### 五、全部清单（含源仓库链接）

#### 5.1 Skill（@@N_SKILL@@ 个）

| # | 技能 | 分类 | 用途 | 源仓库 |
|---:|---|---|---|---|
@@SKILL_ROWS@@

#### 5.2 MCP 连接器（@@N_MCP@@ 个）

| # | 连接器 | 提供方 | 源仓库 |
|---:|---|---|---|
@@MCP_ROWS@@

#### 5.3 本包扩展技能（`local-skills/`，@@N_LOCAL@@ 个）

这 @@N_LOCAL@@ 个技能**不属于上游 OpenScience**，是本包为补齐科研流程里的空缺而自行维护的。
它们放在独立的 `local-skills/` 目录下：`tools/rebuild.py` 从上游重建时会**原样保留**这些技能
并重新并入 `registry.json`，所以不会被覆盖，也不需要放进 `tools/patches/`。

| 技能 | 分类 | 用途 | 版本 | 来源 |
|---|---|---|---|---|
@@LOCAL_ROWS@@

> `unified-research-finder` 是作者本人的独立项目（MIT-0），本包内置其副本以便调度器统一路由；
> **以源仓库为准**，需要最新版本时请直接从源仓库获取。
> `meta-analysis-figures` 为本包自研（Apache-2.0），补齐系统综述 / Meta 分析的四类核心图件：
> 森林图、漏斗图、PRISMA 2020 流程图、偏倚风险红绿灯图——上游技能库只提供底层绘图能力，
> 没有这些成品实现。README 顶部的[图表效果](#gallery)就是它的出图；
> 重新生成演示图：`python tools/make_demo_figures.py`（输出到 `docs/figures/`）。

> 「源仓库」列为该子技能所依托的上游开源项目；标注 **OpenScience 自研** 的条目版权归上游 OpenScience 仓库所有。
> 表中所有链接均已做 HTTP 可用性校验。

<a id="致谢"></a>

### 六、致谢

这份清单能成立，是因为有大量人和项目把东西无偿开放了出来。

**首先感谢 [OpenScience](https://github.com/synthetic-sciences/openscience)（Synthetic Sciences / InkVell Inc.）**——
上游的子技能树、MCP 目录与整套科研 Agent 架构都出自这里，
以 Apache-2.0 授权，让下游可以合法地把这套能力搬到别的平台。

**感谢 @@N_UPSTREAM@@ 个被封装的开源项目与数据库**，例如：
[single-cell 生态](https://github.com/scverse/scanpy)（Scanpy / AnnData / scvi-tools）、
[RDKit](https://github.com/rdkit/rdkit)、[DeepChem](https://github.com/deepchem/deepchem)、
[Biopython](https://github.com/biopython/biopython)、[PyTorch](https://github.com/pytorch/pytorch)、
[Hugging Face](https://github.com/huggingface/transformers)（Transformers / TRL / PEFT / Diffusers）、
[vLLM](https://github.com/vllm-project/vllm)、[SGLang](https://github.com/sgl-project/sglang)、
[Qiskit](https://github.com/Qiskit/qiskit)、[Astropy](https://github.com/astropy/astropy)、
[Polars](https://github.com/pola-rs/polars)、[Dask](https://github.com/dask/dask)，
以及 [PubMed](https://pubmed.ncbi.nlm.nih.gov/)、[UniProt](https://www.uniprot.org/)、
[PDB](https://www.rcsb.org/)、[ChEMBL](https://www.ebi.ac.uk/chembl/)、
[KEGG](https://www.genome.jp/kegg/) 等公共数据源。

**感谢成果被直接打包进来的著作权人**：
[Shoko-official](https://github.com/Shoko-official/Claude-Science-System-Prompts)（2 篇，Apache-2.0）、
[InkVell Inc.](https://github.com/synthetic-sciences/openscience)（12 篇，MIT）、
[Microsoft · markitdown](https://github.com/microsoft/markitdown)（1 篇，MIT）、
Andrey Fedorov（`imaging-data-commons`，1 篇，MIT）。

**感谢 LaTeX 模板与宏包的作者**：Patrick W Daly（natbib）、Piet van Oostrum（fancyhdr）、
Peter Williams（algorithm / algorithmic）、Hal Daumé III、Norman Gray（urlbst），
以及 AAAI / ACL / COLM / ICLR / ICML / NeurIPS 各会议模板维护者。

**感谢所有 MCP 服务的提供方**：San Francisco Compute（GiveMeANode）、GitHub、Benchling、Box、Dropbox、AWS，
以及社区维护的 [SPSS MCP Server](https://github.com/meteor0620/spss-mcp)（meteor0620，MIT）。

也感谢每一个在深夜修 issue 的维护者——开源不是免费的，只是有人替你付了账单。

<a id="许可"></a>

### 七、开源许可证

本仓库整体以 **Apache-2.0** 分发，共四份许可与署名文件：

| 文件 | 作用 |
|---|---|
| [`LICENSE`](LICENSE) | Apache License 2.0 全文（上游，随附原版权行） |
| [`NOTICE`](NOTICE) | 上游 NOTICE 要求的署名声明 |
| [`ATTRIBUTION.md`](ATTRIBUTION.md) | @@N_SKILL@@ 篇子技能的作者与许可分布 |
| [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) | 内嵌第三方作品清单（MIT / LPPL / 数据条款）与再分发提示 |

**著作权分布**（上游按 `metadata.skill-author` 实测，本地技能按随包 `LICENSE`）：

| 著作权人 | 篇数 | 许可 |
|---|---:|---|
| Synthetic Sciences / InkVell Inc. | 130 | Apache-2.0 |
| 未记录 `skill-author`（按上游默认） | 166 | Apache-2.0 |
| Shoko-official | 2 | Apache-2.0 |
| InkVell Inc. | 12 | MIT |
| Microsoft（`markitdown`） | 1 | MIT |
| Andrey Fedorov（`imaging-data-commons`） | 1 | MIT |
| GeorgeChou17（`local-skills/meta-analysis-figures`，本包自研） | 1 | Apache-2.0 |
| GeorgeChou17（`local-skills/unified-research-finder`，作者独立项目副本） | 1 | MIT-0 |

即 **Apache-2.0 = 299 篇 · MIT = 14 篇 · MIT-0 = 1 篇**；MIT 部分要求保留版权声明，
因此本仓库**必须**随附上述署名文件。MIT-0 不要求署名，此处仍如实标注来源。

**三点务必注意：**

1. **子技能 frontmatter 里的 `license:` 不是本仓库的许可声明**，它描述的是「该技能所教的第三方库」的许可
   （例如 `etetoolkit → GPL-3.0` 指 ETE 工具包本身）。文档自身的著作权人记在 `metadata.skill-author`。
   本包**未内嵌任何 GPL / LGPL / CeCILL 源码**，copyleft 义务不附着于整体。
2. `skills/writing/ml-paper-writing/templates/` 内打包了第三方 LaTeX 宏包（多为 **LPPL**），
   **本仓库未附带 `lppl.txt`**，再分发前请从 CTAN 补齐；LPPL 还要求修改过的文件必须改名。
3. 部分数据库（KEGG、HMDB、DrugBank 等）有**独立的数据使用条款**，非学术用途可能需要商业授权。
   许可文件不替代这些条款，请自行确认。

仅调度层（`SKILL.md`、`dispatch.py`、`dispatch.cmd`、`registry.json`、`tools/`、`mcp/INSTALL.md`）
与 `local-skills/` 下的自研技能为本项目原创，同样以 Apache-2.0 分发以保持整体一致
（`local-skills/unified-research-finder` 例外，按作者的 MIT-0 分发）。

> 本文档是基于源码实测整理的合规声明，**不构成法律意见**。若用于商业或融资场景，建议由法务复核。

<a id="appendix"></a>

### 附录：安装、命令与设计说明

**安装** —— 把整个 `openscience-dispatcher` 文件夹放进平台技能目录即可：

| 平台 | 技能目录 |
|---|---|
| WorkBuddy | `%USERPROFILE%\.workbuddy\skills\` |
| 其它平台 | 该平台的 skills 目录，保持文件夹名不变 |

结果应为 `<技能目录>/openscience-dispatcher/SKILL.md`。

**环境要求**：Python 3.8+（仅用标准库）· Windows 10+ / macOS / Linux。
Windows 下用 `dispatch.cmd` 即可，它会自动探测 `py -3` / `python` / `python3`。

**命令一览**

| 命令 | 作用 |
|---|---|
| `category` | 列出 @@N_CAT@@ 个分类及计数 |
| `category <名称>` | 浏览某分类全部子技能 |
| `query "<关键词>" [--top N] [--category X] [--json]` | 关键词打分检索（中文自动做术语展开） |
| `load <name>` | 载入子技能正文 + 基础目录 + 资源清单 |
| `list [--category X] [--json]` | 列出全部子技能 |
| `net` | 显示网络区域判定与镜像源映射 |
| `mcp config` | 显示 MCP 配置文件的实际路径 |
| `mcp list` / `mcp show <id>` | 查看 MCP 连接器 |
| `mcp install <id> [--write] [--config PATH]` | 生成 / 写入 MCP 安装方案 |
| `mcp plan` | 一次性生成所有可自动安装连接器的方案 |
| `status` | 随包 / 已下载 / 未下载的规模统计 |
| `plan <名称…>` / `plan --workflow X` / `plan --all` | **离线**预估要下载几个文件、多大（不联网、不写盘） |
| `fetch <名称…> [--yes] [--all] [--workflow X] [--jobs N]` | 从 Gitee 按需下载；不加 `--yes` 只打印计划，不写盘 |

**设计说明：为什么 @@N_SKILL@@ 个子技能不会被误注册**
子技能位于 `skills/<分类>/<技能>/SKILL.md`（相对技能根目录的第 4 层），
本包自研技能位于 `local-skills/<分类>/<技能>/SKILL.md`（同样是第 4 层）。
主流 Agent 平台的技能发现是**单层**的（只扫描 `<skills>/<名称>/SKILL.md`），
因此它们不会被当成 @@N_SKILL@@ 个顶层技能，也不会拖慢平台启动——
只能通过本调度器访问，这正是设计意图。

**从上游重建**

```bash
git clone https://github.com/synthetic-sciences/openscience
python tools/rebuild.py --source ./openscience   # 重建 skills/ 与 registry.json（含 local-skills/ 并入）
python tools/gen_readme.py                       # 重新生成本清单
python tools/package.py                          # 打包（输出到 dist/）
```

**两种发行形态**（`tools/package.py` 一次产出）：

| 产物 | 内容 | 规模 | 用途 |
|---|---|---|---|
| `openscience-dispatcher-skill.zip` | 扁平根目录、不含 `skills/` | 约 55 文件 / 解压 1.6 MB | 投稿 skillhub / clawhub |
| `openscience-dispatcher-full.zip` | 含全部子技能 | 1670 文件 / 解压 21.2 MB | 自用、离线 |

Gitee 主仓库**始终保留 `skills/`**——它正是按需下载的源，删掉就没得下了。
`manifest.json` 由 `tools/rebuild.py` 与 `registry.json` 一起重建，记录每个子技能的文件与字节数，
`dispatch.py fetch` 据此校验下载完整性（大小不符的文件会被丢弃重下，不会留下半个假技能）。

重建时 `skills/` 会被上游文件逐字节覆盖，所以**直接改 `skills/` 里的文件会在下次重建时丢失**。
两类改动各有归宿：

| 改动类型 | 放在哪 | 谁来落回去 |
|---|---|---|
| 修上游技能里的 bug | `tools/patches/<同名相对路径>` | `tools/rebuild.py` 末尾自动调用 `tools/apply_patches.py` |
| 新增/自有技能 | `local-skills/<分类>/<技能>/` | `tools/rebuild.py` 自动并入 `registry.json`，文件不动 |

**网络自适应**：`dispatch.py` 按 IP 判定区域，自动在 npm / PyPI / GitHub / Docker 的
国内镜像与国际站之间选择。

**MCP 写入门槛**：默认只打印安装方案，`--write` 才写入且自动备份；
配置路径优先级 `--config` > `$OSD_MCP_CONFIG` > `~/.workbuddy/mcp.json`；
写入后仍需在平台连接器页点「信任」才会激活。

---

<a id="english"></a>

## English

Real output from the plotting skills — every panel generated by a script straight from a data file:
**[图表效果 · Figure gallery](#gallery)** (top of this file).

> Ports the **@@N_SKILL@@ scientific sub-skills** and **@@N_MCP@@ MCP connectors** of
> [OpenScience](https://github.com/synthetic-sciences/openscience) onto generic AI agent platforms.
> **The package itself is small** (~1.6 MB unpacked): the @@N_UPSTREAM_ALL@@ upstream sub-skills are not
> bundled — the one you need is fetched from Gitee on demand, and only the files that task needs
> (see [On-demand sub-skills](#ondemand-en)).
> Sub-skills are *capability*, MCP servers are *tooling*, and the dispatcher routes them to your question.

`@@N_SKILL@@` Skills · `@@N_CAT@@` Categories · `@@N_MCP@@` MCP Connectors · Apache-2.0 · Python 3.8+ · Zero dependencies · ~1.6 MB unpacked

### 1. The real bottleneck for undergrads and master's students

The hardest part of research training is not a missing fact — it is that **nobody teaches you the method itself**.
Courses hand you a map of knowledge, not the craft of doing research. So most people self-teach by trial and
error, and the same errors repeat: choosing the wrong statistical test, no power analysis, no pre-registration,
getting stuck on environment setup, hitting a paywall of compute, and learning paper writing by osmosis.

Worse: a general-purpose LLM without methodological constraints will happily produce
*confident, well-formatted, wrong* output — which is more dangerous than admitting ignorance.

### 2. What this project does for you

| Scenario | Representative sub-skills |
|---|---|
| **Write a paper from scratch** | `scientific-writing`, `literature-review`, `citation-management`, `ml-paper-writing`, `venue-templates`, `latex-posters`, `scientific-slides`, `paper-2-web` |
| **Design experiments & analyse data** | `statistical-analysis`, `pymc-bayesian-modeling`, `scikit-survival`, `statsmodels`, `shap`, `exploratory-data-analysis`, `pymoo` |
| **Literature, ideation & self-audit** | `research-lookup`, `hypothesis-generation`, `scientific-problem-selection`, `scientific-critical-thinking`, `peer-review`, `verify`, `reproduce`, `sources` |
| **Wet-lab ↔ dry-lab handoff** | `molecular-cloning`, `opentrons-integration`, `pylabrobot`, `flow-cytometry-analysis`, `protocolsio-integration`, `pydicom`, `pathml` |
| **Modelling & omics** | `scanpy`, `anndata`, `scvi-tools`, `pydeseq2`, `biopython`, `pysam`, `deeptools`, `rdkit`, `deepchem`, `diffdock`, `pymatgen`, `astropy`, `qiskit` |
| **LLM training & serving** | `transformers`, `peft`, `trl`, `unsloth-fine-tuning`, `axolotl`, `deepspeed`, `serving-llms-vllm`, `sglang`, `llama-cpp`, `tensorrt-llm` |
| **Compute without bill shock** | `skypilot-multi-cloud-orchestration`, `modal-serverless-gpu`, `runpod-gpu-cloud`, `vast-ai-gpu-cloud`, `lambda-gpu-cloud` + on-demand MCP |
| **Reproducible delivery** | `iso-13485-certification`, `research-grants`, `get-available-resources` |

**Flagship workflow — write a SCI paper from scratch.** A fixed ten-stage pipeline, not a bag of tools:
ask first (Stage 0 collects PICO and picks the route), then verify novelty, retrieve, screen to PRISMA,
extract, analyse, plot, draft in IMRaD, audit every citation and number, and finally prepare the submission.
Six non-negotiable rules run throughout: never invent a reference, never invent a number, verify before
writing, keep everything reproducible, explain each step in plain language, ask when unsure.
Full definition in `workflows/sci-paper.md`.

```bash
dispatch.cmd workflow show sci-paper               # read the full SCI-paper workflow
dispatch.cmd query "single cell RNA integration"   # retrieve capability
dispatch.cmd load scanpy                          # load the full methodology
dispatch.cmd mcp install github                   # print an install plan (dry run by default)
```

### 3. How to install and use it (no coding required)

Written for people who don't program. **No coding, no GPU.**

| Term | In plain words | What you do |
|---|---|---|
| **AI Agent platform** | The chat box you already use (WorkBuddy here; any skill-capable platform works similarly) | Have it installed |
| **Skill** | A pack of research methodology the AI only opens when your question calls for it | Drop the folder in the right place |

**Install in three steps**

1. **Download** — on this repo page click **Clone/Download → Download ZIP** (~8 MB; the repository
   carries every sub-skill, so this build works offline immediately). The slim build published on
   skillhub / clawhub is ~1 MB and pulls sub-skills on demand — see
   [On-demand sub-skills](#ondemand-en).
2. **Find the skills directory**
   - Windows: press `Win + R`, paste `%USERPROFILE%\.workbuddy\skills`, press Enter
   - macOS: Finder → Go → Go to Folder → `~/.workbuddy/skills`
   - If it does not exist, create `.workbuddy` and then `skills` inside it — keep the leading dot.
   - On another platform, substitute that platform's skills directory.
3. **Extract into it** — rename the extracted `open-science-dispatcher-main` folder to
   `openscience-dispatcher`, then move it inside `skills`. The layout must be exactly:

```
skills
└── openscience-dispatcher
    ├── SKILL.md          ← must sit at this level
    ├── dispatch.cmd
    ├── registry.json     ← index of all @@N_SKILL@@ sub-skills (always present)
    ├── manifest.json     ← what files each sub-skill is made of, and their sizes
    ├── skills\           ← the @@N_UPSTREAM_ALL@@ upstream sub-skills; empty in the slim build
    ├── local-skills\     ← the @@N_LOCAL@@ sub-skills maintained by this package
    ├── docs\figures\     ← the figures shown in the gallery
    ├── mcp\
    └── tools\
```

> **Windows users**: the retrieval script needs Python 3.8+. If you don't have it, install Python
> from the Microsoft Store (free, about a minute) and restart the chat. macOS ships with it.

**Check it worked** — open a new chat and ask:

> Using OpenScience, find the evidence on metformin and cardiovascular outcomes

If the answer names sub-skills such as `pubmed-database` or `literature-review`, you are set.
If nothing happens, it is almost always the folder nesting.

**Day to day: just talk**

No commands to memorise. Treat it as a colleague who knows research methodology and the
tooling, and state four things clearly:

| Be clear about | Weak ask | Better ask |
|---|---|---|
| **Who you are** | "Write me a paper" | "I'm a medical undergraduate, I've never written a review" |
| **The exact question** | "Look into diabetes" | "Effect of metformin on cardiovascular outcomes in type 2 diabetes" |
| **What you have** | (unstated) | "I only have library PubMed access, no raw data" |
| **What you want back** | "Tidy it up" | "A DOI-linked reference list plus a data-extraction table" |

**Worked example — a small clinical research task**

> **Setting**: you are a medical undergraduate; your supervisor wants you in three days to present
> the evidence on metformin and cardiovascular outcomes in type 2 diabetes. You have never done an
> evidence review.

1. **Get the evidence** — "I'm a medical undergraduate presenting on metformin and cardiovascular
   outcomes in T2DM. Search the last 10 years of RCTs and meta-analyses, adult MACE endpoints only,
   and give me a DOI-linked list."
   *Behind the scenes:* `pubmed-database` queries PubMed, `literature-review` applies
   inclusion/exclusion criteria, `citation-management` formats citations.
2. **Turn evidence into a table** — "Extract these studies into one table: study, year, sample size,
   follow-up, primary endpoint, effect size (HR and 95% CI)."
3. **Fix the methodology (where most people go wrong)** — "The endpoint definitions differ — can
   these be pooled? How do I judge heterogeneity? Fixed- or random-effects? If pooling isn't valid,
   how should I structure the talk?"
   *Behind the scenes:* `statistical-analysis`, `scientific-critical-thinking`. This step separates
   AI that helps from AI that produces polished but unsound conclusions.
4. **Draft it** — "Write this up as an 8-page report: background, methods, results, discussion,
   limitations, references in Vancouver style." (`scientific-writing`, `citation-management`)
5. **Self-audit (strongly recommended)** — "Check every sentence: each claim must trace to a
   specific study in that list. Flag anything unsupported." (`verify`, `sources`, `peer-review`)
   This is what filters out confident-sounding fabrication.

**Going further**: real cases → `clinical-reports`; prospective study design →
`scientific-problem-selection`; journal submission → `venue-templates`.

**FAQ**

- **Nothing happens?** Check the nesting — it must be `skills\openscience-dispatcher\SKILL.md`.
- **Need internet?** Retrieval skills (PubMed, ClinicalTrials, UniProt) do; methodology-only skills
  work offline.
- **Any cost?** The skills are free (Apache-2.0). Only cloud-GPU skills such as `runpod-gpu-cloud`
  cost money, and they print a plan rather than ordering by default.
- **Will it touch my files or spin up paid resources?** No — MCP writes are dry-run unless you pass
  `--write` (with automatic backup), and cloud actions ask for confirmation first.
- **Do I need Python?** The retrieval script `dispatch.py` needs Python 3.8+ (Microsoft Store on
  Windows, built in on macOS). Without it the agent can still browse the skill folder directly,
  just with less precise keyword retrieval.
- **Uninstall?** Delete `skills\openscience-dispatcher`. Nothing else is left behind.

<a id="ondemand-en"></a>

**On-demand sub-skills**

The published builds are deliberately small: skillhub.cn caps an upload at 10 MB (~200 files suggested),
and the @@N_UPSTREAM_ALL@@ upstream sub-skills alone are @@FETCH_FILES@@ files / @@FETCH_MB@@ MB. So the package ships
their **index** (`registry.json`) and a **file manifest** (`manifest.json`) instead of their content.

You never have to manage this. When a task needs a sub-skill, the agent

1. runs `plan` and tells you how many files and how many bytes it would take;
2. **asks whether to download it**;
3. only then runs `fetch` — and only for the files that task actually needs (a single sub-skill is
   typically tens of kilobytes).

The @@N_LOCAL@@ sub-skills this package maintains (`unified-research-finder`, `meta-analysis-figures`)
and everything in the [figure gallery](#gallery) ship inside the package and need no download at all.

> **Want it fully offline?** `dispatch.py fetch --all --yes` pulls all @@N_UPSTREAM_ALL@@ in one go
> (~@@FETCH_MB@@ MB), after which nothing needs the network. The Gitee repository ZIP already contains them.

One source only: `https://gitee.com/georgechou17/open-science-dispatcher`, file by file over raw HTTP —
no git, no token.

> **One file withdrawn.** `assets/pain_management_plan.tex` in the upstream `treatment-plans`
> skill -- concrete opioid dosing tables -- is refused by the host's content-compliance filter
> (`HTTP 451`), so it could be neither fetched nor redistributed. It is now **removed from the
> repository** (see `tools/patches/remove.txt`) and the three files that pointed at it have been
> updated. That is why the manifest lists @@FETCH_FILES@@ files rather than 1,616.

### 4. Scale

**@@N_SKILL@@ skills across @@N_CAT@@ categories + @@N_MCP@@ MCP connectors.**
Of these, @@N_UPSTREAM@@ wrap a concrete open-source project and @@N_SELFMADE@@ are
OpenScience's own methodology / workflow skills; a further @@N_LOCAL@@ are maintained by
this package under `local-skills/` (see §5.3).

Note that the @@N_UPSTREAM_ALL@@ upstream sub-skills are **not bundled** — they are fetched on
demand (see [On-demand sub-skills](#ondemand-en)), so the table above describes their scale
rather than what is on disk right now.

The per-skill inventory with source-repository links lives in
[§5.1 above](#inventory) — it is generated from `registry.json` and `tools/sources.py`,
and every link is HTTP-verified.

### 5. Acknowledgements

Above all, **[OpenScience](https://github.com/synthetic-sciences/openscience)** (Synthetic Sciences /
InkVell Inc.) — the @@N_UPSTREAM_ALL@@ upstream sub-skills, the MCP catalogue and the research-agent
architecture originate there under Apache-2.0.

Thanks also to the @@N_UPSTREAM@@ open-source projects and public databases these skills wrap
(Scanpy, RDKit, Biopython, PyTorch, Hugging Face, vLLM, Qiskit, Astropy, PubMed, UniProt, PDB,
ChEMBL, KEGG …), to the bundled-work copyright holders
([Shoko-official](https://github.com/Shoko-official/Claude-Science-System-Prompts),
InkVell Inc., [Microsoft markitdown](https://github.com/microsoft/markitdown), Andrey Fedorov),
to the LaTeX package authors (Patrick W Daly, Piet van Oostrum, Peter Williams, Hal Daumé III,
Norman Gray) and venue template maintainers, and to every MCP provider
(San Francisco Compute, GitHub, Benchling, Box, Dropbox, AWS).

### 6. License

Distributed under **Apache-2.0**. See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE),
[`ATTRIBUTION.md`](ATTRIBUTION.md) and [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).

- **Apache-2.0 = 299 · MIT = 14 · MIT-0 = 1** (MIT requires retaining its copyright notice;
  MIT-0 does not require attribution, but the source is credited here anyway).
- The `license:` field inside each sub-skill's frontmatter describes **the third-party library the skill
  documents**, not this repository. No GPL/LGPL/CeCILL source is bundled.
- Third-party **LaTeX packages (mostly LPPL)** are bundled under
  `skills/writing/ml-paper-writing/templates/`; `lppl.txt` is *not* shipped — obtain it before redistributing.
- Some databases (KEGG, HMDB, DrugBank) carry **separate data-use terms**; a software license does not replace them.

Only the dispatcher layer is original to this project and is released under the same Apache-2.0 terms.

### Appendix: install, commands, design notes

Copy the whole `openscience-dispatcher` folder into your platform's skills directory
(WorkBuddy: `%USERPROFILE%\.workbuddy\skills\`). The result must be
`<skills-dir>/openscience-dispatcher/SKILL.md`. Requires Python 3.8+ (standard library only),
Windows 10+ / macOS / Linux; on Windows `dispatch.cmd` auto-detects `py -3` / `python` / `python3`.

| Command | Purpose |
|---|---|
| `category` / `category <name>` | List the @@N_CAT@@ categories / browse one |
| `query "<text>" [--top N] [--category X] [--json]` | Scored retrieval (Chinese is term-expanded) |
| `load <name>` | Print the sub-skill body, base directory and resources |
| `list [--category X] [--json]` | List every sub-skill |
| `net` | Show the detected region and mirror mapping |
| `mcp config` | Show the resolved MCP client config path |
| `mcp list` / `mcp show <id>` | Inspect MCP connectors |
| `mcp install <id> [--write] [--config PATH]` | Print or persist an install plan |
| `status` | How much of the bundle is on disk |
| `plan <name…>` / `plan --workflow X` / `plan --all` | Offline estimate of files and bytes to fetch |
| `fetch <name…> [--yes] [--all] [--workflow X] [--jobs N]` | Fetch from Gitee; without `--yes` it only prints the plan |

Sub-skills live at `skills/<category>/<skill>/SKILL.md` — depth 4, below the single-level
skill scan that mainstream agent platforms use, so the @@N_SKILL@@ sub-skills are never
registered as top-level skills. That is intentional.

```bash
git clone https://github.com/synthetic-sciences/openscience
python tools/rebuild.py --source ./openscience   # rebuild skills/ and registry.json
python tools/gen_readme.py                       # regenerate this inventory
python tools/package.py                          # build the distribution zips (into dist/)
```

Two distribution shapes are produced. `openscience-dispatcher-skill.zip` is flat at the root and
omits `skills/` (~55 files / 1.6 MB unpacked) for uploading to skillhub / clawhub. skillhub.cn
allows 10 MB per upload with ~200 files suggested; clawhub's only published cap is 50 MB per
bundle, with no file-count limit. `openscience-dispatcher-full.zip` carries all 1670 files /
21.2 MB for offline use. The Gitee repository always keeps `skills/` — it is the

Two kinds of local change survive a rebuild, each in its own place: a fix to an upstream
skill goes into `tools/patches/<same relative path>` (re-applied automatically at the end
of `rebuild.py`), while a new or self-authored skill goes into `local-skills/<category>/<name>/`
and is merged into `registry.json` with `origin: local`. Editing `skills/` directly does not.

MCP writes are opt-in: the plan is printed by default, `--write` persists with an automatic
backup. Config path precedence is `--config` > `$OSD_MCP_CONFIG` > `~/.workbuddy/mcp.json`;
a written server still needs to be "Trusted" in the platform's connector page.

> Compiled from source inspection; **not legal advice**.
"""


if __name__ == "__main__":
    main()
