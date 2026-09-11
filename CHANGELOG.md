# Changelog

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
