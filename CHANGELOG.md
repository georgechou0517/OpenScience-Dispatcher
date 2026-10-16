# Changelog

## 1.4.1

**移除被合规拦下的那一个文件，并修掉一个会让按需下载全线失败的换行符缺陷。**

- **`pain_management_plan.tex` 已从仓库移除。** 这份上游 `treatment-plans` 模板含**具体阿片类处方
  剂量表**（Oxycodone 5 mg q6h、MME 阈值、纳洛酮共处方），源站的内容合规过滤拒绝提供
  （`HTTP 451`）——既取不回，也不宜随包分发。原先指向它的三个文件（`SKILL.md`、`README.md`、
  `scripts/generate_template.py`）已同步改掉：模板清单从 7 个减为 6 个，`generate_template.py`
  的模板表也移除了对应条目（否则 `--type pain_management` 会直接抛 `FileNotFoundError`）。
  清单随之 **1616 → 1615 个文件**，19.7 → 19.6 MB。
- **补丁层新增「移除」能力。** `tools/patches/remove.txt` 登记不得再分发的路径，
  `apply_patches.py` 在**打完补丁之后**删除它们。此前只能手工删，而 `skills/` 是上游逐字节拷贝，
  **下次重建就会把它悄悄带回来**。
- **修掉一个会让按需下载全线失败的缺陷。** 补丁脚本用 `Path.write_text` 落盘，Windows 下会把
  `\n` 静默改写成 `\r\n`。仓库以 `.gitattributes`（`* text=auto eol=lf`）统一按 LF 存储，
  而 `manifest.json` 记录的是**字节数**——两者一旦不一致，那批文件**每一个下载都会判为校验失败**。
  现已改为显式 `newline="\n"`，并在 `apply_patches.py` 里加了 CRLF 告警。
- **修正一处平台门槛的误记。** 此前按「200 文件 / 解压 10 MB」准备投稿，那是**龙蜥 SkillHub**
  （skillhub.openanolis.cn）的规则。**腾讯 skillhub.cn** 是「单次上传 ≤ 10 MB、建议 ≤ 200 个文件」；
  **clawhub** 官方文档只给「总包 ≤ 50 MB」，**没有文件数上限**（见 `docs.openclaw.ai/clawhub/skill-format`）。
  体积门槛三家都满足；真正需要留意的是 clawhub 强制 **MIT-0**、且元数据声明必须与实际行为一致。
- 顺带修掉 `apply_patches.py` 的一处隐患：跳过规则原本按**文件名**匹配，会把上游真正的
  `README.md` 补丁一并跳过；现改为按**相对路径**匹配。
- 验证：全部 1615 个文件在「工作区字节数」与「提交后 blob 字节数」两个口径下都与清单一致
  （4 个 `.pdf` 被 git 判为二进制、不参与归一，已单独核对）；检索排序与 v1.3.1 仍逐条一致。

## 1.4.0

**按需下载**：把 312 个上游子技能从包体里挪出去，改为用到时才从 Gitee 拉取——使本包得以通过
skillhub / clawhub 的投稿门槛（单包上限 **200 个文件 / 解压 10 MB**）。

- **投稿包瘦身到 51 文件 / 解压 1.5 MB**（此前 1665 文件 / 21 MB，两条硬门槛全部超出）。
  包内只留索引 `registry.json` 与新增的文件清单 `manifest.json`；两套发行形态由
  `tools/package.py` 一次产出：精简包（扁平根目录、不含 `skills/`，用于投稿）与全量包
  （1667 文件 / 21 MB，用于自用与离线）。
- **新增 `manifest.json`**：312 个上游子技能逐个记录「由哪些文件组成、各多大」，另附 Gitee 源信息。
  由 `tools/rebuild.py` 在**打完补丁之后**生成——顺序很重要，否则补丁过的文件字节数会被记错，
  每一个下载都会被判为校验失败。
- `dispatch.py` 新增三条命令：`status`（随包 / 已下载 / 未下载规模）、`plan`（**离线**预估文件数
  与体积，不联网、不写盘）、`fetch`（从 Gitee raw 逐文件下载，并发 6、失败重试 3 次、按字节数
  校验、可断点续传）。
