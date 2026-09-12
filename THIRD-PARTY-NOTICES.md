# Third-Party Notices

[English](#english) · [中文摘要](#中文摘要)

This file supplements the upstream [`NOTICE`](NOTICE) and [`LICENSE`](LICENSE). It records
every third-party work bundled in this repository, its copyright holder, and the license under
which it is redistributed.

It exists because the upstream `NOTICE` does not enumerate all of them — in particular the
LaTeX support packages under `skills/writing/ml-paper-writing/templates/` and the sub-skills
authored by InkVell Inc. and Andrey Fedorov.

---

<a id="english"></a>

## English

> This English text is authoritative. A Chinese summary follows for convenience.

### 1. How to read the `license:` frontmatter field

Each sub-skill under `skills/` carries a YAML frontmatter block. The `license:` field in that
block describes **the third-party library or service that the skill teaches the agent to use**.
It is *not* the license of the document itself.

For example, `skills/biology/etetoolkit/SKILL.md` declares `license: GPL-3.0 license`, because
the ETE toolkit is GPL-3.0. No ETE source code is bundled here — the document only describes how
to call it, and the accompanying helper scripts merely `import ete3` at runtime.

The copyright holder of the **document** is recorded separately, in `metadata.skill-author`.

### 2. Copyright holders of the bundled sub-skills

`skills/` contains 312 sub-skill documents copied verbatim from OpenScience 2.0.66. They are not
the work of a single author.

| Copyright holder | Sub-skills | License |
|---|---:|---|
| Synthetic Sciences | 130 | Apache-2.0 |
| *(no `skill-author` recorded — upstream default applies)* | 166 | Apache-2.0 |
| Shoko-official | 2 | Apache-2.0 |
| InkVell Inc. | 12 | MIT |
| Microsoft Corporation (`markitdown`) | 1 | MIT |
| Andrey Fedorov | 1 | MIT |
| **Total** | **312** | |

**Subtotals: Apache-2.0 = 298 · MIT = 14.**

The counts above cover the 312 upstream sub-skills under `skills/` only. The 2 sub-skills
added by this package under `local-skills/` are original work (not third-party): see
[`ATTRIBUTION.md`](ATTRIBUTION.md) for their licenses (Apache-2.0 and MIT-0).

All Apache-2.0 content is covered by the root [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

### 3. MIT-licensed sub-skills — copyright notice required

The MIT License requires that the copyright notice and permission notice be retained in all
copies. The following 14 sub-skills are MIT-licensed; their authorship is recorded in each
file's `metadata.skill-author` field.

**InkVell Inc. (12)**

```
skills/biology/bioimage-analysis
skills/biology/cancer-genomics-analysis
skills/biology/clinical-imaging
skills/biology/curated-bio-datasets
skills/biology/flow-cytometry-analysis
skills/biology/glycobiology
skills/biology/immunology-assays
skills/biology/microbial-dynamics
skills/biology/molecular-cloning
skills/biology/pharmacology-wetlab
skills/biology/synthetic-biology
skills/other/skill-installer
```

**Andrey Fedorov (1)**

```
skills/databases/imaging-data-commons
```

> The skill document is MIT. The NCI Imaging Data Commons **data** it queries carries separate
> per-collection licensing (mostly CC-BY, some CC-NC) that must be respected independently.

**Microsoft Corporation (1)**

```
skills/data-engineering/markitdown
```

> Bundles Microsoft's `markitdown` under the MIT License. The full license text ships as
> `skills/data-engineering/markitdown/LICENSE.txt`.

### 4. Third-party LaTeX packages under `skills/writing/ml-paper-writing/templates/`

These are **not** OpenScience works. They are LaTeX support files redistributed as part of the
paper templates.

| File | Copyright | License |
|---|---|---|
| `colm2025/natbib.sty` | Patrick W Daly, 1993–2009 | LPPL v1.0 or later |
| `iclr2026/natbib.sty` | Patrick W Daly, 1993–2009 | LPPL v1.0 or later |
| `colm2025/fancyhdr.sty` | Piet van Oostrum, v3.2 | LPPL v1.0 or later |
| `iclr2026/fancyhdr.sty` | Piet van Oostrum | LPPL v1.0 or later |
| `icml2026/fancyhdr.sty` | Pieter van Oostrum, 1994–2025, v1.3+ | LPPL v1.3 or later |
| `acl/acl_natbib.bst` | Norman Gray (`urlbst` 0.9.1), 2002–23 | LPPL v1.0 or later |
| `colm2025/colm2025_conference.bst` | Hal Daumé III, 2010; Patrick W Daly, 1993–2007 | LPPL v1.0 or later |
| `iclr2026/iclr2026_conference.bst` | Hal Daumé III, 2010; Patrick W Daly, 1993–2007 | LPPL v1.0 or later |
| `icml2026/icml2026.bst` | Hal Daumé III, 2010; Patrick W Daly, 1993–2007 | LPPL v1.0 or later |
| `icml2026/algorithm.sty` | Peter Williams, 1994 | No license statement in file; distributed by CTAN under the LGPL |
| `icml2026/algorithmic.sty` | Peter Williams, 1994; modified by Alex Smola, 2000 | No license statement in file; distributed by CTAN under the LGPL |

**LPPL compliance — action required if you redistribute.** The LaTeX Project Public License
requires that a copy of the license be available to recipients. **This repository does not ship
`lppl.txt`.** Obtain it from CTAN at `macros/latex/base/lppl.txt` (or
<https://www.latex-project.org/lppl.txt>) and ship it alongside this bundle. The LPPL also
requires that modified files be renamed — do not modify these files in place under their
original names.

### 5. Conference paper templates

The template directories are distributed by their respective venues for preparing submissions:

```
skills/writing/ml-paper-writing/templates/aaai2026/     AAAI 2026
skills/writing/ml-paper-writing/templates/acl/          *ACL (ACL Rolling Review)
skills/writing/ml-paper-writing/templates/colm2025/     COLM 2025
skills/writing/ml-paper-writing/templates/iclr2026/     ICLR 2026
skills/writing/ml-paper-writing/templates/icml2026/     ICML 2026
skills/writing/ml-paper-writing/templates/neurips2025/  NeurIPS 2025
```

Each venue's template carries its own terms of use. Consult the venue before using them for
anything beyond preparing a submission to that venue.

### 6. Data sources referenced (not redistributed)

No data from the following sources is redistributed here. Each is governed by its own terms, and
users are responsible for compliance:

- **KEGG** — non-academic use requires a commercial license.
- **HMDB** — commercial use and redistribution require explicit permission and citation.
- **DrugBank** — commercial use requires a license.
- **NCI Imaging Data Commons** — per-collection licensing, partly CC-BY, partly CC-NC.
- **UniProt, RCSB PDB, PDBe, AlphaFold DB, Ensembl, NCBI (E-utilities, ClinVar, GEO), ChEMBL,
  PubChem, Reactome, STRING, Open Targets, OpenAlex, Crossref, arXiv, bioRxiv** and others —
  public APIs, each with its own terms of use.

### 7. No copyleft source code is bundled

Several sub-skills document GPL-2.0, GPL-3.0 or CeCILL-licensed libraries — for example
`biology/etetoolkit`, `biology/cobrapy`, `biology/scikit-survival`, `biology/pathml` and
`physics/fluidsim`. Only documentation, plus small helper scripts authored by the upstream
project, is bundled. Those scripts `import` the libraries at runtime and embed none of their
source code. No GPL, LGPL or CeCILL source code is redistributed in this repository, and no
copyleft obligation attaches to the bundle as a whole.

---

<a id="中文摘要"></a>

## 中文摘要

> 以下内容为方便阅读而提供，**以英文版为准**。

1. **子技能 frontmatter 里的 `license:` 字段**描述的是「该技能所教的第三方库」的许可，
   **不是文档自身的许可**。文档的著作权人记在 `metadata.skill-author` 字段里。

2. **312 篇子技能分属 6 个著作权人**：Synthetic Sciences 130 篇、未记 author 的 166 篇
   （按上游仓库默认）、Shoko-official 2 篇 —— 合计 **Apache-2.0 共 298 篇**；
   InkVell Inc. 12 篇、Microsoft 1 篇、Andrey Fedorov 1 篇 —— 合计 **MIT 共 14 篇**。
   MIT 部分要求随附版权声明，其作者已记在各文件 frontmatter 中。
   （以上仅计 `skills/` 下的 312 篇上游子技能；`local-skills/` 下另 2 篇为本包原创，
   非第三方作品，其许可见 [`ATTRIBUTION.md`](ATTRIBUTION.md)。）

3. **`skills/writing/ml-paper-writing/templates/` 内打包了第三方 LaTeX 宏包**，其中
   natbib、fancyhdr 及四个会议 `.bst` 均为 **LPPL** 授权；`algorithm.sty` 与
   `algorithmic.sty`（Peter Williams, 1994）文件内**没有许可声明**，CTAN 按 **LGPL** 分发。
   **本仓库未附带 `lppl.txt`** —— 再分发时需自行从 CTAN 补齐许可全文。

4. **六套会议模板**（AAAI / ACL / COLM / ICLR / ICML / NeurIPS）各有馆方条款，
   超出「准备投稿」用途前请查阅各馆方规定。

5. **KEGG / HMDB / DrugBank / NCI IDC 等数据源未被再分发**，但各有使用条款
   （KEGG 非学术用途需商业授权、HMDB 商业再分发需授权、IDC 含 CC-NC 集合），
   使用者需自行遵守。

6. **本包未内嵌任何 GPL / LGPL / CeCILL 源代码**，因此 copyleft 义务不附着于整体。
