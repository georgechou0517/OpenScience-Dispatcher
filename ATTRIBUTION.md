# Attribution

[English](#english) · [中文](#中文)

---

<a id="english"></a>

## English

### Bundled content — not original to this project

`skills/` and most of `mcp/catalog.json` come from the **OpenScience** project.

- Project: OpenScience
- Source: https://github.com/synthetic-sciences/openscience
- Version bundled: 2.0.66
- Sub-skills: 312 (16 categories)
- MCP connector catalog entries: 6 transcribed from `backend/cli/src/mcp/catalog.ts`, plus 1 community entry (`spss`) added by this package

Two further sub-skills under `local-skills/` are **not** OpenScience content — see
"Original to this project" below.

> **Two distribution shapes.** `openscience-dispatcher-full.zip` contains everything described below;
> `openscience-dispatcher-skill.zip` — the build published to skillhub / clawhub — **omits `skills/`
> entirely** (51 files) and instead ships `manifest.json`, the file inventory that
> `dispatch.py fetch` uses to pull individual sub-skills from the Gitee repository on demand.
> Every upstream sub-skill is therefore still distributed under the terms below; the slim build
> simply does not carry the files until they are fetched.

The bundled sub-skills are **not the work of a single author**. Copyright holders:

| Copyright holder | Sub-skills | License |
|---|---:|---|
| Synthetic Sciences | 130 | Apache-2.0 |
| *(no `skill-author` recorded — upstream default applies)* | 166 | Apache-2.0 |
| Shoko-official | 2 | Apache-2.0 |
| InkVell Inc. | 12 | MIT |
| Microsoft Corporation (`markitdown`) | 1 | MIT |
| Andrey Fedorov | 1 | MIT |
| **Total** | **312** | |

Apache-2.0 content is covered by [`LICENSE`](LICENSE.md) and [`NOTICE`](NOTICE.md). The MIT portion,
plus the third-party LaTeX packages bundled with the paper templates, are itemised in
[`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).

### Original to this project

The dispatcher layer — `SKILL.md`, `dispatch.py`, `dispatch.cmd`, `registry.json`,
`manifest.json`, `mcp/INSTALL.md`, `tools/rebuild.py`, `tools/gen_readme.py`, `tools/sources.py`,
`tools/aliases.json`, `tools/package.py`, `tools/make_demo_figures.py`,
`README.md`, `CHANGELOG.md` — is original work,
distributed under the same Apache-2.0 terms as the bundle it ships with.
Every dispatcher-layer source file carries an `SPDX-License-Identifier: Apache-2.0` header.

Two bundled sub-skills under `local-skills/` are also original to this project:
`visualization/meta-analysis-figures` (Apache-2.0) and `research/unified-research-finder`
(an MIT-0 copy of the author's own standalone project — see its `LICENSE.md`).

### A note on the `license:` frontmatter field

Each sub-skill records a `license:` value in its YAML frontmatter. This field describes **the
third-party library that the sub-skill documents**, not the license of the document itself. For
example `biology/etetoolkit/SKILL.md` reads `license: GPL-3.0 license` because the ETE toolkit
is GPL-3.0; no ETE source code is bundled, and the document itself is Apache-2.0. The document's
own copyright holder is recorded in `metadata.skill-author`.

Do not read these values as license declarations for this repository. See
[`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) § 1 and § 7.

---

<a id="中文"></a>

## 中文

### 随包内容 —— 非本项目原创

`skills/` 与 `mcp/catalog.json` 的绝大部分来自 **OpenScience** 项目。

- 项目：OpenScience
- 来源：https://github.com/synthetic-sciences/openscience
- 打包版本：2.0.66
- 子技能：312 篇（16 个分类）
- MCP 连接器目录条目：6 条转录自 `backend/cli/src/mcp/catalog.ts`，另 1 条社区条目（`spss`）为本包新增

`local-skills/` 下另有 2 篇子技能**不属于 OpenScience**，见下方「本项目原创」。

> **两种发行形态。** `openscience-dispatcher-full.zip` 含下述全部内容；
> 投稿 skillhub / clawhub 用的 `openscience-dispatcher-skill.zip` **完全不含 `skills/`**（共 51 个文件），
> 代之以 `manifest.json`（文件清单），由 `dispatch.py fetch` 按需从 Gitee 仓库逐个取回子技能。
> 也就是说上游每一篇子技能仍然按下方条款分发，只是精简包在取回之前不携带这些文件。

子技能**并非单一作者的作品**，著作权人分布：

| 著作权人 | 子技能 | 许可 |
|---|---:|---|
| Synthetic Sciences | 130 | Apache-2.0 |
| （未记录 `skill-author`，按上游默认） | 166 | Apache-2.0 |
| Shoko-official | 2 | Apache-2.0 |
| InkVell Inc. | 12 | MIT |
| Microsoft Corporation（`markitdown`） | 1 | MIT |
| Andrey Fedorov | 1 | MIT |
| **合计** | **312** | |

Apache-2.0 部分见 [`LICENSE`](LICENSE.md) 与 [`NOTICE`](NOTICE.md)；MIT 部分及随论文模板打包的
第三方 LaTeX 宏包，逐项列于 [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md)。

### 本项目原创部分

调度层 —— `SKILL.md`、`dispatch.py`、`dispatch.cmd`、`registry.json`、`manifest.json`、
`mcp/INSTALL.md`、`tools/rebuild.py`、`tools/gen_readme.py`、`tools/sources.py`、
`tools/aliases.json`、`tools/package.py`、`tools/make_demo_figures.py`、
`README.md`、`CHANGELOG.md`
—— 为本项目原创，与随包内容一致地以
Apache-2.0 分发。调度层每个源文件均带 `SPDX-License-Identifier: Apache-2.0` 头。

`local-skills/` 下的 2 篇子技能同样为本项目原创：`visualization/meta-analysis-figures`
（Apache-2.0）与 `research/unified-research-finder`（作者本人独立项目的 MIT-0 副本，
许可见其自带 `LICENSE.md`）。

### 关于 frontmatter 里的 `license:` 字段

每篇子技能的 YAML frontmatter 都带一个 `license:` 值。该字段描述的是
**该子技能所讲授的第三方库**的许可，**不是文档自身的许可**。例如
`biology/etetoolkit/SKILL.md` 写着 `license: GPL-3.0 license`，那是因为 ETE 工具包是
GPL-3.0；本包未内嵌任何 ETE 源码，而该文档本身是 Apache-2.0。文档的著作权人记在
`metadata.skill-author` 中。

**请勿**把这些值当作本仓库的许可声明。详见
[`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) 第 1 节与第 7 节。
