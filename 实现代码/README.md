# 研究复盘助手 · 实现代码

LearnBuddy 专家（AI 入口）+ 静态网页（使用入口）的工程骨架。

> 当前状态：**框架骨架**。所有类与接口已定义，方法体一律为 `raise NotImplementedError`
> 或 `throw new Error('not implemented')`，尚无业务实现。

## 目录

| 路径 | 作用 |
| --- | --- |
| `docs/HANDOFF.md` | **先看这个**：当前进度、剩余工作、三条硬规则 |
| `docs/architecture.md` | 技术路线、选型对比、评测口径、成本估算、风险与降级 |
| `docs/plans/` | 逐任务实现计划（TDD 顺序，每任务 2–5 分钟） |
| `data/` | 数据真源：种子数据与库文件 |
| `reports/` | 评测结果、记录表、迭代留痕（**必须入库**） |
| `tools/` | 命令行入口，不含业务逻辑 |
| `prompts/` | 平台侧技能提示词（与 `src/rra/skills/` 一一配对） |
| `docs/record-format.md` | 档案字段规范（对外可移植版本） |
| `contracts/` | 数据契约：JSON Schema 与维度枚举，专家与网页共用的唯一接口 |
| `src/rra/` | Python 侧：契约、库、召回、技能、评测、种子数据、导出 |
| `web/` | 静态网页：库、检索、立项检查、对比矩阵、孵化清单、导入导出 |
| `tests/` | 契约与确定性逻辑的测试（标准库 unittest 风格，无第三方依赖） |

## 环境

- Python：`C:\Users\Lenovo\.workbuddy\binaries\python\envs\default\Scripts\python.exe`
- 运行测试：`<python> -m pytest tests -q`（尚未实现，当前只建骨架）
- 网页：零构建，直接静态托管 `web/` 目录即可（无 node_modules、无打包步骤）

## 两条硬约束（来自设计方案）

1. 不接任何第三方模型：AI 能力只来自 LearnBuddy 专家 + 技能。
2. 不依赖未确认的数据通路：专家与网页之间以一份结构化文件传递，通路可替换。
