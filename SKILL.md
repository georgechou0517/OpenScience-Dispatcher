---
name: openscience-dispatcher
version: 1.3.1
description: 综合科研调度器（OpenScience Dispatcher）——把 312 个上游 OpenScience 子技能（16 类：ml-training / biology / databases / llm-tools / chemistry / physics / coding / research / cloud-compute / data-engineering / writing / ml-inference / visualization / quantum / other / document-parsing）加 2 个本包自研子技能（学术搜索 unified-research-finder、Meta 分析图件 meta-analysis-figures），共 314 个，与 7 个按需安装的 MCP 工具，在通用 AI Agent 平台上编排成类 OpenScience 的科研工作流。**内置端到端 SCI 论文工作流**：面向零科研基础的本科生，从一句话题目经信息采集、可行性查证、检索、PRISMA 筛选、数据提取、统计、图表、英文稿、反造假审计到投稿准备，全程由本调度器串联子技能完成。触发场景：从零写一篇 SCI 论文、系统综述 / Meta 分析、森林图 / 漏斗图 / PRISMA 流程图 / 偏倚风险图、文献检索与循证写作（PubMed / Google 学术 / 学术镜像 / 影响因子）、单细胞与组学分析、结构生物学与药物设计、化学信息学、科学数据库查询（UniProt / PDB / ChEMBL / PubMed 等）、模型训练与微调、GPU 云算力调度、量子计算、科学可视化、同行评审；或用户直接提到 OpenScience、子技能、科研调度、scientific workflows。
agent_created: true
license: Apache-2.0
triggers:
  - OpenScience
  - 科研调度
  - 子技能
  - 写SCI论文
  - 从零写论文
  - 写一篇论文
  - 系统综述
  - meta分析
  - 荟萃分析
  - 文献检索
  - 学术搜索
  - 找文献
  - 科研入门
  - 单细胞分析
  - 组学分析
  - 药物设计
  - 化学信息学
  - 科学数据库
  - 模型微调
  - GPU 算力
  - 量子计算
  - 科学可视化
  - 森林图
  - PRISMA
  - SPSS
  - 论文写作
  - 同行评审
---

# OpenScience Dispatcher

把 314 个科研子技能当作**可检索的能力库**（312 个上游 + 2 个本包自研），把 7 个 MCP 连接器当作**按需安装的外部工具**，由本调度器统一路由、加载、执行。

本文件所在目录记作 `$OSD`（即本包根目录）。安装到 Agent 平台后通常位于 `<用户目录>/.workbuddy/skills/openscience-dispatcher`。
所有命令都在 `$OSD` 内执行；**不要**把 `$OSD/skills/**/SKILL.md` 当作顶层技能去调用——它们只能经调度器访问。

---

## 一、四层调度模型

```
用户任务
   │
   ├─ 0. workflow orchestration  dispatch.py workflow show sci-paper  → 拿到阶段、门控与产物规范
   ├─ 1. capability routing      dispatch.py query "<关键词>"          → 命中哪几个子技能
   ├─ 2. skill loading           dispatch.py load <name>               → 拿到 SKILL.md 正文 + 基础目录 + 资源清单
   └─ 3. tool provisioning       dispatch.py mcp install <id>          → 需要外部系统时按需装 MCP
```

**第 0 层是可选的编排层。** 当任务是"从零写一篇论文"这类**跨越多个子技能的长流程**时，先取工作流定义，
它规定了下游阶段顺序、每阶段的准入与门控、产物文件，以及必须遵守的铁律。单点任务（"帮我把这个蛋白质结构预测一下"）
不需要第 0 层，直接从第 1 层检索入手。

子技能是**能力**（知道怎么做科研），MCP 是**工具**（能碰到外部系统）。两者职责不重叠：
子技能告诉你"用什么方法、跑什么代码、如何解读结果"；MCP 让你"真的去 GitHub / 云存储 / GPU 集群上动手"。

---

## 二、端到端工作流

工作流定义放在 `$OSD/workflows/*.md`，由 `dispatch.py workflow` 读取（文件名即 id，无需额外登记）。

