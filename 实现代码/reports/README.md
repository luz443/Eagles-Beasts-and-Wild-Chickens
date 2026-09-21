# reports/ 评测与证据目录

**这个目录必须入库。** 评委看的「实测结果」与「AI 工具使用」两项证据都在这里。

| 路径 | 内容 | 谁产生 |
| --- | --- | --- |
| `reports/eval-results/<日期>-<模式>.json` | 一次跑批的逐条结果 | `tools/run_eval.py` |
| `reports/eval-log.md` | 记录表（命中 / 引用正确 / 无依据归因 / 结论） | `EvalReport.to_markdown_table()`，**仅真实跑批** |
| `reports/prompt-freeze.json` | 六份提示词的冻结哈希（含逐份哈希与合并哈希） | `tools/run_eval.py --create-freeze ... --prompts-dir prompts` |
| `reports/contract-parity.json` | 两端契约一致性的期望快照 | `tools/make_contract_parity.py`（`run_tests.py` 每次重建） |
| `reports/archive/placeholder/` | **占位产物**：没有调用专家的运行结果，数字不可引用 | 见该目录 `README.md` |
| `reports/exports/` | 导出的单条档案报告与避坑清单 | `MarkdownExporter` |
| `reports/iteration-log.md` | 那一轮真实迭代（初版误判 → 发现 → 改流程 → 复测） | 手工记录，当天写 |

## 命名与口径

- 文件名带日期与提示词版本：`2026-09-24-v1.0-frozen-open.json`。
- `*.local.json` 与 `*-placeholder-*.json` 不入库（服务器端已由 `.gitignore` 拦住）。
- 盲测结果单独放 `reports/eval-results/*-blind.json`，冻结时间同步记进 `docs/plans/` 的计划文件。

## 两条硬纪律

1. **占位数据不许冒充结果。** 没有真实执行器时 `tools/run_eval.py` 退出码为 1，
   只写 `*-local.json`，**绝不覆盖** `eval-log.md`；档案进 `archive/placeholder/`。
2. **提示词冻不住，第 8 页就是假的。** `eval-log.md` 只能由「冻结之后跑出来的结果」生成；
   改过提示词就要重新冻结，并明确知道此前的盲测结果作废。
   `tests/test_eval_integrity.py` 会逐份复核冻结哈希，改了没重新冻结就会失败。