- **先问再下**：`fetch` 不加 `--yes` **永远只打印计划，一个字节都不写**；`load` 遇到未下载的
  子技能会返回**退出码 4** 并打印下载指引。包自带的 2 个自研技能不受影响，始终开箱即用。
- **源只有一个**：`https://gitee.com/georgechou17/open-science-dispatcher` 的 raw 端点，逐文件
  直连，不需要 git、不需要令牌；可用 `OSD_SOURCE_HOME` / `OSD_SOURCE_REF` 指向 fork 或镜像。
- `workflows/sci-paper.md` 顶部新增 `requires:` 清单，`fetch --workflow sci-paper` 据此一次拉齐该
  工作流真正需要的 18 个上游子技能（122 个文件 / 18 秒），而不是全量 19.7 MB。
- **区分「网络失败」与「源站合规拦截」**：全量 1616 个文件里有 1 个——上游 `treatment-plans` 的
  `assets/pain_management_plan.tex`（内容是具体的阿片类处方剂量表）——被 Gitee 的内容合规过滤
  拒绝（`HTTP 451`）。`fetch` 把这一类单列并返回**退出码 5**（退出码 1 只代表网络 / 校验失败）。
  本工具**不会**用其它途径绕过平台的合规判断；受影响的子技能仍可用，只是少这一个资源文件。
- README（由 `tools/gen_readme.py` 模板重新生成）与 `SKILL.md` 均已按新模型改写。
- 验证：检索排序与 v1.3.1 **逐条一致**（35 条中文查询基线零回归）；按需拉取实测 312 个技能 /
  1616 个文件全部逐字节校验通过（唯一例外即上一条被拦截的文件）。

## 1.3.1

README 顶部新增**图表效果画廊**，把「科研图表绘制」这一主打直接亮出来。

- 新增 `docs/figures/`：森林图、漏斗图、PRISMA 2020 流程图、偏倚风险红绿灯图（RoB 2）
  与 Kaplan-Meier 生存曲线共 5 张效果图，全部由脚本从数据文件生成（PDF + PNG、300 dpi、
  字体嵌入、色盲友好配色），是真实出图而非示意图或贴图。
- 新增 `tools/make_demo_figures.py`：一条命令重建这 5 张图，保证图与 README 同步；
  生存曲线面板用固定随机种子合成演示队列，不携带任何真实患者数据。
- 图中所用为示例数据，README 已显著标注「仅用于展示出图效果」。
- README 安装目录树与 `SKILL.md` 目录结构同步补上 `docs/figures/` 与生成脚本。

## 1.3.0

新增**本地技能层**与两项自研能力，接入学术搜索与 SPSS，并系统性修复中文检索。

- **新增 `local-skills/` 本地技能层**：本包自研技能放这里，`rebuild.py` 只把它们并入
  `registry.json`（标 `origin: local`），**绝不覆盖**——与 `tools/patches/`（修上游 bug）
  职责分离：一个装自己的东西，一个补上游的东西。
- **自研技能 `unified-research-finder`**（research）：整合学术搜索技能，覆盖 PubMed 官方
  E-utilities（真实 PMID / 摘要 / DOI）与 Google 学术及其镜像站（灯塔 / 烂番薯 / KipHub /
  学术搜索Pro / 香港镜像），按优先级自动回退，另提供影响因子与引用查询。**找不到就是找不到，
  绝不编造。** 已设为 `sci-paper` Stage 1/2 的**首选检索**。
- **自研技能 `meta-analysis-figures`**（visualization）：补齐上游只提供底层 matplotlib 的空档，
  用可复现脚本从 CSV / 计数直接产出**森林图、漏斗图、PRISMA 2020 流程图、偏倚风险红绿灯图**
  （RoB 2 / ROBINS-I），内置数值一致性校验（置信区间填反、点估计越界、计数自相矛盾时拒绝出图）。
  已设为 `sci-paper` Stage 6 的**首选出图**。
- **新增第 7 个 MCP 连接器 `spss`**（社区 `meteor0620/spss-mcp`，`manual_review`）：
  在 `catalog.json` 中记录了选型理由（对比 `Exekiel179/SPSS-MCP`：pyreadstat 即时读写、
  单引擎持久会话、工具面收敛、仍在维护；后者的 `configure-claude` 改写 Claude Code 专属
  `~/.claude.json`，不适配通用 `mcpServers`）。**新增占位符守卫**：配置里还有 `<...>` 时
  `mcp install --write` 直接拒绝写入，避免登记一个永远连不上的服务器。
