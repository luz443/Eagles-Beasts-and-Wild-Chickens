# 交接说明（研究复盘助手 · 2026-09-19 18:00 快照）

> 这一页是**状态**的唯一入口：谁接手（新会话 / 新同学 / 压缩上下文之后）都先读它。
> 作品要做什么、做什么形态 → 见 [`product-form.md`](product-form.md)；逐任务进度 → 见 [`plans/2026-09-19-implementation-plan.md`](plans/2026-09-19-implementation-plan.md)。

## 三十秒上手

| 想做的事 | 命令 |
| --- | --- |
| 跑一遍全部验证 | `python run_tests.py`（Python 测试 + 两端契约一致性测试） |
| 本地看网页 | 在 `web/` 下起 `python -m http.server 8123`，打开 `http://127.0.0.1:8123/index.html` |
| 深链直达某个视图 / 档案 | 网址后加 `#/map`、`#/incubation`、`#/detail/R-003`；检索条件也可带 `#/library?q=显存&sort=confidence` |
| 键盘操作 | `1`–`5` 切视图、`/` 定位检索框（界面页签下方有提示） |
| 重新生成种子数据 | `python tools/make_seed.py` |
| 校验库并同步给网页 | `python tools/validate_library.py` |
| 跑评测（当前为占位执行器） | `python tools/run_eval.py` |

## 现在到哪了

| 模块 | 状态 |
| --- | --- |
| 契约层（schema / 维度枚举 / 校验器 / 4 个夹具） | ✅ 完成，**两端一致性测试通过** |
| 库（读写 / 去重指纹 / 合并重编号 / 原子导入） | ✅ 完成 |
| 召回（字段加权 + 命中解释 + 宁少不凑的门限） | ✅ 完成 |
| 评测（27 条用例 / 跑批 / 记录表 / 盲测守门 / 缓存） | ✅ 完成（未跑真实专家） |
| 种子数据（14 条，含死实验复活伏笔） | ✅ 完成 |
| 导出（档案报告 / 避坑清单） | ✅ 完成 |
| 网页（数据层 + 六视图 + 引用上标 + 反驳入口） | ✅ 完成，**视觉已重做为「档案刊」风格**（规格见 `docs/design-spec-web.md`，19 对配色实测达标，7 张逐视图截图验证，0 控制台错误） |
| 网页交互层（深链路由 / 键盘快捷键 / 排序切换） | ✅ 完成（`js/route.js` + `js/util/sort.js`；交互实测 24 项 × file/http 两模式全过，见设计规格第十节） |
| 技能基座 + 五个技能的确定性部分 | ✅ 完成 |
| **专家包（6 个技能 + 提示词 + 确定性 CLI）** | ✅ **已落地、官方校验通过、已注册**（包名 `research-retro-assistant`；仓内镜像 `expert/research-retro-assistant/`；CLI 自检 5 步全过） |
| 技能语义层（原 `build()` 桩） | 🟡 **改由专家承担**——平台上语义判断由模型做，代码只做确定性把关（见下方第 2 项） |
| **平台内冒烟（专家能否执行包内脚本）** | ✅ **已通过**（2026-09-19 20:00）：平台内以该专家跑一次性任务，`ls` + `selftest` 均**退出码 0**，回执原文见 `_build/smoke-platform-run-2026-09-19.txt`；该会话 **0.92 Credits** |
| **真实评测跑批** | ⛔ 待平台（要 Credits） |
| PPT / 视频 / 对话记录 | ⛔ 未开始 |
| 静态托管（作品在线链接） | 🟡 已部署待确认：https://851ad98062994a60a3b8f1ffd8c56704.app.workbuddy.host （沙箱上游暂 504，稍等重试；本地兜底见下） |

验证现状：Python **116 条测试全绿**（2026-09-19 外部后端审查修复后新增 18 条护栏：CLI 自举 3 / 引文可复核 7 / 嵌套容错 4 / 评测纪律 4）；`tools/check_web.py` 全绿（18 个 JS 语法 + 3 个 CSS）；`python run_tests.py` 含 5 个前端套件（契约一致性 5 夹具 / 路由 21 项 / 排序 10 项 / 纠错规则两端一致 10 项 / **写失败原子性 10 项**）；浏览器交互实测 24 项（file:// 与 http:// 各一轮，控制台真实错误 0）；`sync_expert.py --check`（仓库镜像）与 `--check --platform`（本机已装包）摘要均一致；`tools/rra_cli.py` 在无关目录、不设 `PYTHONPATH` 下 **exit 0**。

## 只剩这四件（按依赖顺序）

