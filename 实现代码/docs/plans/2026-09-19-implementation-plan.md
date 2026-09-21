# 实现计划（2026-09-19）

> **本文件是 2026-09-19 的计划快照，别拿它当当前状态**（当前状态看 `docs/HANDOFF.md`）。
>
> **2026-09-20 更新**：下表 M3 里标注「待平台」的六个 `build()` **已完成**——但不是接平台专家，
> 而是按平台实测结论改为**确定性把关**（取专家 JSON → 规则门禁 → 规范化 → 违规抛 `ValueError` /
> 证据不足抛 `SkillRefusal`），语义判断仍由专家承担；六份提示词已定稿并冻结（`v1.0-frozen`），
> 两个第一梯队创新点（S2 死实验复活、D5 审稿人 2 号）也补上了网页落点。测试数 75 → 170。

> 每个任务 2–5 分钟：**先写测试 → 看它失败 → 实现 → 看它通过 → 提交**。
> 状态：`骨架` = 类与接口已建、方法体未实现；`待做` = 文件都还没建。
> 路径约定：种子与库数据在 `data/`；评测结果与记录表落 `reports/`；一次性脚本放 `tools/`。

## M1 契约（最小可跑前提）

| # | 任务 | 测试 | 状态 |
| --- | --- | --- | --- |
| 1.1 | `contracts.Dim` 九维枚举与中文标签 | `test_dims.py::test_enum_matches_schema` | 骨架 |
| 1.2 | `Archive` / `Library` 等数据类与 `from_dict/to_dict` 往返 | `test_models.py`（4 条） | **已完成**（2026-09-19，先红后绿） |
| 1.3 | `Validator.validate_archive` 必填、枚举、引用格式 | `test_validator.py`（6 条） | **已完成**（2026-09-19） |
| 1.4 | 夹具驱动：4 个 fixtures 与两端校验器结论一致 | `test_fixtures.py`（4 条） | **已完成**（2026-09-19） |
| 1.5 | `Validator.validate_library` 唯一编号与引用可解析 | 随 1.3 实现（重复编号与悬空引用检查） | **已完成**（2026-09-19） |

## M2 库与召回

| # | 任务 | 测试 | 状态 |
| --- | --- | --- | --- |
| 2.1 | `LibraryStore.load/save` JSON 读写（读写前全量校验） | `test_store.py::test_load_save` | **已完成**（2026-09-19） |
| 2.2 | `Deduplicator.key_of` 内容指纹（尝试 + 阻塞点 + 关键条件） | `test_dedup.py`（3 条） | **已完成**（2026-09-19） |
| 2.3 | `LibraryStore.merge` 合并：去重、重编号、`remap_from` | `test_store.py`（2 条） | **已完成**（2026-09-19） |
| 2.4 | `RecallScorer.load_weights` 从 `contracts/scoring.json` 读权重 | `test_scorer.py::test_weights_from_contract` | **已完成**（2026-09-19） |
| 2.5 | `RecallScorer.recall` 召回 + 命中解释 + 空结果如实返回 | `test_scorer.py`（4 条） | **已完成**（2026-09-19） |

## M3 技能（供平台技能调用的脚本）

| # | 任务 | 对应提示词 | 覆盖用例 | 状态 |
| --- | --- | --- | --- | --- |
| 3.1 | `SkillBase.run` 模板方法 + 证据不足即拒绝 | `test_skill_base.py`（3 条） | — | **已完成**（2026-09-19） |
| 3.2 | `ExtractSkill` | `prompts/extract.md` | 1–3 | **待平台**（build 需挂专家；无本地可做部分） |
| 3.3 | `ReverseLookupSkill` | `prompts/reverse_lookup.md` | 4–7、15–17 | **确定性部分已完成**（`apply_clarification_facts`：清缺失字段 + 版本递增）；`build()` 待平台 |
| 3.4 | `ConditionCompareSkill` | `prompts/condition_compare.md` | 4–7、11–14 | **条件门禁已完成**（`verdict`/`differing_dims`，任一维度不同即不得判冲突，5 条测试）；结论语义比对待平台 |
| 3.5 | `InductionSkill` | `prompts/induction.md` | 21–23 | **门槛逻辑已完成**（`eligible_groups`，≥3 条才成组）；假设生成待平台 |
| 3.6 | `ResurrectionSkill`（附录 D.1 的 S2） | `prompts/resurrection.md` | 26 | **候选筛选已完成**（`candidates`：已放弃 + 阻塞点非空）；解除判断待平台 |
| 3.7 | `Reviewer2Skill`（附录 D.1 的 D5） | `prompts/reviewer2.md` | 27 | **有据校验已完成**（`is_grounded`：无 R-### 证据编号的质询一律丢弃）；质询生成待平台 |