- **检索修复（四项）**：
  1. `rebuild.py` 的 frontmatter 解析器此前会把 `description: >-` 这类**折叠标量截断在第一行**，
     静默掏空该技能的检索索引（本包自研技能正用这种写法）——已支持 `>` / `|` / `>-` / `|-` 等；
  2. 中文**标签**改为分档计分：技能自己声明的中文标签权重最高，仅作为更长标签**子串**命中时
     权重很低（中文没有词边界，否则「文献」会误命中「文献综述」，把自研检索技能挤到第二）；
  3. 新增 `tools/aliases.json` + `rebuild.py` 别名合并：上游技能多为英文元数据、常常无标签，
     中文查询天然搜不到，构建期为它们补中文触发词（`scientific-visualization` ← 科研绘图 / 绘图 /
     图表；`statistical-analysis` ← 样本量 / 敏感性分析；`venue-templates` ← 投稿）；
  4. 展开出的英文**短语**按特异性折扣，避免单个翻译词把自研技能顶掉。
- 计数更新：**312 → 314** 个技能（上游 312 + 自研 2），**6 → 7** 个 MCP；`SKILL.md` / `README.md`
  / 路由表 / 目录结构同步更新，`sci-paper` 的检索与出图阶段改指自研技能。

## 1.2.1

修复上游生存分析脚本的五个缺陷，并新增本地补丁层防止重建时被覆盖。

对 `generate_survival_analysis.py`（Kaplan-Meier 报告生成器）实测发现：**在当前 lifelines 上
直接崩溃**，且即使不崩溃也会输出经不起审稿的数值。已全部修复：

1. **崩溃**：置信区间列名硬编码为 `KM_estimate_lower_0.95`，但 lifelines 一旦收到 `label=`
   就会把列名改成 `<组名>_lower_0.95`，任何带标签的拟合都 `KeyError`。改为按子串动态取列。
2. **方法学错误**：中位生存期的置信区间取自**生存概率**的置信带，于是打印出
   `16.7 months (95% CI 0.4-0.6)`——把概率区间标成了月份。改为 Brookmeyer-Crowley 构造
   （置信带与 S(t)=0.5 的交叉时间），现输出 `16.7 months (95% CI 10.3-24.3)`。
3. **参数失效**：`generate_report()` 硬编码标题，导致 `-t/-x/-y/--time-col/--event-col/--group-col`
   全部被静默忽略。已透传；`patient_id` 也不再是必需列（下游从不使用）。
4. **表述错误**：效应量对两个方向都用 `(1 - hr)`，HR=1.48 被写成
   `Control has -48% increase in risk`。已按方向分支修正为 `48% increase in risk`。
5. **观感缺陷**：log-rank p 值画在 `(0.02, 0.15)`，被左下图例遮住，已移至 `(0.02, 0.97)`。

- 新增 `tools/patches/` + `tools/apply_patches.py`：`skills/` 是上游树的逐字节拷贝，
  直接修 `skills/` 会在下次 `rebuild.py` 被覆盖；补丁层保存修正版并按相对路径回写。
  `rebuild.py` 现于重建末尾自动调用它（`--no-copy` 时跳过）。
- 新增 `tools/patches/README.md`：记录每个补丁的缺陷、症状与修法。

## 1.2.0

新增端到端工作流层，主打「从零写一篇 SCI 论文」。

- 新增 `workflows/sci-paper.md`：面向零科研基础的本科生，十阶段（信息采集 → 可行性查证 → 检索 →
  PRISMA 筛选 → 数据提取 → 统计 → 图表 → 英文稿 → 反造假审计 → 投稿准备），
  每阶段定义准入条件、要调用的子技能、产物文件与门控；含分轮提问设计（每轮 ≤4 问）与"信息足够"判据。
- 明确六条铁律：绝不编造文献、绝不编造数据、先查证再动笔、全程留痕、每步说人话、不确定就问。
- `dispatch.py` 新增 `workflow list` / `workflow show <id>` 子命令；工作流文件名即 id，无需额外登记。
- 检索质量修复：打分由裸子串改为**词边界匹配**（`meta` 不再命中 `metabolomics`）；
  中文术语展开补入循证与临床术语（系统综述、荟萃分析、发表偏倚、森林图等），
  并对展开出的英文**短语**整体命中加权——「meta 分析」现正确命中 `literature-review` 而非 `*-analysis`。