| 子命令 | 作用 |
|---|---|
| `workflow` / `workflow list` | 列出全部工作流 |
| `workflow show <id>` | 打印某个工作流的完整定义 |

### 已有工作流

| id | 名称 | 适用 |
|---|---|---|
| `sci-paper` | 从零到一篇 SCI 论文初稿 | 零科研基础的本科生 / 研究生，给出题目即可 |

`sci-paper` 的完整定义见 `workflows/sci-paper.md`，**执行前必须完整读一遍**。它规定了：

- **六条铁律**：绝不编造文献、绝不编造数据、先查证再动笔、全程留痕、每步说人话、不确定就问
- **三条路线**：系统综述 / Meta 分析（默认推荐）、叙述性综述、公开数据库二次分析
- **十个阶段（Stage 0–9）**：Intake 信息采集 → 可行性查证 → 检索 → PRISMA 筛选 → 数据提取 → 统计 → 图表 → 英文稿 → 反造假审计 → 投稿准备
- **每阶段的准入条件、要调用的子技能、产物文件、门控条件**
- **分轮提问设计**（一轮不超过 4 个问题）与"信息已足够"的判据
- **产物目录规范**与中断恢复方式
- **每阶段结束的固定四段话术**：做了什么 / 为什么 / 说明什么 / 需要你确认什么

**这条工作流的价值不在于"生成文本"，而在于先问清楚、再查证、最后才动笔。**
缺少必要信息时必须停下来问用户（一轮 ≤4 个问题）；信息足够（PICO 明确 + 路线确定 + 主要结局明确）
之后才开始检索。阶段之间可以有简短对话确认方向，但**不许跳过门控**。

---

## 三、检索引擎

统一入口，零第三方依赖，需 Python 3.8+。

调用方式（任选其一）：

| 平台 | 命令 |
|---|---|
| Windows | `dispatch.cmd <子命令>`（自动探测 Python，无需配路径） |
| 通用 | `python "dispatch.py" <子命令>` |
| macOS / Linux | `python3 "dispatch.py" <子命令>` |

> 若 `python` 不在 PATH，可用 Windows 的 `py -3`，或任何绝对路径的解释器。

| 子命令 | 作用 |
|---|---|
| `category` | 列出 16 个分类及计数 |
| `category biology` | 浏览某分类全部子技能 |
| `query "single cell RNA integration"` | 关键词打分检索，返回 Top-N |
| `query "蛋白结构预测" --category biology --top 5` | 限定分类检索（支持中文） |
| `load scanpy` | 载入子技能：正文 + 基础目录 + 资源清单 |
| `list --json` | 全量导出（脚本消费用） |
| `net` | 显示网络区域判定与镜像源映射 |
| `mcp config` | 显示 MCP 客户端配置文件的实际路径 |
| `mcp list` | 列出 7 个 MCP 连接器、读写操作与前置要求 |
| `mcp install <id>` | 生成该连接器的安装方案（默认只打印，`--write` 才落盘） |
| `workflow show <id>` | 读取端到端工作流定义（见第二节） |

`query` 的排序依据：名称精确匹配 > 名称包含 > 标签 > 描述 > 功能摘要 > 分类。
匹配按**词边界**进行（`meta` 不会命中 `metabolomics`），而非裸子串。
中文查询会先做**术语展开**（如「分子对接 打分」→ `molecular docking` + `scoring`）再打分，因为上游技能名与描述是英文优先的。
展开出的英文**短语**若整体命中某技能的元数据，会获得远高于其组成单词的权重——这保证「meta 分析」命中
`literature-review` 这类真正相关的技能，而不会被名字里恰好含 `-analysis` 的无关技能挤掉。

中文**标签**按命中方式分两档：技能自己声明的中文标签（如自研技能 `unified-research-finder` 的「找文献」）
命中时权重最高；仅作为某个**更长标签的子串**命中时权重很低。中文没有词边界，若不区分，
查询「我要找文献」里的「文献」会误命中 `literature-review` 的别名标签「文献综述」，把用户的学术搜索技能挤到第二。

