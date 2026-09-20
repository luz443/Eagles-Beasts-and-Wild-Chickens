# 研究复盘助手（research-retro-assistant）

把**杂乱的实验记录**读成**带编号、带原文证据、可复核的结构化档案**，并在入库当下反查同类尝试与冲突判断。

- 类型：Agent 型（单专家）
- 行业分类：`04-DataAI`（数据智能）——主要输出物是结构化研究档案与可检索的知识资产
- 对应作品：粤港澳大湾区 AI Coding 创新大赛 · 研究方向二（AI + 学术科研助手）

## 六个技能

| 技能 | 作用 |
| --- | --- |
| `extract-record` | 把日志抽成一条契约档案（编号由 CLI 给） |
| `reverse-lookup` | 入库即反查：同类 / 冲突 / 缺什么信息 |
| `condition-compare` | 条件对齐后再判是否真冲突（条件不全就不下结论） |
| `induction` | 同一阻塞点 ≥3 条 → 可立项假设 + 证据强度 + 反例 |
| `resurrection` | 已放弃且阻塞点明确的记录 → 复活支点评估 |
| `reviewer2` | 带证据的质疑（无证据不许质疑） |

## 三条铁律（在 Agent 定义与各技能里重复声明）

1. 证据引用必须带**档案编号 + 原文片段**；
2. 假设不得写成结论（`attribution.type` 只能是 `observed` / `assumption`）；
3. 证据不足就**拒绝**，不编造（缺的写进 `missing_info`）。

## 语义与确定性分离（本包的核心架构）

- **语义判断**由专家（模型）完成：抽取、判断关系、写假设、写质疑。
- **确定性步骤**一律走随包 CLI，专家不得自己算：

```bash
python3 bin/rra_cli.py selftest                      # 自检：校验/编号/召回/归纳/复活
python3 bin/rra_cli.py validate-library <库文件>      # 契约校验（不合规 → 退出码 1）
python3 bin/rra_cli.py next-id <库文件>
python3 bin/rra_cli.py recall <库文件> "<关键词>"     # 宁少不凑
python3 bin/rra_cli.py dedup-check <库文件> <候选>
python3 bin/rra_cli.py apply-clarification <档案.json> "<已澄清字段>"
python3 bin/rra_cli.py condition-compare <a> <b>
python3 bin/rra_cli.py induction-candidates <库文件>
python3 bin/rra_cli.py resurrection-candidates <库文件>
python3 bin/rra_cli.py merge-library <库文件> <新库> --out <输出>
python3 bin/rra_cli.py report <档案.json>            # Markdown 档案报告
python3 bin/rra_cli.py blocker-digest <库文件>        # 避坑清单
python3 bin/rra_cli.py eval-cases                     # 评测用例清单（开放 17 / 盲测 10）
```

纯标准库、不联网、不调用任何模型。

## 生成物说明（重要）

`bin/rra/`、`skills/*/references/`、`bin/samples/` **都是生成物**，单一真源是代码仓库：

| 包内路径 | 来自仓库 |
| --- | --- |
| `bin/rra/**` | `src/rra/**` |
| `bin/rra_cli.py` | `tools/rra_cli.py` |
| `skills/*/references/prompt.md` | `prompts/*.md` |
| `skills/*/references/*.schema.json`、`dim.json` | `contracts/*.json` |
| `bin/samples/library.seed.json` | `data/library.seed.json` |

改代码请改仓库，然后重跑 `python tools/sync_expert.py`；`bin/SYNC.json` 里存着引擎摘要，
可用来发现「包内代码与仓库不一致」。

## 安装

把本目录放到专家目录下：

```
$WORKBUDDY_CONFIG_DIR/plugins/marketplaces/my-experts/plugins/research-retro-assistant/
```

然后按官方流程注册（专家不注册不会出现）：

```bash
python3 <expert-manager>/scripts/validate_expert.py <expert-dir>
python3 <expert-manager>/scripts/register_expert.py <expert-dir> --session-id <本会话 id>
```

> 本机注意：官方脚本会 print emoji，Windows 控制台是 GBK 时会崩 —— 跑之前设
> `PYTHONIOENCODING=utf-8`（`set PYTHONIOENCODING=utf-8` 或 PowerShell 的 `$env:PYTHONIOENCODING="utf-8"`）。

## 打包分享

```bash
python3 <expert-manager>/scripts/package_expert.py <expert-dir> [输出目录]
```

## 头像

`avatars/` 目前只有 `.gitkeep`。补头像时按官方要求：PNG/JPG、512×512、≤500KB，
命名为 `avatars/expert.png`（`plugin.json` 的 `avatar` 字段已指向它）。
