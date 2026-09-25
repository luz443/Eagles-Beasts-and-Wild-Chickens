# 交接说明（研究复盘助手 · 2026-09-20 快照）

> 这一页是**状态**的唯一入口：谁接手（新会话 / 新同学 / 压缩上下文之后）都先读它。
> 作品要做什么、做什么形态 → 见 [`product-form.md`](product-form.md)；
> 逐任务进度 → 见 [`plans/2026-09-19-implementation-plan.md`](plans/2026-09-19-implementation-plan.md)。

## 三十秒上手

| 想做的事 | 命令 |
| --- | --- |
| 跑一遍全部验证 | `<python> run_tests.py`（268 条 Python 测试 + 7 个前端套件） |
| 本地看网页 | 在 `web/` 下起 `<python> -m http.server 8123`，打开 `http://127.0.0.1:8123/index.html` |
| 深链直达某个视图 / 档案 | 网址后加 `#/resurrection`、`#/map`、`#/incubation`、`#/detail/R-003`；检索条件也可带 `#/library?q=显存&sort=confidence` |
| 键盘操作 | `1`–`6` 切视图、`/` 定位检索框（界面页签下方有提示） |
| 重新生成种子数据 | `<python> tools/make_seed.py` |
| 校验库并同步给网页 | `<python> tools/validate_library.py` |
| 刷新专家包镜像的生成物 | `<python> tools/sync_expert.py --mirror-only` |
| 校验专家包与仓库一致 | `<python> tools/sync_expert.py --check` |
| 冻结六份提示词 | `<python> tools/run_eval.py --create-freeze reports/prompt-freeze.json --prompts-dir prompts --version v1.0-frozen --by <名字>` |
| 盲测守门自检（改动提示词后应退 1） | `<python> tools/run_eval.py --blind --placeholder` |
| 跑评测（当前为占位执行器） | `<python> tools/run_eval.py` |
| 静态检查网页 | `<python> tools/check_web.py` |

`<python>` 指任意 Python 3.11+（除标准库外无运行时依赖）。Node 仅测试期需要。

## 现在的状态

| 模块 | 状态 |
| --- | --- |
| 契约层（schema / 维度枚举 / 校验器 / **11 个夹具**） | ✅ 完成，**两端一致性测试通过** |
| 库（读写 / 去重指纹 / 合并重编号 / 原子导入） | ✅ 完成 |
| 召回（字段加权 + 命中解释 + 宁少不凑的门限） | ✅ 完成 |
| 评测（27 条用例 / 跑批 / 记录表 / 盲测守门 / 缓存） | ✅ 完成（未跑真实专家） |
| 种子数据（**15 条**，含死实验复活伏笔 + 解除依据 + 专家质询） | ✅ 完成 |
| 导出（档案报告 / 避坑清单） | ✅ 完成 |
| 网页（数据层 + **八个视图** + 引用上标 + 反驳入口 + 深链路由 + 键盘） | ✅ 完成，视觉为「档案刊」风格（规格见 `docs/design-spec-web.md`） |
| **可重试方向视图（附录 D.1 的 S2 死实验复活）** | ✅ **本轮新增**：`#/resurrection`，复用候选规则 + 消费专家写回的 `resurrection.unblocks` |
| **立项检查主动质询（附录 D.1 的 D5 审稿人 2 号）** | ✅ **本轮新增**：网页算「已有 N 次 / M 条未验证」的计数，专家写回的质询逐条须带证据编号 |
| **六份技能提示词定稿并冻结** | ✅ **本轮新增**：`prompts/*.md` 已写成 `v1.0-frozen`；`reports/prompt-freeze.json` 记录六份逐份哈希 + 合并哈希 |
| **六个技能的 `build()`（确定性把关）** | ✅ **本轮新增**；`src/rra` 下只剩 `base.py::build` 一处 `NotImplementedError`，且有明确理由 |
| 专家包（6 技能 + 提示词 + 确定性 CLI） | ✅ 已落地、官方校验通过、已注册；仓内镜像 `expert/` 由 `--mirror-only` 同步 |
| 平台内冒烟（专家能否执行包内脚本） | ✅ 已通过（2026-09-19 20:00，`ls` + `selftest` 退出码均 0，0.92 Credits） |
| **真实评测跑批** | ✅ **已完成（2026-09-23）**：27/27 用例、平台内真实会话 5 批、23.79 Credits；见 `reports/eval-real-sessions.md`（`reports/eval-log.md` 仍只由跑批器写） |
| PPT / 视频 | ⛔ 未开始（本轮明确不做） |
| 对话记录 | ✅ 已入包（`实现代码/对话记录/`，5 份真实会话 jsonl + README，已脱敏） |
| 静态托管（作品在线链接） | 🟡 待发布：此前是 Cloudflare 快速隧道（随进程失效，**已废弃**）；`web/` 可直接静态托管，站点根必须是 `web/` |

**验证现状（2026-09-24 复核）**：Python **268 条测试全绿**（`Ran 268 tests … OK`，exit 0；
170 → 268 为 9-22 后端审查 11 项 + 收尾 4 项修复新增护栏所致）；前端 7 个套件全绿（契约一致性 13 夹具 + 8 指纹样本、
路由 23 项、排序 10 项、纠错规则一致性 10 项、**复活规则一致性 20 项**、写失败原子性 11 项、
工作台回归）；`tools/check_web.py` 25 个 JS + 3 个 CSS、0 问题；`tools/sync_expert.py --check`
（镜像）引擎摘要与 CLI 摘要一致；`tools/validate_library.py` 15 条整库校验通过。
**真实评测（2026-09-23）**：27/27 用例已在平台内以真实会话跑完（5 批、23.79 Credits），
见 `reports/eval-real-sessions.md` 与 `对话记录/`；`reports/eval-log.md` 仍只由跑批器写入。