⚠️ **上游技能多为英文元数据、且常常没有标签**，中文查询因此天然搜不到它们（「科研绘图」匹配不了
`publication-ready figures`）。本包用 `tools/aliases.json` 在**构建期**为这些技能补上中文触发词
（如 `scientific-visualization` ← 科研绘图 / 绘图 / 图表；`statistical-analysis` ← 样本量 / 敏感性分析；
`venue-templates` ← 投稿），由 `rebuild.py` 合并进 `registry.json`——这样修复是持久的，
不会因为下一次重建覆盖上游目录而丢失。

⚠️ **检索只索引技能元数据**（名称 / 描述 / 功能 / 标签 / 分类），**不索引 `references/` 与 `assets/` 正文**。
因此只写在正文里的概念（如 `publication bias`）可能查不到——这是设计边界而非故障：
此时用 `category` 浏览该领域分类，或直接 `load` 语义相邻的技能（循证写作 → `clinical-decision-support`、`statistical-analysis`）。
若某个上游技能对中文查询反复搜不到，最干净的修法是往 `tools/aliases.json` 给它加一条中文别名，而不是改上游文件。

`query` 无命中时，先用 `category` 浏览，或换用更贴近上游命名的英文术语。

---

## 四、路由表（16 分类 / 314 子技能：上游 312 + 本包自研 2）

> 自研子技能（`origin: local`，位于 `local-skills/`）在表中以 **(自研)** 标出。

| 分类 | 数量 | 何时路由到这里 | 代表子技能 |
|---|---|---|---|
| `ml-training` | 52 | 训练/微调/量化/分布式/实验追踪 | deepspeed, axolotl, awq-quantization, colab-finetuning |
| `biology` | 44 | 单细胞、基因组、影像、临床决策 | anndata, biopython, bioimage-analysis, clinical-decision-support |
| `databases` | 32 | 查科学数据库（结构/序列/化合物/文献/临床） | alphafold-database, chembl-database, biorxiv-database, clinicaltrials-database |
| `llm-tools` | 31 | Agent 框架、向量库、多模态、提示工程 | dspy, crewai-multi-agent, chroma, clip |
| `chemistry` | 23 | 分子性质、对接、从头设计 | datamol, deepchem, diffdock, admet-prediction |
| `physics` | 23 | 天体物理、PDE、动力系统、量纲分析 | astropy, fluid-dynamics, bayesian-inference, dimensional-analysis |
| `coding` | 20 | 通用工程能力、EDA、优化、MATLAB | exploratory-data-analysis, matlab, multi-objective-optimization, arboreto |
| `research` | 19 | 科研方法论、假设生成、评审、**学术检索**、市场调研 | **unified-research-finder(自研)**, conducting-scientific-research, hypothesis-generation, peer-review, perplexity-search |
| `other` | 16 | 元能力：上下文/目标/交接/检查点/资源盘点 | context, goal, handoff, checkpoint, compact |
| `cloud-compute` | 11 | 租 GPU / 无服务器 / 多云编排 | modal-serverless-gpu, runpod-gpu-cloud, skypilot-multi-cloud-orchestration, lambda-gpu-cloud |
| `data-engineering` | 10 | 大数据帧、地理空间、数据集、格式转换 | polars, dask, geopandas, hugging-face-datasets |
| `writing` | 10 | 论文/海报/引用/文献综述/投稿 | ml-paper-writing, latex-posters, citation-management, literature-review |
| `ml-inference` | 9 | 推理服务、量化、可观测性 | serving-llms-vllm, llama-cpp, gguf-quantization, sglang |
| `visualization` | 9 | 科研绘图、示意图、DNA/蛋白图、**Meta 分析图件** | **meta-analysis-figures(自研)**, matplotlib, plotly, scientific-schematics, protein-diagram |
| `quantum` | 4 | 量子线路与模拟 | qiskit, cirq, pennylane, qutip |
| `document-parsing` | 1 | 文档解析 | liteparse |

