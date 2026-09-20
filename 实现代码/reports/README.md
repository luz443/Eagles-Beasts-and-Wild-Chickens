# reports/ 评测与证据目录

**这个目录必须入库。** 评委看的「实测结果」与「AI 工具使用」两项证据都在这里。

| 路径 | 内容 | 谁产生 |
| --- | --- | --- |
| `reports/eval-results/<日期>.json` | 一次跑批的逐条结果 | `tools/run_eval.py` |
| `reports/eval-log.md` | 记录表（命中 / 引用正确 / 无依据归因 / 结论） | `EvalReport.to_markdown_table()` |
| `reports/exports/` | 导出的单条档案报告与避坑清单 | `MarkdownExporter` |
| `reports/iteration-log.md` | 那一轮真实迭代（初版误判 → 发现 → 改流程 → 复测） | 手工记录，当天写 |

## 命名与口径

- 文件名带日期与提示词版本：`2026-09-24-promptv0.3-open.json`。
- `*.local.json` 不入库（本地试跑，随时可丢）。
- 盲测结果单独放 `reports/eval-results/*-blind.json`，冻结时间同步记进 `docs/plans/` 的计划文件。
