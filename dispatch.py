#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Part of OpenScience Dispatcher (dispatcher layer). Upstream content and full notices:/n# see LICENSE, NOTICE, ATTRIBUTION.md, THIRD-PARTY-NOTICES.md.
"""OpenScience Dispatcher - retrieval engine for the bundled sub-skill tree and MCP connectors.

Semantics mirror OpenScience's single `skill` tool (name | query | category), plus an
MCP install planner that adapts download sources to the detected network region.

Portable by design: no absolute paths, no machine-specific assumptions.
Works on Windows 10+, macOS and Linux with Python 3.8+ and no third-party dependencies.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS = ROOT / "skills"
MCP_DIR = ROOT / "mcp"
WORKFLOWS = ROOT / "workflows"

# Override the MCP client config location with this environment variable.
MCP_CONFIG_ENV = "OSD_MCP_CONFIG"
DEFAULT_MCP_CONFIG = ".workbuddy/mcp.json"

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

WORD = re.compile(r"[a-z0-9][a-z0-9+#._-]*")
CJK = re.compile(r"[\u4e00-\u9fff]+")
# Separators used for word-boundary comparison inside a haystack.
SEP = re.compile(r"[^a-z0-9]+")

# Upstream skill names and descriptions are English-first, so a Chinese query needs
# term expansion before scoring. Longest match wins.
CN_TERMS = {
    "单细胞": "single cell", "空间转录组": "spatial transcriptomics", "组学": "omics",
    "基因组": "genome", "转录组": "transcriptome", "蛋白": "protein", "蛋白质": "protein",
    "结构预测": "structure prediction", "蛋白结构": "protein structure",
    "分子对接": "molecular docking", "对接": "docking", "结合亲和力": "binding affinity",
    "打分": "scoring", "评分": "scoring", "化合物": "compound", "分子": "molecule",
    "药物设计": "drug design", "从头设计": "de novo design", "分子动力学": "molecular dynamics",
    "训练": "training", "预训练": "pretraining", "微调": "fine-tuning", "量化": "quantization",
    "蒸馏": "distillation", "推理": "inference", "部署": "serving deployment",
    "分布式": "distributed", "并行": "parallel", "加速": "acceleration", "实验追踪": "experiment tracking",
    "可视化": "visualization", "绘图": "plotting", "图表": "chart", "示意图": "schematic",
    "论文": "paper", "写作": "writing", "文献综述": "literature review", "文献": "literature",
    "引用": "citation", "同行评审": "peer review", "海报": "poster", "幻灯片": "slides",
    "检索": "search", "搜索": "search", "数据库": "database", "数据集": "dataset",
    "量子": "quantum", "线路": "circuit", "模拟": "simulation",
    "天体": "astronomy", "物理": "physics", "流体": "fluid", "动力学": "dynamics",
    "优化": "optimization", "聚类": "clustering", "降维": "dimensionality reduction",
    "差异表达": "differential expression", "注释": "annotation", "质控": "quality control",
    "临床": "clinical", "影像": "imaging", "病理": "pathology", "基因编辑": "crispr",
    "序列": "sequence", "比对": "alignment", "变异": "variant", "基因": "gene",
    "智能体": "agent", "提示": "prompt", "向量": "vector", "知识库": "knowledge base",
    "云端": "cloud", "算力": "gpu compute", "显卡": "gpu", "存储": "storage",
    "无服务器": "serverless", "化学": "chemistry", "生物": "biology",
    "文档": "document", "解析": "parsing", "医学": "medical",
    # --- 科研通用 / SCI 论文场景（临床与循证术语）---
    # Only compound phrases here: a bare "分析" -> "analysis" mapping is far too
    # broad and lifts every *-analysis skill above the actually relevant ones.
    "系统综述": "systematic review", "系统评价": "systematic review",
    "荟萃分析": "meta-analysis", "元分析": "meta-analysis",
    "meta分析": "meta-analysis", "meta 分析": "meta-analysis",
    "统计分析": "statistical analysis", "数据分析": "data analysis",
    "文献检索": "literature search", "研究设计": "study design",
    "研究进展": "research progress",
    "随机对照": "randomized controlled trial", "队列研究": "cohort study",
    "病例对照": "case-control", "横断面": "cross-sectional",
    "纳入": "inclusion", "排除": "exclusion", "筛选": "screening",
    "数据提取": "data extraction", "提取": "extraction",
    "森林图": "forest plot", "漏斗图": "funnel plot", "流程图": "flow diagram",
    "异质性": "heterogeneity", "发表偏倚": "publication bias", "偏倚": "risk of bias",
    "效应量": "effect size", "置信区间": "confidence interval",
    "比值比": "odds ratio", "风险比": "hazard ratio", "相对危险度": "relative risk",
    "敏感性分析": "sensitivity analysis", "亚组分析": "subgroup analysis",
    "生存分析": "survival analysis", "回归": "regression",
    "统计": "statistics", "显著性": "significance", "样本量": "sample size",
    "随访": "follow-up", "结局": "outcome",
    "检索式": "search strategy", "主题词": "mesh", "摘要": "abstract",
    "投稿": "submission", "期刊": "journal", "影响因子": "impact factor",
    "审稿": "peer review", "返修": "revision",
    "糖尿病": "diabetes", "心血管": "cardiovascular", "二甲双胍": "metformin",
    "预后": "prognosis", "临床试验": "clinical trial",
}

MIRRORS = {
    "CN": {
        "label": "中国大陆镜像",
        "npm": "https://registry.npmmirror.com",
        "pypi": "https://pypi.tuna.tsinghua.edu.cn/simple",
        "github": "https://ghfast.top/https://github.com",
        "docker": "https://docker.m.daocloud.io",
    },
    "INTL": {
        "label": "国际站",
        "npm": "https://registry.npmjs.org",
        "pypi": "https://pypi.org/simple",
        "github": "https://github.com",
        "docker": "https://docker.io",
    },
}


def expand(q):
    """Append English equivalents for any Chinese term found in the query.

    Matching is case-insensitive, so "Meta 分析" resolves as well. The returned
    phrase list lets the scorer weight a whole-phrase hit above the loose
    individual words that phrase happens to contain.
    """
    low = q.lower()
    keys = sorted((k for k in CN_TERMS if k in low), key=len, reverse=True)
    used, extra = set(), []
    for k in keys:
        if any(k in u for u in used):
            continue
        used.add(k)
        extra.append(CN_TERMS[k])
    return q + (" " + " ".join(extra) if extra else ""), extra


# --------------------------------------------------------------------------- io
def registry():
    return json.loads((ROOT / "registry.json").read_text(encoding="utf-8"))


def catalog():
    return json.loads((MCP_DIR / "catalog.json").read_text(encoding="utf-8"))


def workflows():
    """Scan workflows/*.md.

    Metadata is read from the file itself, so adding a workflow needs no registry
    update: the H1 line supplies the title, the first blockquote supplies the summary.
    """
    rows = []
    if not WORKFLOWS.is_dir():
        return rows
    for f in sorted(WORKFLOWS.glob("*.md")):
        title, summary = "", ""
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for ln in lines:
            s = ln.strip()
            if not title and s.startswith("# ") and not s.startswith("## "):
                title = re.sub(r"^Workflow:\s*\S+\s*", "", s[2:].strip()).lstrip("—-– ").strip()
                continue
            if s.startswith(">") and not summary:
                summary = s.lstrip("> ").strip()
            if title and summary:
                break
        rows.append({"id": f.stem, "title": title or f.stem, "summary": summary, "path": f})
    return rows


def resolve_mcp_config(override=None):
    """Locate the MCP client config file. Precedence: --config > $OSD_MCP_CONFIG > default."""
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get(MCP_CONFIG_ENV, "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / DEFAULT_MCP_CONFIG).resolve()


def find_skill(name):
    rows = registry()
    low = name.strip().lower()
    for e in rows:
        if e["name"].lower() == low:
            return e, rows
    hits = [e for e in rows if e["name"].lower().startswith(low)]
    if len(hits) == 1:
        return hits[0], rows
    return None, rows


# ------------------------------------------------------------------------ score
def words(text):
    """Lowercase word set; treats - _ . / and spaces as separators.

    Whole-word comparison replaces substring matching, which made short query
    tokens collide across unrelated skills: querying "meta" matched "metabolomics",
    "metadata" and Meta-the-company, drowning out the actual meta-analysis skills.
    """
    return {w for w in SEP.split(text.lower()) if w}


def score(e, q, phrases=()):
    ql = q.strip().lower()
    if not ql:
        return 0.0
    name = e["name"].lower()
    tags = [str(t).lower() for t in (e.get("tags") or [])]
    desc = (e.get("description") or "").lower()
    func = (e.get("functionality") or "").lower()
    cat = (e.get("category") or "").lower()
    hay = " ".join([name, desc, func, cat, " ".join(tags)])

    name_w = words(name)
    desc_w = words(desc)
    func_w = words(func)
    cat_w = words(cat)
    tag_w = words(" ".join(tags))

    s = 0.0
    if ql == name:
        s += 120
    elif ql in name:
        s += 45
    if ql in desc:
        s += 25
    if ql in func:
        s += 12
    if ql in hay:
        s += 8
    for t in WORD.findall(ql):
        if len(t) < 2:
            continue
        if t == name:
            s += 30
        elif t in name_w:
            s += 14
        if t in tag_w:
            s += 12
        if t in desc_w:
            s += 5
        if t in func_w:
            s += 3
        if t in cat_w:
            s += 2
    for c in CJK.findall(ql):
        if c in hay:
            s += 10

    # A whole-phrase hit is far stronger evidence of intent than the loose words it
    # contains: "meta-analysis" must outrank any skill merely named "*-analysis".
    for p in phrases:
        pw = words(p)
        if not pw:
            continue
        if pw <= name_w:
            s += 50
        elif pw <= tag_w:
            s += 30
        elif pw <= desc_w:
            s += 25
        elif pw <= func_w:
            s += 15
        elif pw <= (name_w | tag_w | desc_w | func_w | cat_w):
            s += 8
    return s


def brief(e, i=None):
    tag = "".join(f"#{t} " for t in (e.get("tags") or [])[:4])
    head = f"{i:>2}. " if i else ""
    out = [f"{head}{e['name']}  [{e['category']}]  {tag}".rstrip()]
    if e.get("description"):
        out.append(f"    {e['description']}")
    if e.get("functionality"):
        out.append(f"    功能: {e['functionality'][:220]}")
    out.append(f"    路径: {e['path']}")
    return "\n".join(out)


# ----------------------------------------------------------------------- region
def detect_region(timeout=4.0):
    env = os.environ.get("OPENSCIENCE_REGION", "").strip().upper()
    if env in ("CN", "INTL"):
        return env, f"环境变量 OPENSCIENCE_REGION={env}"

    probes = [
        ("https://ipapi.co/json/", ("country_code", "country")),
        ("http://ip-api.com/json/", ("countryCode", "country")),
        ("https://ipinfo.io/json", ("country",)),
    ]
    for url, keys in probes:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "openscience-dispatcher/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            cc = next((str(d[k]) for k in keys if d.get(k)), "").upper()[:2]
            if cc:
                return ("CN" if cc == "CN" else "INTL"), f"IP 地理位置 API 返回 {cc}"
        except Exception:
            continue

    lat = {}
    for label, url in (("baidu", "https://www.baidu.com"), ("google", "https://www.google.com")):
        t0 = time.time()
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                r.read(1)
            lat[label] = time.time() - t0
        except Exception:
            lat[label] = None
    if lat.get("baidu") is not None and lat.get("google") is None:
        return "CN", "百度可达、Google 不可达"
    if lat.get("google") is not None and (lat.get("baidu") is None or lat["google"] < lat["baidu"]):
        return "INTL", "Google 可达且比百度更快"
    if lat.get("baidu") is not None:
        return "CN", "仅百度可达（保守判定）"
    return "CN", "无法判定，按大陆用户保守默认；可用 OPENSCIENCE_REGION=INTL 覆盖"


# -------------------------------------------------------------------------- mcp
def mcp_plan(entry, region):
    m = MIRRORS[region]
    setup = entry.get("setup")
    lines = []

    if setup and setup.get("type") == "remote":
        server = setup["name"]
        cfg = {"type": "http", "url": setup["url"]}
        lines += [
            "安装类型: 远程托管端点（无需下载，只登记 URL）",
            f"服务端名称: {server}",
            f"端点: {setup['url']}",
            f"OAuth: {setup['oauth']}" + ("（需自带 client id/secret）" if setup.get("confidential_client") else ""),
            "",
            "MCP 客户端配置片段:",
            json.dumps({"mcpServers": {server: cfg}}, ensure_ascii=False, indent=2),
            "",
            "说明:",
            "  · 若客户端不识别 type=http，退化为 " + json.dumps({"mcpServers": {server: {"url": setup["url"]}}}, ensure_ascii=False),
            "  · 写入后需在平台的连接器管理页对该服务器点「信任」/启用，不会自动生效",
            "  · OAuth 走浏览器回环回调；授权范围需人工核对后再批准",
        ]
        if entry.get("recommended"):
            lines.append("  · 上游标记为 recommended + one_click_connect")
    elif setup and setup.get("type") == "local":
        server = setup["name"]
        cfg = {"command": setup.get("command", ""), "args": setup.get("args", [])}
        lines += [
            "安装类型: 本地进程（需下载）",
            f"命令: {cfg['command']} {' '.join(cfg['args'])}",
            "",
            "按网络区域选择下载源:",
            f"  npm registry → {m['npm']}",
            json.dumps({"mcpServers": {server: cfg}}, ensure_ascii=False, indent=2),
        ]
    else:
        lines.append("安装类型: 手工审查（上游未提供已审端点，本包不代为克隆或执行）")
        if entry["id"] == "benchling":
            lines += [
                "",
                "步骤:",
                "  1. 由租户管理员在 Benchling 开启 Benchling Chat 与 MCP，并启用 V3 API",
                "  2. 替换为你的真实租户地址 https://<tenant>.mcp.benchling.com/mcp",
                "  3. 走 OAuth 2.1 动态客户端注册完成授权",
                "",
                json.dumps({"mcpServers": {"benchling": {"type": "http", "url": "https://<tenant>.mcp.benchling.com/mcp"}}}, ensure_ascii=False, indent=2),
            ]
        elif entry["id"] == "dropbox":
            lines += [
                "",
                "步骤（上游要求固定 commit，禁止跟踪活动分支）:",
                f"  1. 克隆并检出一个已审阅的固定提交（{m['label']}）:",
                f"     git clone {m['github']}/dropbox/mcp-server-dash && cd mcp-server-dash",
                f"  2. 安装依赖（{m['label']}）:",
                f"     uv pip install -r requirements.txt --index-url {m['pypi']}",
                "  3. 用只读 Dropbox 作用域创建应用并取得 token",
                "  4. 将确切的本地启动命令手工登记进 mcp 配置",
            ]

    lines += ["", "安全要求:",
              f"  · 写入操作（{len(entry.get('upstream_write_operations') or [])} 项）默认全部关闭，任何写操作需二次确认",
              "  · 每次工具调用都要过一次权限边界，不要批量预授权"]
    return "\n".join(lines)


def write_mcp(server_name, cfg, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = path.with_name(f"{path.name}.bak-{stamp}")
        shutil.copy2(path, backup)
        print(f"已备份原配置 → {backup}")
    servers = data.setdefault("mcpServers", {})
    servers[server_name] = cfg
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------- commands
def cmd_list(a):
    rows = registry()
    if a.category:
        rows = [e for e in rows if e["category"].lower() == a.category.lower()]
    rows.sort(key=lambda e: (e["category"], e["name"]))
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    print(f"共 {len(rows)} 个子技能" + (f"（分类 {a.category}）" if a.category else ""))
    for i, e in enumerate(rows, 1):
        print(brief(e, i))


def cmd_category(a):
    rows = registry()
    if not a.name:
        counts = {}
        for e in rows:
            counts[e["category"]] = counts.get(e["category"], 0) + 1
        print(f"共 {len(counts)} 个分类 / {len(rows)} 个子技能")
        for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {v:>3}  {k}")
        return
    rows = [e for e in rows if e["category"].lower() == a.name.lower()]
    if not rows:
        print(f"未找到分类: {a.name}")
        return
    print(f"分类 {a.name} — {len(rows)} 个子技能")
    for i, e in enumerate(rows, 1):
        print(brief(e, i))


def cmd_query(a):
    rows = registry()
    if a.category:
        rows = [e for e in rows if e["category"].lower() == a.category.lower()]
    q, extra = expand(a.text)
    ranked = sorted(((score(e, q, extra), e) for e in rows), key=lambda x: -x[0])
    hits = [(s, e) for s, e in ranked if s > 0][: a.top]
    if a.json:
        print(json.dumps([{**e, "score": round(s, 1)} for s, e in hits], ensure_ascii=False, indent=1))
        return
    note = f"（中文术语已展开: {'、'.join(extra)}）" if extra else ""
    if not hits:
        print(f"无匹配{note}。可先用 `category` 浏览分类，或换用更贴近上游英文命名的关键词。")
        return
    print(f"检索「{a.text}」— 命中 {len(hits)} 个（已按相关度排序）{note}")
    for i, (s, e) in enumerate(hits, 1):
        print(f"\n[{s:.0f} 分]")
        print(brief(e, i))
    print("\n下一步: 用 `load <name>` 载入命中的子技能，读完其 SKILL.md 再执行。")


def cmd_load(a):
    e, rows = find_skill(a.name)
    if not e:
        cands = sorted(((score(x, a.name), x) for x in rows), key=lambda x: -x[0])[:5]
        print(f"未精确匹配「{a.name}」。相近候选：")
        for i, (s, x) in enumerate(cands, 1):
            print(brief(x, i))
        sys.exit(1)

    base = ROOT / e["path"]
    text = (base / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\s*\n.*?\n---\s*\n?(.*)$", text, re.DOTALL)
    body = m.group(1) if m else text

    print(f"## Skill: {e['name']}")
    print(f"**Category**: {e['category']}")
    print(f"**Base directory**: {base}")
    if e.get("license"):
        print(f"**License**: {e['license']}")
    if e.get("tags"):
        print(f"**Tags**: {', '.join(map(str, e['tags']))}")
    if e.get("description"):
        print(f"**Description**: {e['description']}")
    if e.get("functionality"):
        print(f"**功能**: {e['functionality']}")
    print(f"**资源**: {', '.join(sorted(p.name for p in base.iterdir() if p.name != 'SKILL.md')) or '（仅 SKILL.md）'}")
    print("\n> 子技能目录为只读；其中的脚本可在该目录内用 Bash 运行。")
    print("\n---\n")
    print(body.strip())


def cmd_mcp(a):
    entries = catalog()
    if a.action == "list":
        if a.json:
            print(json.dumps(entries, ensure_ascii=False, indent=1))
            return
        print(f"MCP 连接器 {len(entries)} 个（全部默认禁用，待人工审查）")
        for i, e in enumerate(entries, 1):
            flag = "★推荐 " if e.get("recommended") else ""
            print(f"{i:>2}. {e['name']}（id={e['id']}）{flag}[{e['status']}]")
            print(f"    {e['summary']}")
            print(f"    读: {'；'.join(e['read_operations']) or '—'}")
            print(f"    写: {'；'.join(e['upstream_write_operations']) or '—'}")
            print(f"    要求: {'；'.join(e['requirements'])}")
        return

    if a.action == "config":
        path = resolve_mcp_config(a.config)
        print(f"MCP 客户端配置文件: {path}")
        print(f"  存在: {'是' if path.exists() else '否（写入时会自动创建目录）'}")
        print(f"  来源: {'--config 参数' if a.config else ('环境变量 ' + MCP_CONFIG_ENV if os.environ.get(MCP_CONFIG_ENV) else '默认位置')}")
        print(f"\n如需改到其它位置，设置环境变量 {MCP_CONFIG_ENV}，或调用时加 --config <路径>。")
        return

    if a.action == "show":
        hit = next((e for e in entries if e["id"] == a.id or e["name"].lower() == a.id.lower()), None)
        if not hit:
            print(f"未找到连接器: {a.id}")
            sys.exit(1)
        print(json.dumps(hit, ensure_ascii=False, indent=2))
        return

    if a.action == "install":
        hit = next((e for e in entries if e["id"] == a.id or e["name"].lower() == a.id.lower()), None)
        if not hit:
            print(f"未找到连接器: {a.id}")
            sys.exit(1)
        region, reason = detect_region()
        m = MIRRORS[region]
        target = resolve_mcp_config(a.config)
        print(f"网络区域判定: {region}（{m['label']}）— 依据: {reason}")
        print(f"目标配置文件: {target}\n")
        print(mcp_plan(hit, region))

        if a.write:
            setup = hit.get("setup")
            if setup and setup.get("type") == "remote":
                server = setup["name"]
                cfg = {"type": "http", "url": setup["url"]}
            elif setup and setup.get("type") == "local":
                server = setup["name"]
                cfg = {"command": setup.get("command", ""), "args": setup.get("args", [])}
            else:
                print("\n该连接器无已审端点，无法自动写入；请按上面步骤手工登记。")
                return
            path = write_mcp(server, cfg, target)
            print(f"\n已写入 {path} → mcpServers.{server}")
            print("注意: 不会自动激活，需在平台连接器管理页对该服务器点「信任」/启用。")
        else:
            print("\n（未写入磁盘。加 --write 可写入，会自动备份。）")
        return

    if a.action == "plan":
        region, reason = detect_region()
        print(f"网络区域判定: {region}（{MIRRORS[region]['label']}）— 依据: {reason}\n")
        for e in entries:
            if e.get("setup"):
                print("=" * 72)
                print(mcp_plan(e, region))
                print()


def cmd_net(a):
    region, reason = detect_region()
    m = MIRRORS[region]
    print(f"区域: {region}（{m['label']}）")
    print(f"依据: {reason}\n")
    print("下载源映射:")
    for k in ("npm", "pypi", "github", "docker"):
        print(f"  {k:<7} {m[k]}")
    print("\n覆盖方式: 设置环境变量 OPENSCIENCE_REGION=CN 或 INTL")


def cmd_workflow(a):
    rows = workflows()
    if a.action == "show":
        if not a.id:
            print("请指定工作流 id，例如: dispatch.py workflow show sci-paper")
            if rows:
                print("可用: " + ", ".join(r["id"] for r in rows))
            return
        key = a.id.strip().lower()
        hit = next((r for r in rows if r["id"].lower() == key), None)
        if not hit:
            print(f"未找到工作流: {a.id}")
            if rows:
                print("可用: " + ", ".join(r["id"] for r in rows))
            return
        print(hit["path"].read_text(encoding="utf-8"), end="")
        return

    if not rows:
        print("未找到工作流定义（workflows/ 目录为空）。")
        return
    print(f"可用工作流（{len(rows)}）:\n")
    for r in rows:
        print(f"  {r['id']:<14} {r['title']}")
        if r["summary"]:
            print(f"  {'':<14} {r['summary'][:96]}")
    print("\n查看全文: dispatch.py workflow show <id>")


def main():
    p = argparse.ArgumentParser(
        prog="dispatch",
        description="OpenScience dispatcher for bundled sub-skills and MCP connectors",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list", help="列出全部子技能")
    s.add_argument("--category", help="只看某分类")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("category", help="浏览分类（不带参数则列出所有分类）")
    s.add_argument("name", nargs="?")
    s.set_defaults(fn=cmd_category)

    s = sub.add_parser("query", help="按自然语言关键词检索子技能")
    s.add_argument("text")
    s.add_argument("--top", type=int, default=8)
    s.add_argument("--category")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_query)

    s = sub.add_parser("load", help="载入某个子技能（输出其 SKILL.md 与基础目录）")
    s.add_argument("name")
    s.set_defaults(fn=cmd_load)

    s = sub.add_parser("mcp", help="管理 MCP 连接器（config/list/show/install/plan）")
    s.add_argument("action", choices=["config", "list", "show", "install", "plan"])
    s.add_argument("id", nargs="?")
    s.add_argument("--write", action="store_true", help="真正写入 MCP 配置文件（自动备份）")
    s.add_argument("--config", help=f"MCP 配置文件路径（默认 ~/{DEFAULT_MCP_CONFIG}，可用 ${MCP_CONFIG_ENV} 覆盖）")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_mcp)

    s = sub.add_parser("net", help="显示网络区域判定与镜像源映射")
    s.set_defaults(fn=cmd_net)

    s = sub.add_parser("workflow", help="端到端科研工作流（列阶段、门控与产物）")
    s.add_argument("action", nargs="?", default="list", choices=["list", "show"])
    s.add_argument("id", nargs="?", help="工作流 id，配合 show 使用")
    s.set_defaults(fn=cmd_workflow)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