---

## 五、执行协议

1. **判流程**：任务是长流程（写论文、完整分析管线）还是单点问题？长流程先 `workflow show <id>` 取编排定义。
2. **提关键词**：从任务里抽出领域词 + 动作词（如 `single-cell` + `integration`、`分子对接` + `打分`）。
3. **检索**：跑 `query`。命中不理想就换英文术语或加 `--category`。
4. **选 1–3 个**：只挑真正要用的。子技能之间常有明确分工（例如 `anndata` 管数据结构、`scanpy` 管分析流程）。
5. **载入**：`load <name>`。返回的 `Base directory` 就是该子技能的根，其 `scripts/`、`references/`、`assets/` 都在那里。
6. **执行**：严格按子技能正文的步骤走；需要跑脚本时，在该 `Base directory` 内用 Bash 运行。
   **子技能目录视为只读**——不要往里写文件；产物写到用户工作目录或临时目录。
7. **补外部工具**：任务需要触达外部系统（GitHub、云存储、托管 GPU、ELN）时，才走第六节的 MCP 流程。
8. **自检（可选）**：交付前沿用 `research` 类的 `peer-review` / `scholar-evaluation` 做一轮质量复核。

**委派**：当流程够长（多子技能串联，或需要读大量数据库）时，把子技能执行丢给子代理，只让主上下文接收结论。这样能避免把每个子技能的全文都堆进主上下文。

---

## 六、MCP 按需安装协议

**原则：用户不需要，就不装。** MCP 只在任务确实要触达外部系统时才引入。

```
dispatch.py mcp config                 # 先确认目标配置文件在哪
dispatch.py mcp list                   # 看有哪些、各自能读能写什么、有什么前置条件
dispatch.py mcp install <id>           # 生成方案：网络判定 + 镜像选择 + 配置片段
dispatch.py mcp install <id> --write   # 真正写入配置文件（自动备份原文件）
```

**配置文件位置**：默认 `<用户目录>/.workbuddy/mcp.json`。
若平台不同或想放别处，用环境变量 `OSD_MCP_CONFIG` 覆盖，或调用时加 `--config <路径>`：

```bash
# Windows (cmd)
set OSD_MCP_CONFIG=D:\ai\my-agent\mcp.json

# Windows (PowerShell) / macOS / Linux
$env:OSD_MCP_CONFIG = "D:\ai\my-agent\mcp.json"     # PowerShell
export OSD_MCP_CONFIG="$HOME/my-agent/mcp.json"     # bash
```

### 网络分流（按 IP 自动判定）

`mcp install` / `net` 会自动判定所在区域并选择下载源：

| | 中国大陆 | 国际 |
|---|---|---|
| 判定 | IP 地理位置返回 `CN`，或百度可达而 Google 不可达 | IP 非 CN，或 Google 可达且更快 |
| npm | `registry.npmmirror.com` | `registry.npmjs.org` |
| PyPI | `pypi.tuna.tsinghua.edu.cn` | `pypi.org` |
| GitHub | `ghfast.top/https://github.com` 代理 | `github.com` 直连 |
| Docker | `docker.m.daocloud.io` | `docker.io` |

判定失败时**保守默认中国大陆镜像**。可用环境变量 `OPENSCIENCE_REGION=CN|INTL` 强制覆盖。

### 七个连接器

| id | 名称 | 类型 | 状态 | 写操作 |
|---|---|---|---|---|
| `givemeanode` | GiveMeANode | 远程托管 | official_setup（★推荐，一键 OAuth） | GPU 资源增删、作业提交、存储上传删除 |
| `github` | GitHub | 远程托管 | official_setup | Issue/PR 变更、仓库与工作流改动 |
| `benchling` | Benchling | 远程（租户专属） | manual_review | 无 |
| `box` | Box | 远程托管 | official_setup | 文件/元数据、Hub、Doc Gen 变更 |
| `dropbox` | Dropbox | 本地进程 | manual_review（需固定 commit） | 无 |
| `s3` | Amazon S3 | 远程托管 | official_setup | IAM 允许时含 S3 变更 |
| `spss` | IBM SPSS Statistics | 本地进程（社区） | manual_review（需自装 SPSS） | 任意 SPSS 语法 / SPSS 内嵌 Python 执行 |

