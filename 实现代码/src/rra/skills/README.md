# skills/ 技能目录

每个技能类对应平台侧的一份提示词，配对关系必须保持一致（新增技能时两处都要加）。

| 技能类 | 提示词 | 契约产出 | 覆盖用例 |
| --- | --- | --- | --- |
| `ExtractSkill` | `prompts/extract.md` | `Archive` | 1–3 |
| `ReverseLookupSkill` | `prompts/reverse_lookup.md` | `Link` + `EvidenceRef` | 4–7、15–17 |
| `ConditionCompareSkill` | `prompts/condition_compare.md` | `Link.same` / `Link.diff` | 4–7、11–14 |
| `InductionSkill` | `prompts/induction.md` | 待验证假设清单（H 编号） | 21–23 |
| `ResurrectionSkill` | `prompts/resurrection.md` | 可重试方向清单 | 26（待补） |
| `Reviewer2Skill` | `prompts/reviewer2.md` | 带编号的质询 | 27（待补） |

## 共同约束（写在 `base.py` 里，各技能不得各自实现）

1. 输出必须通过 `Validator` 的契约校验，否则整体失败，不留半成品。
2. 证据不足时抛 `SkillRefusal`，并给出缺失字段。
3. 提示词文件的版本行是盲测冻结的锚点，冻结后不得再改。