- `SKILL.md` 由三层调度模型扩为**四层**（新增 workflow orchestration 层），
  并补检索边界说明（只索引元数据，不索引 `references/` 正文）。
- `README.md` 增补主打工作流说明与 `workflow` 命令示例。

## 1.1.0

README 重写与许可补全。

- 重写 `README.md`：科研困境 → 能力场景 → 规模 → **312 技能 + 6 MCP 全清单（含源仓库链接）** → 致谢 → 许可，
  并附安装、命令与设计说明；中英双语、锚点互跳。
- 新增 `tools/sources.py`：312 个 Skill 与 6 个 MCP 的源仓库映射（243 个第三方项目 + 69 个 OpenScience 自研），
  全部链接经 HTTP 可用性校验。
- 新增 `tools/gen_readme.py`：从 `registry.json` + `tools/sources.py` 生成 README，清单可复现、不会手工漂移。
- 许可补全：调度层源文件（`dispatch.py`、`dispatch.cmd`、`tools/*.py`）加
  `SPDX-License-Identifier: Apache-2.0` 头；`SKILL.md` 补 `license: Apache-2.0`；
  `ATTRIBUTION.md` 补入 `tools/` 文件清单。

## 1.0.1

许可合规补全。基于 OpenScience 2.0.66。

- 新增 `THIRD-PARTY-NOTICES.md`：逐项列出随包分发的第三方作品，补齐上游 `NOTICE` 未披露的部分。
  - 312 篇子技能的著作权人分布确认为 6 方：Synthetic Sciences 130、无 `skill-author` 166、
    Shoko-official 2（Apache-2.0，共 298）；InkVell Inc. 12、Microsoft 1、Andrey Fedorov 1
    （MIT，共 14）。
  - 记录 `skills/writing/ml-paper-writing/templates/` 内打包的第三方 LaTeX 宏包：
    natbib、fancyhdr、四个会议 `.bst` 为 **LPPL**；`algorithm.sty` / `algorithmic.sty`
    文件内无许可声明，CTAN 按 **LGPL** 分发。**本仓库未附带 `lppl.txt`**，已在文件中标注补齐方法。
  - 记录六套会议模板（AAAI / ACL / COLM / ICLR / ICML / NeurIPS）与
    KEGG / HMDB / DrugBank / NCI IDC 等数据源的使用条款。
- 重写 `ATTRIBUTION.md`：修正原文「子技能均为 Synthetic Sciences 作品」的错误表述，
  补入 InkVell Inc.、Microsoft、Andrey Fedorov、Shoko-official 四个著作权人；
  新增「`license:` frontmatter 字段语义」说明（该字段描述所授库的许可，非文档自身许可）。
- `README.md`：许可章节改写为中英双语完整版本，目录树补入 `THIRD-PARTY-NOTICES.md`。
- 清单交付物：CSV 与 HTML 的「许可证」列更名为「**所授库许可**」，并在页首加注说明语义，
  避免下游把 `etetoolkit → GPL-3.0` 误读为技能自身许可。

## 1.0.0

首个版本。基于 OpenScience 2.0.66。

- 打包 312 个科研子技能（16 分类）与 6 个 MCP 连接器元数据。
- `dispatch.py` 检索引擎：`list` / `category` / `query` / `load` / `mcp` / `net`，零第三方依赖。
- `query` 支持中文术语展开后打分，复刻上游 `skill` 工具的名称/标签/描述/功能/分类加权语义。
- `mcp install` 按 IP 自动在中国大陆镜像站与国际站之间选择下载源，默认只打印方案。
- MCP 配置文件路径可通过 `OSD_MCP_CONFIG` 或 `--config` 覆盖，写入前自动备份。
- 无绝对路径、无机器相关假设；Windows 10+ / macOS / Linux 通用，附 `dispatch.cmd` 启动器。
- 保留上游 Apache-2.0 `LICENSE`、`NOTICE` 与 `ATTRIBUTION.md`。
- `tools/rebuild.py` 可从上游仓库重建 `skills/` 与 `registry.json`。