> **为什么选 `meteor0620/spss-mcp` 而不是 `Exekiel179/SPSS-MCP`**：前者用 pyreadstat 做 `.sav` 即时读写、
> 单个持久 SPSS 引擎跨调用保持数据集、工具面收敛（7 个），且仍在维护；后者的 `configure-claude`
> 会改写 Claude Code 专属的 `~/.claude.json`，不适配通用 `mcpServers` 模型，且已久未更新。
> 两者都只支持 Windows + 已装 SPSS，故一律登记为 `manual_review`，**不会自动克隆或安装**。
> `spss` 的配置命令含 `<安装目录>` 占位符——**本工具检测到占位符时会拒绝写入**，避免登记一个永远连不上的服务器。

**注意**：远程连接器只需登记 URL，**不涉及下载**，因此网络分流对它们不生效；网络分流只在本地进程类（如 Dropbox 的 git/uv 安装）和用户自定义 MCP 上起作用。

### 安装后的两步（缺一不可）

1. 写入 `mcpServers` 后，**不会自动激活**——必须到平台的连接器管理页对该服务器点「**信任**」/启用。
2. 点信任前，先核对它暴露的工具清单与 OAuth 授权范围。

---

## 七、安全边界

- **写操作默认关闭**。上游 catalog 中 `writes_enabled_by_catalog` 全为 `false`；任何写操作（创建/删除 GPU、改 Issue、动 S3、改文件）都必须先向用户说明再执行。
- **不代跑未审代码**。`manual_review` 类连接器（Benchling / Dropbox / SPSS）本包**不会**自动克隆或执行上游仓库——Dropbox 必须固定并审阅 commit 后手工登记；SPSS 需用户自装 SPSS 并替换配置里的真实路径。
- **不猜凭据、不存凭据**。Benchling 的租户地址需用户提供；OAuth 走浏览器回环，本包不接触 token 明文。
- **不预授权**。每次 MCP 工具调用都过一次权限边界；不要为了省事批量批准。
- **计费资源需显式确认**。GPU 类连接器在批准前先确认计费上限。
- `skills/` 子技能目录只读（重建会覆盖），要修上游内容走 `tools/patches/`；`local-skills/` 可直接编辑。整体以 Apache-2.0 分发，见 `LICENSE`、`NOTICE`、`ATTRIBUTION.md` 与 `THIRD-PARTY-NOTICES.md`。
- **注意**：子技能 frontmatter 里的 `license:` 字段描述的是**它所讲授的第三方库**的许可（如 `etetoolkit → GPL-3.0` 指 ETE 工具包），**不是**该技能或本仓库的许可声明；本包未内嵌任何 GPL/LGPL/CeCILL 源码。

---

## 八、目录结构