**浏览器实测（2026-09-20）**：用 CDP 直接驱动本机 Chromium（headless）走查了
**8 个视图 + 4 项交互**：逐页截图、控制台 **error/warn 为 0**、
键盘 `6` 能切到可重试方向（hash 确认为 `#/resurrection`）、390px 窄屏 `scrollWidth == innerWidth`（无横向溢出）；
新增的两个功能都在真实渲染下验证过：立项检查出现「审稿人 2 号」计数陈述与专家质询，
可重试方向展示了 R-015 解除 R-006 的原文依据。证据：`.learnbuddy/artifacts/browser-walkthrough.json`
与 `shots/*.png`。

## 三条硬边界（不能违反）

1. **网页侧零模型调用**：AI 能力全部在 LearnBuddy 专家里；网页只做确定性的召回与视图。
2. **技能脚本不调模型**：`skills/*.py` 的 `build()` 只做确定性把关（取专家 JSON → 规则门禁 →
   规范化 → 违规抛 `ValueError` / 证据不足抛 `SkillRefusal`）。平台实测确认技能脚本调不到模型。
3. **证据引用必须带档案编号 + 原文片段**：没有出处的判断不许出现在任何输出里。
4. **假设不得写成结论**：归因类型只能是 `assumption` / `observed`；日志没给原因时只能是前者。

## 还剩什么（按依赖顺序）

1. **真实评测跑批**（需平台额度）：把 `tools/run_eval.py` 的占位执行器换成专家调用 →
   产出 `reports/eval-log.md`（PPT 第 8 页用它）。**前置已就绪**：六份提示词已冻结，
   `--blind` 守门可用；先测单次 Credits 成本，> 60 则按降级预案压到 6 条开放用例。
2. **材料与部署**：3 分钟视频、作品介绍 PPT、LearnBuddy 对话记录导出；
   把 `web/` 发布成稳定 HTTPS 链接（站点根必须是 `web/`，`file://` 下 ES module 会被 CORS 拦）。
3. 仓库根 `README.md` 里的**团队成员与分工表仍是占位符**，提交前必须替换为真实信息。

## 状态源（谁是权威，别互相打架）

| 内容 | 权威文件 |
| --- | --- |
| 逐任务进度 | `docs/plans/2026-09-19-implementation-plan.md` |
| 作品形态与完工标准 | `docs/product-form.md` |
| 技术选型与取舍 | `docs/technical-notes.md`、`docs/architecture.md` |
| 引用编号 | 项目目录 `参考文献/`（当前 R1–R22，下一条 **R23**） |
| **判断规则的唯一真源** | `prompts/*.md`（参与冻结哈希；镜像副本由 `sync_expert.py` 生成） |
| 提示词冻结记录 | `reports/prompt-freeze.json`（逐份哈希 + 合并哈希） |
| 评测纪律与占位产物的归属 | `reports/README.md`、`reports/archive/placeholder/README.md` |
| 代码审查结论 | `reports/code-review-2026-09-19.md` |
| 网页视觉规格 / 令牌 / 路由与键盘交互规范 | `docs/design-spec-web.md`（路由与键盘见第十节） |

## 常见坑（都真踩过）

- **Bash 工具对含中文的路径不可靠**（历史上任何命令都报 `unexpected EOF`）；
  PowerShell 在本机**不回传 stdout**。取输出要"脚本写文件 + 读文件"。
- **PowerShell 的 `>` 重定向写的是 UTF-16**，读回来是乱码。落盘要用
  `[System.IO.File]::WriteAllText($p, $text, (New-Object System.Text.UTF8Encoding($false)))`。
- 生成类/补丁类脚本**写盘前必须编译检查**；`io.open(newline=...)` 只允许 None / "" / "\n" / "\r" / "\r\n"。
- 被编辑器打开的文件**无法覆盖**（`PermissionError`）→ 另存新版本号。
- **验证脚本自身也要能被证伪**：曾因正则被双重转义报出"0/0 全干净"的假阴性；
  现在 `tests/test_tools_smoke.py` 专门喂一份坏库，要求工具**报错并退 1**。
- **跨端分叉不止在数据契约里，也在"行为约定"里**：规则若 schema 管不到，
  就必须在两端各放一个测试（`tests/*_filter.py` 与 `web/tests/*-rule-parity.mjs`）。
- **提示词改动会作废冻结**：改完必须重跑 `--create-freeze`，
  否则 `tests/test_eval_integrity.py` 会失败——这是刻意的（盲测结果要作废）。
- **改了 `src/rra` 或 `prompts/` 就要刷镜像**：`tools/sync_expert.py --mirror-only`，
  否则 `tests/test_expert_mirror.py` 会失败（镜像里的生成物与仓库逐字节比对）。
- **深链参数别名不一致会静默失效**：立项检查的深链是 `#/projectCheck?q=…`，
  **不是 `?query=`**（`routeToHash` 把 `query` 写成 `q`，`parseHash` 也只认 `q`）。写错不报错，只是检索不跑 ——
  这一条是 2026-09-20 浏览器实测时真实踩到的。
- **占位/桩产出的数字不许落进正式文件**：`reports/eval-log.md` 只能由真实跑批写；
  占位运行只写 `reports/eval-results/*-local.json` 且退出码为 1（旧占位已移入
  `reports/archive/placeholder/`）。
- **测试基准必须可重建**：`reports/contract-parity.json` 由 `tools/make_contract_parity.py`
  生成，`run_tests.py` 每次跑前重建——手写基准会让两端测试拿过期快照静默通过。
