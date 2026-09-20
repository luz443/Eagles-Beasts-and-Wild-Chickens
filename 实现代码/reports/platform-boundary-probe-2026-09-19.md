# 平台边界探测报告（2026-09-19）

> 对应 `docs/HANDOFF.md` 待办第 1 项："平台边界探测（1 小时四问）"。
> 方法：以本机 LearnBuddy 内置的 **expert-manager 技能**（专家包开发规范 v2.0 的权威来源）为证据，
> 辅以官方脚本实物核对。第三方网页教程（头条/php.cn 等）全部弃用，不作证据。

## 四问结论速览

| # | 问题 | 结论 | 是否影响架构 |
| --- | --- | --- | --- |
| 1 | 专家能否挂知识库 | **包内不能声明**；用 `skills/*/references/` 承载资料（官方转化策略明文支持） | 否 |
| 2 | 技能里能否放代码 | **能**。`skills/*/scripts/`（脚本）与 `bin/`（CLI）是官方结构 | 否（利好） |
| 3 | 能否挂连接器 | **专家包不能自带**；连接器是会话级/自动化级能力 | 否（本作品不需要） |
| 4 | 能否打包导出 | **能**。官方脚本 `package_expert.py` | 否（利好开源交付） |

**总裁定：四个答案都不要求改架构。** 原方案（六个技能挂专家 + references 放契约 + scripts 放 build()）成立，
可以直接进入第 2 件事：六个技能的 `build()`。

## 逐问证据

### Q1 专家能否挂知识库？

- 证据 A：`plugin.json` 字段规范（expert-manager 技能 `references/plugin-json-spec.md`，已全文读取）。
  全部字段为：name / version / description / author / homepage / license / keywords / expertType /
  agentName / teamInfo / agents / skills / 展示字段（displayName 等）/ members。**没有任何知识库字段。**
- 证据 B：官方"资料转化策略"表（SKILL.md 第三节）明文：
  - 「大段参考资料 → `references/` —— 不要塞进 Agent MD 正文」
  - 「API 文档、字段定义 → SKILL.md + references/」
- 证据 C：Agent MD frontmatter 可选字段 `skills: [{skill-name}]`（启动时预加载的 Skill），
  即技能（连同其 references/）可以在专家会话开始时自动加载。
- 未证实项（如实登记）：**平台"资料库"能否绑定到某个专家**——专家包规范里没有这个字段，
  本地无法证实或证伪。但替代方案（references/）已确定可用，不阻塞本项目。

### Q2 技能里能否放代码？

- 证据 A：官方"资料转化策略"表明文：「可执行脚本代码 → `scripts/`」「通用 CLI 工具 → `bin/`」。
- 证据 B（实物）：expert-manager 技能自身就带 6 个 Python 脚本，位于
  `C:\Users\Lenovo\AppData\Local\Programs\LearnBuddy\resources\app.asar.unpacked\resources\builtin-skills\expert-manager\scripts\`
  （batch_create.py / init_expert.py / package_expert.py / register_expert.py / test_package_expert.py / validate_expert.py，
  Glob 实测存在）。
- 推论：六个技能 `build()` 的确定性 Python 部分可以直接放进 `skills/*/scripts/`，
  由专家在会话中调用执行。

### Q3 能否挂连接器？

- 证据 A：`plugin.json` 规范中**没有 connector 字段**。
- 证据 B：Agent MD 规范明文：「frontmatter 中不可添加 tools 字段——所有工具权限由系统统一分配，
  开发者无需也不能在 frontmatter 中声明」。
- 证据 C：连接器（MCP）在本平台是会话级/自动化级能力——automations 配置可指定 `connectorIds`
  与 `expertId`，但专家包本身不声明连接器。
- 对本作品的影响：**零**。赛规禁止第三方 AI，且我们的铁律是"网页侧零模型调用"，
  全部 AI 能力都在专家 + 本地确定性代码里，不需要任何 MCP 连接器。

### Q4 能否打包导出？

- 证据（实物）：官方打包脚本存在：
  `...\builtin-skills\expert-manager\scripts\package_expert.py <expert-dir> [output-dir]`。
- 用途：开源仓库交付时，可以把整个专家包（agents + skills + references + scripts）一并导出，
  与"开源代码仓库"交付物互相印证。

## 专家包目录结构（探测中确认，供 build() 落地用）

```
<expert-name>/
├── .codebuddy-plugin/plugin.json   # name(kebab-case) / expertType / agents / skills / 展示字段
├── agents/<agent-name>.md          # frontmatter 禁 tools；可选 skills: 预加载
├── skills/<skill-name>/
│   ├── SKILL.md
│   ├── references/                 # 大段参考资料：schema、维度枚举、提示词
│   ├── scripts/                    # 可执行 Python：build() 的确定性部分
│   └── templates/
├── avatars/                        # 512×512，≤500KB
└── bin/                            # 通用 CLI（可选）
```

> **勘误（2026-09-19 晚，落地实验时发现）**：元数据目录的正确名字是 **`.codebuddy-plugin/`**，
> 本文早期版本写成 `.workbuddy-plugin/`。以官方脚本实物为准：`init_expert.py` 生成的是
> `.codebuddy-plugin/plugin.json`，`validate_expert.py` 也据此检查（`register_expert.py`
> 为兼容两种名字都认，但只有前者是规范）。建包时以 `init_expert.py` 的输出为准。

关键铁律（摘自规范，落地时必须遵守）：

1. `name` 字段 kebab-case；`agentName` = agents/ 下 MD 文件名（不含 .md）。
2. tags / quickPrompts **固定 3 个**；第一条 quickPrompt = defaultInitPrompt。
3. displayDescription 中文 40–50 字。
4. Agent MD frontmatter **禁止 tools 字段**。
5. 生成后必须走 `validate_expert.py` → `register_expert.py`，禁止手写 marketplace.json。
6. 专家目录固定为 `$WORKBUDDY_CONFIG_DIR/plugins/marketplaces/my-experts/plugins`。

## 下一步

进入 HANDOFF 待办第 2 项：**六个技能的 `build()`**——把 `prompts/*.md` 与
`src/rra/skills/*.py` 的确定性入口落进上述专家包结构。