```
openscience-dispatcher/
├── SKILL.md            ← 本文件（调度协议）
├── dispatch.py         ← 检索引擎（list / category / query / load / mcp / net / workflow）
├── dispatch.cmd        ← Windows 启动器（自动探测 Python）
├── registry.json       ← 314 条子技能索引（名称/分类/描述/功能/标签/路径/origin）
├── workflows/          ← 端到端工作流定义（文件名即 id，无需登记）
│   └── sci-paper.md    ← 从零写 SCI 论文：10 阶段 + 门控 + 铁律 + 产物规范
├── skills/             ← 312 个**上游**子技能，按 16 分类分层（每次重建覆盖，勿手改）
│   └── <category>/<name>/{SKILL.md, scripts/, references/, assets/}
├── local-skills/       ← 2 个**本包自研**子技能（手动维护，重建不覆盖）
│   ├── research/unified-research-finder/    ← 学术搜索（PubMed / Google 学术 / 镜像 / 影响因子）
│   └── visualization/meta-analysis-figures/ ← 森林图 / 漏斗图 / PRISMA 2020 / 偏倚风险红绿灯
├── mcp/
│   ├── catalog.json    ← 7 个连接器元数据（转录自上游 catalog.ts + 社区 SPSS）
│   └── INSTALL.md      ← 安装与网络分流详解
├── tools/              ← 维护脚本
│   ├── rebuild.py      ← 重建 skills/ 与 registry.json（含 local-skills 合并 + 别名覆盖）
│   ├── aliases.json    ← 给英文元数据的上游技能补中文触发词
│   ├── patches/        ← 对上游 bug 的最小修复（重建后自动回填）
│   ├── gen_readme.py   ← 生成 README.md
│   ├── make_demo_figures.py ← 重建 README 效果图到 docs/figures/
│   └── sources.py      ← 源仓库映射（上游 / 自研 / MCP）
├── docs/figures/       ← README 顶部效果图（森林图 / 漏斗图 / PRISMA / RoB 2 / KM）
├── README.md
├── CHANGELOG.md
├── ATTRIBUTION.md           ← 署名与著作权人分布
├── THIRD-PARTY-NOTICES.md   ← 第三方作品清单（MIT / LPPL 等）
├── NOTICE
└── LICENSE                  ← Apache-2.0（上游）
```

子技能保持上游 `<分类>/<技能>/` 的原始分层，因此可以直接与上游做目录级 diff 或整目录替换。
**两类目录的维护方式不同**：`skills/` 每次重建都会被上游覆盖，要修就改 `tools/patches/`；
`local-skills/` 是自研内容，直接编辑即可。二者最终都汇入 `registry.json`。

---

## 九、失败与回退

| 情况 | 处理 |
|---|---|
| 提示找不到 Python | Windows 装 Python 3.8+ 并勾选 "Add python.exe to PATH"，或直接用 `dispatch.cmd` |
| 控制台中文乱码 | `dispatch.py` 已强制 UTF-8 输出；若仍乱码，在 cmd 先执行 `chcp 65001` |
| `query` 无命中 | 先 `category` 浏览；改用上游英文命名；再不行就承认超出子技能覆盖，用通用能力完成，不要硬套 |
| `load` 名称歧义 | 用返回的候选列表选精确名重试 |
| 脚本在子技能目录跑失败 | 读该子技能的 `references/` 找依赖与版本要求；缺依赖按第六节网络分流装 |
| MCP 连接失败 | `mcp install` 重跑看状态（`connected / disabled / failed / needs_auth / needs_client_registration`）；`needs_auth` 需完成 OAuth |
| 配置文件写错位置 | `mcp config` 查看实际路径；用 `OSD_MCP_CONFIG` 或 `--config` 指定 |
| 网络判定异常 | `OPENSCIENCE_REGION=CN|INTL` 强制覆盖后重试 |
| `workflow show` 找不到 id | 先跑 `workflow list` 看可用 id；工作流文件名即 id |
| 检索被无关技能占据前排 | 已按词边界 + 短语加权排序；仍不理想时用 `--category` 限定分类缩小范围 |
| 某个上游技能中文搜不到 | 上游元数据多为英文、常无标签；往 `tools/aliases.json` 给它加一条中文别名，再 `rebuild.py --no-copy` |
| 概念只写在子技能正文里、检索不到 | 检索只索引元数据；改用 `category` 浏览该领域，或直接 `load` 语义相邻技能 |
| 自研技能在重建后消失 | 确认它在 `local-skills/` 下且未被同名上游技能遮蔽；`rebuild.py` 会打印 local 合并条数 |
| `mcp install --write` 拒绝写入 | 配置里还有 `<...>` 占位符；先把路径换成真实值再登记 |
| 用户信息不全就想开写 | **停下来问**，一轮 ≤4 个问题；`sci-paper` 的 Stage 0 定义了"信息足够"的判据，禁止在信息不足时进入检索 |
| 工作流中途被打断 | 读项目目录下 `00-brief.md` 末尾的进度表，从第一个未完成阶段继续，不要从头重做 |