1. ~~**平台边界探测**~~ ✅ **已完成**（2026-09-19，结论见 `reports/platform-boundary-probe-2026-09-19.md`）：
   四问均**不要求改架构**——技能可放代码（scripts/）、可打包导出（package_expert.py）、
   参考资料走 skills/*/references/；专家包不声明知识库/连接器，本作品也不需要。
2. **六个技能** ~~`build()`~~ ✅ **落地方式已定并已建包**（2026-09-19 晚，证据见 `reports/platform-boundary-probe-2026-09-19.md` 与
   `_build/expert-*.txt`）：
   - **结论（改变了原计划）**：平台上**技能脚本无法调用模型**（实物核对：唯一涉网脚本走的是平台云服务能力，
     需连接器授权，赛规亦禁用）。因此语义判断**由专家本身承担**，`src/rra/skills/*.py` 的 `build()` 保持桩，
     其"平台调用"位置由各技能的 `SKILL.md` 流程取代；代码侧只做确定性把关。
   - **产物**：专家包 `research-retro-assistant`（`agents/` 角色定义 + `skills/{extract-record, reverse-lookup,
     condition-compare, induction, resurrection, reviewer2}` + `bin/rra_cli.py` 确定性引擎 + references 提示词与契约）。
     官方 `validate_expert.py` 通过、`register_expert.py` 已注册；仓内镜像 `expert/research-retro-assistant/`。
   - **同步方式**：`python tools/sync_expert.py`（单一真源 = 仓库；包内引擎摘要与仓库比对，`--check` 可做交付前自检）。
   - **剩**：无（**已冒烟通过**，2026-09-19 20:00：平台内以该专家跑一次性任务，`ls` 与 `selftest` 退出码均 0，
     回执原文 `_build/smoke-platform-run-2026-09-19.txt`；该会话 0.92 Credits）。
   - **可复用机制**：平台没有"代码调专家"的 API，但可用「一次性自动化任务 + 绑定 `expertId`」真实执行专家，
     再从 `~/.learnbuddy/workbuddy.db` 的 `automation_runs.runs_json[].output` 读回执
     （流程与坑已写成技能 `~/.learnbuddy/skills/platform-expert-smoke-run/SKILL.md`）——评测跑批同样走这条路。
3. **先测单次 Credits 成本**，再定评测规模（判定规则：单次 > 60 就把开放用例压到 6 条，保盲测 10 条与录屏）。
   已有第一个实测锚点：**轻量冒烟会话 0.92 Credits**（1 条短指令 + 2 条 shell 命令，`session_usage.credit_json`）——
   远低于阈值；但**带完整日志抽取的真实技能会话会更重**，要按同类任务再测一次再定规模。
4. **真实评测跑批**：把 `tools/run_eval.py` 的占位执行器换成专家调用 → 产出 `reports/eval-log.md`（PPT 第 8 页用它）。
5. **材料与部署**：3 分钟视频、PPT、对话记录导出；~~静态托管上线~~ **已部署**（链接见上表；若打不开稍等几秒重试，本地兜底 `python -m http.server 8123` 或直接双击 `web/index.html`）。

## 三条不能违反的规则

1. **网页侧零模型调用**：AI 能力全部在 LearnBuddy 专家里；网页只做确定性的召回与视图。
2. **证据引用必须带档案编号 + 原文片段**：没有出处的判断不许出现在任何输出里。
3. **假设不得写成结论**：归因类型只能是 `assumption` / `observed`；日志没给原因时只能是前者。

## 状态源（谁是权威，别互相打架）

| 内容 | 权威文件 |
| --- | --- |
| 逐任务进度 | `docs/plans/2026-09-19-implementation-plan.md` |
| 作品形态与完工标准 | `docs/product-form.md` |
| 技术选型与取舍 | `docs/technical-notes.md` |
| 引用编号 | 项目目录 `参考文献/`（当前 R1–R22，下一条 **R23**） |
| 代码审查结论 | `reports/code-review-2026-09-19.md` |
| 网页视觉规格 / 令牌 / 路由与键盘交互规范 | `docs/design-spec-web.md`（路由与键盘见第十节） |
| 后端审查作业书（交给外部 AI 用） | `docs/review-prompt-backend.md` |
| 后端审查处置报告（回给审查方） | `docs/review-response-2026-09-19.md` |

## 常见坑（都真踩过）

- 本机 **Bash 工具不可用**（任何命令报 `unexpected EOF`）；PowerShell **不回传 stdout**，取输出要"脚本写文件 + 读文件"。
- 生成类/补丁类脚本**写盘前必须编译检查**；`io.open(newline=...)` 只允许 None / "" / "\n" / "\r" / "\r\n"（写错会先截断文件再报错）。
- 被编辑器打开的文件**无法覆盖**（`PermissionError`）→ 另存新版本号，不要要求用户关文件。
- **验证脚本自身也要能被证伪**：曾因正则被双重转义报出"0/0 全干净"的假阴性。
- **跨端分叉不止在数据契约里，也在"行为约定"里**：2026-09-19 实测发现网页端 `incubation.js` 会剔除
  「人工纠错」记录再数归纳门槛，而 Python 侧原本没有这条过滤——同一个库，网页说"不足 3 条"、
  专家侧却产出假设。已收口为 `src/rra/library/refutation.py`（规则唯一真源），并加了两道护栏：
  `tests/test_refutation_filter.py`（9 条）与 `web/tests/refutation-rule-parity.mjs`（10 项，直接比字面量）。
  **规则若只在 schema 里管不到，就必须在两端各放一个测试**，否则改一端会静默破坏一致性。
- **占位/桩产出的数字不许落进正式文件**：`reports/eval-log.md` 只能由真实跑批写；
  占位运行只写 `reports/eval-results/*-local.json` 且退出码为 1（旧占位表格已移至 `eval-log.local.md`）。
- **测试基准必须可重建**：`reports/contract-parity.json` 由 `tools/make_contract_parity.py` 生成，
  `run_tests.py` 每次跑前重建——手写基准会让两端测试拿过期快照静默通过。
