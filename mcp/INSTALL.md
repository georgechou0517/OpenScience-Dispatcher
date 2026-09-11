# MCP 连接器安装指南

本目录的 `catalog.json` 是上游 OpenScience `backend/cli/src/mcp/catalog.ts` 的完整转录：
6 个连接器、读写能力、安全说明、前置条件。**全部默认禁用**，`writes_enabled_by_catalog` 均为 `false`。

## 使用方式

在包根目录执行（Windows 可用 `dispatch.cmd` 代替 `python dispatch.py`）：

```bash
python dispatch.py mcp config                 # 查看目标配置文件的实际路径
python dispatch.py mcp list                   # 看清单与前置要求
python dispatch.py mcp show github            # 看单个连接器完整元数据
python dispatch.py mcp install github         # 生成安装方案（只打印，不落盘）
python dispatch.py mcp install github --write # 写入配置文件（自动备份）
python dispatch.py net                        # 只看网络区域判定与镜像映射
```

## 配置文件位置

默认写入 `<用户目录>/.workbuddy/mcp.json`。不同平台的 Agent 客户端路径不同，用任一方式覆盖：

| 方式 | 写法 |
|---|---|
| 环境变量 | `OSD_MCP_CONFIG=<路径>` |
| 命令行 | `dispatch.py mcp install <id> --write --config <路径>` |
| 查询当前值 | `dispatch.py mcp config` |

```bash
# Windows (cmd)
set OSD_MCP_CONFIG=D:\ai\my-agent\mcp.json

# PowerShell
$env:OSD_MCP_CONFIG = "D:\ai\my-agent\mcp.json"

# macOS / Linux
export OSD_MCP_CONFIG="$HOME/my-agent/mcp.json"
```

写入前会自动把原文件备份为 `<文件名>.bak-<时间戳>`。

## 网络分流

安装前先判定用户所在区域，再决定下载源。判定顺序：

1. 环境变量 `OPENSCIENCE_REGION`（`CN` / `INTL`）——优先级最高，用于人工覆盖
2. IP 地理位置 API：`ipapi.co` → `ip-api.com` → `ipinfo.io`，返回 `country_code == CN` 即判为中国大陆
3. 延迟探测兜底：百度可达而 Google 不可达 → 中国大陆；Google 可达且更快 → 国际
4. 全部失败 → **保守默认中国大陆镜像**（对大陆用户更友好）

| 资源 | 中国大陆 | 国际 |
|---|---|---|
| npm registry | `https://registry.npmmirror.com` | `https://registry.npmjs.org` |
| PyPI index | `https://pypi.tuna.tsinghua.edu.cn/simple` | `https://pypi.org/simple` |
| GitHub | `https://ghfast.top/https://github.com` | `https://github.com` |
| Docker registry | `https://docker.m.daocloud.io` | `https://docker.io` |

> 本 catalog 中的 5 个 `remote` 连接器（givemeanode / github / box / s3，以及租户态的 benchling）
> **只登记 URL，不下载任何东西**，因此网络分流对它们不产生效果。
> 分流实际作用于：Dropbox 的本地进程安装、以及用户后续自行添加的 local MCP。

## 权威提示：先读 upstream 的 reviewed_at 与 safety

每个连接器的 `reviewed_at` 是上游最后一次人工审阅日期，`safety` 是当时的结论。
引入前请重新核对 `source_url` 上的官方文档——上游明确表示**不对任何服务端做"只读"背书**，
所有写能力都保留在服务端，调用时仍要过一次权限边界。

## 三个特殊情形

**Benchling（manual_review）** — 端点是租户专属，本包不会猜测或存储你的租户地址。
需管理员在 Benchling 开启 Benchling Chat 与 MCP、启用 V3 API，再把
`https://<tenant>.mcp.benchling.com/mcp` 中的 `<tenant>` 换成真实值。

**Dropbox（manual_review）** — 上游只发布源码仓库、不提供托管端点。
上游明确拒绝"克隆并执行活动分支"，因此必须：固定并审阅一个 commit → 用只读作用域创建 Dropbox 应用 →
安装依赖（按上表选源）→ 手工登记确切的本地启动命令。

**Amazon S3** — 该端点覆盖面**大于** S3（是整个 AWS MCP），必须用最小权限 IAM 身份接入；
CloudTrail 才是权威的外部审计日志。

## 写入后的必做两步

1. 配置写入 `mcpServers` 后**不会自动生效**，需在平台的连接器管理页
   （或自定义连接器入口）对该服务器点「**信任**」/启用。
2. 点信任前，核对它暴露的工具清单与 OAuth 授权范围；不要批量预授权。

## 手工登记格式参考

远程托管（HTTP）：

```json
{
  "mcpServers": {
    "github": { "type": "http", "url": "https://api.githubcopilot.com/mcp/" }
  }
}
```

若客户端不识别 `type: http`，退化为：

```json
{
  "mcpServers": {
    "github": { "url": "https://api.githubcopilot.com/mcp/" }
  }
}
```

本地进程：

```json
{
  "mcpServers": {
    "dropbox-dash": {
      "command": "uv",
      "args": ["--directory", "<pinned-checkout>", "run", "server.py"]
    }
  }
}
```

本地 MCP 进程会被平台沙箱化，并过滤凭据类环境变量；不要把长期 token 写进明文 `env`。


---

## 许可与来源

本文件与 `catalog.json` 属 OpenScience Dispatcher 的调度层，以 **Apache-2.0** 分发
（`SPDX-License-Identifier: Apache-2.0`）。`catalog.json` 转录自上游 OpenScience
`backend/cli/src/mcp/catalog.ts`，版权归 Synthetic Sciences / InkVell Inc.，
见仓库根目录的 [`LICENSE`](../LICENSE)、[`NOTICE`](../NOTICE)、
[`ATTRIBUTION.md`](../ATTRIBUTION.md) 与 [`THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md)。
