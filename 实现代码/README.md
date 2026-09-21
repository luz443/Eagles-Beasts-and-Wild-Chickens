# 研究复盘助手 · 实现代码

LearnBuddy 专家（AI 入口）+ 静态网页（使用入口）的工程实现。

> 当前状态：**可用**。契约层、库、召回、评测、种子数据、导出、六个技能的确定性把关、
> 八个网页视图、专家包（含 6 技能 + 确定性 CLI）均已落地并测试。
> `python run_tests.py` 跑 **170 条 Python 测试 + 7 个前端套件**，全绿。

## 目录

| 路径 | 作用 |
| --- | --- |
| `docs/HANDOFF.md` | **先看这个**：当前进度、剩余工作、三条硬规则 |
| `docs/architecture.md` | 技术路线、选型对比、评测口径、成本估算、风险与降级 |
| `docs/product-form.md` | 作品最终形态、五项交付物、四条完工标准 |
| `docs/design-spec-web.md` | 网页视觉规格：令牌、配色、路由与键盘交互 |
| `docs/record-format.md` | 档案字段规范（对外可移植版本） |
| `docs/plans/` | 逐任务实现计划（TDD 顺序） |
| `data/` | 数据真源：种子数据与库文件 |
| `reports/` | 评测结果、提示词冻结记录、迭代留痕（**必须入库**） |
| `tools/` | 命令行入口，不含业务逻辑 |
| `prompts/` | 六份技能提示词：**判定规则的唯一真源**，参与盲测冻结哈希 |
| `expert/` | 专家包镜像（可直接安装；生成物由 `tools/sync_expert.py` 产出） |
| `contracts/` | 数据契约：JSON Schema 与维度枚举，专家与网页共用的唯一接口 |
| `src/rra/` | Python 侧：契约、库、召回、技能、评测、种子数据、导出 |
| `web/` | 静态网页：经验库、详情、立项检查、失败地图、条件对比矩阵、孵化清单、可重试方向、导入导出 |
| `tests/` | 契约、确定性逻辑与交付纪律的测试（标准库 unittest，无第三方依赖） |

## 环境与常用命令

- Python：任意 **3.11+**（除标准库外无运行时依赖）。本机隔离环境示例：
  `<python>` 指到你的 Python 解释器即可，例如
  `C:\Users\<你>\.workbuddy\binaries\python\envs\default\Scripts\python.exe`。
- Node.js：仅测试期需要（跑 `web/tests/*.mjs`），非运行依赖。

| 想做的事 | 命令 |
| --- | --- |
| 跑一遍全部验证 | `<python> run_tests.py` |
| 本地看网页 | 在 `web/` 下起 `<python> -m http.server 8123`，打开 `http://127.0.0.1:8123/index.html` |
| 深链直达 | 网址后加 `#/resurrection`、`#/map`、`#/incubation`、`#/detail/R-003`；检索也可带 `#/library?q=显存&sort=confidence` |
| 键盘操作 | `1`–`6` 切视图、`/` 定位检索框、`Esc` 关闭证据浮层 |
| 重新生成种子数据 | `<python> tools/make_seed.py` |
| 校验库并同步给网页 | `<python> tools/validate_library.py` |
| 刷新专家包镜像的生成物 | `<python> tools/sync_expert.py --mirror-only` |
| 校验专家包与仓库一致 | `<python> tools/sync_expert.py --check` |
| 冻结六份提示词 | `<python> tools/run_eval.py --create-freeze reports/prompt-freeze.json --prompts-dir prompts --version v1.0-frozen --by <名字>` |
| 跑评测（当前无真实执行器 → 退出码 1） | `<python> tools/run_eval.py`；显式占位加 `--placeholder` |

## 三条硬约束

1. **不接任何第三方模型**：AI 能力只来自 LearnBuddy 专家 + 技能；网页侧零模型调用。
2. **不依赖未确认的数据通路**：专家与网页之间以一份结构化文件传递，通路可替换。
3. **技能脚本不调模型**：`skills/*.py` 的 `build()` 只做确定性把关（取专家 JSON → 规则门禁 →
   规范化 → 违规抛错 / 证据不足拒绝），语义判断由专家承担。

## 交接与状态

**接手的人先读 `docs/HANDOFF.md`**：那里是进度、剩余工作、验证现状与常见坑的唯一入口。