## M4 网页

| # | 任务 | 验证方式 | 状态 |
| --- | --- | --- | --- |
| 4.1 | `PersistenceAdapter` + `LibraryStore`（导入合并 / 导出 / storage 事件） | node --check + 人工走查 | **已完成**（2026-09-19） |
| 4.2 | `ContractValidator`（浏览器侧镜像） | 规则与 Python 侧逐条对齐 | **已完成**（2026-09-19） |
| 4.3 | 库视图 + 详情视图 + `CitationRenderer` 引用上标 | 人工走查 | **已完成**（2026-09-19） |
| 4.4 | 立项检查视图（含命中解释；质询部分待平台专家） | 用例 18–20（召回侧已实现） | **召回侧已完成** |
| 4.5 | 失败地图视图（点击格 → 过滤列表） | 人工走查 | **已完成**（2026-09-19） |
| 4.6 | 条件对比矩阵（`dim` 对位高亮） | 用例 25 | **已完成**（2026-09-19） |
| 4.7 | 孵化清单视图（≥3 条才产出假设） | 用例 21–23 | **已完成**（2026-09-19） |
| 4.8 | `RefutationController` 反驳入口（append-only） | 人工走查 | **已完成**（2026-09-19） |

## M5 评测与材料

| # | 任务 | 产物路径 | 状态 |
| --- | --- | --- | --- |
| 5.1 | `CaseRegistry.default()` 登记 27 条用例 | `test_cases.py`（4 条） | **已完成**（2026-09-19） |
| 5.2 | `EvalRunner` 跑批并落盘 | `test_runner.py`（4 条） | **已完成**（2026-09-19） |
| 5.3 | `EvalReport.to_markdown_table()` 生成记录表 | `test_runner.py` | **已完成**（2026-09-19） |
| 5.4 | `SeedGenerator` 造 12–15 条种子数据（含 S2 伏笔） | `data/library.seed.json`（14 条，已同步 `web/data/`） | **已完成**（2026-09-19） |
| 5.5 | `MarkdownExporter` 导出档案与避坑清单 | `test_export.py`（2 条） | **已完成**（2026-09-19） |
| 5.6 | `tools/validate_library.py` 校验并同步到 `web/data/` | 同步前后条数一致 | 骨架 |

## 提交纪律

- 每个任务通过后立即提交，提交信息写清「任务号 + 行为变化」。
- 跳过测试写出来的实现，先删掉再按 TDD 重写。
- `reports/` 必须入库（那是 55% 分数的证据）；`data/library.local.json` 与任何 `.local.json` 不入库。

## 进度汇总（2026-09-19 更新）

- 全量测试：**75 条全部通过，零 skip**（含 7 条为审查后发现的新规则补的测试）。
- 已实现：契约（模型/校验/枚举）、库（读写/去重/合并）、召回、评测（用例/跑批/记录表/盲测守门）、种子数据、导出、网页全部（数据层 + 六视图）、技能基座与五个技能的确定性部分、三个命令行工具。
- 仍待平台：六个技能的 `build()`（需把提示词挂到 LearnBuddy 专家上）与 `ReverseLookupSkill.update_after_clarification`（需语义重判）。
- 闭环冒烟：新档案导入合并后，用同一阻塞点召回**命中且排第一**。
- **两端契约一致性测试**：`web/tests/contract-parity.mjs`（Node 加载浏览器侧校验器，对同一批夹具与指纹样本逐条比对两端结论）；一键入口 `python run_tests.py`。
- 代码审查（分四个角度并行）结论与修复清单：`reports/code-review-2026-09-19.md`（22 条已修、8 条已知未修）。
- 状态入口：`docs/HANDOFF.md`。
