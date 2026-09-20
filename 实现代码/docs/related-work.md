# 可借鉴文献摘要（一页版，供 PPT 引用）

> 完整版见 `docs/research/report.md`（含全部链接）。本文只保留**能直接写进 PPT 或用于答辩**的部分。

## 三个可以直接用的数字

| 数字 | 出处 | 用途 |
| --- | --- | --- |
| 81% 的研究者产生过有用的负结果，只有 **12.5%** 有机会发表（2022 年法国调查） | [UIC 报道](https://grad.uic.edu/news-stories/illuminating-the-ugly-side-of-science-fresh-incentives-for-reporting-negative-results/) | PPT 第 2 页、视频开场 |
| 到 2007 年，**85%** 已发表论文为阳性结果（1990–2007 间阳性结论占比上升 22%） | 同上 | 说明问题在恶化 |
| 生成式搜索中只有约 **52%** 的陈述被所引文献完全支持 | [AttrScore](https://lacuna.tiptreesystems.com/paper/automatic-evaluation-of-attribution-by-large-language-models/art_5bb9cd3d07124206a8edfd2773b635f6) | 说明「有引用」不等于「有依据」，即我们为什么强制带原文片段 |

## 四句可以直接引的话

1. **CBR 讲义**：「如果改后的方案失败，系统也会把它存下来，并注明下次要注意什么。」——[来源](https://www.cs.northwestern.edu/courses/325/readings/cbr-intro.html)
2. **Nanopublication**：「需要时撤回，但从不删除。」——[来源](https://peerj.com/articles/cs-1159)（对应我们的「反驳不覆盖原判断」）
3. **Kapoor & Narayanan 2023**：17 个领域、294 篇论文受数据泄漏影响，提出 model info sheets 逐类自查。——[来源](https://pubmed.ncbi.nlm.nih.gov/37720327/)
4. **华东师大报道**引波普尔：「证伪常常被视为一位科学家的失败。」——[来源](https://www.ecnu.edu.cn/info/1095/59649.htm)

## 与既有工作的三条差异（应对「别人做过了」）

1. 既有渠道（期刊 / 合集 / 预印本）面向**已完成的完整研究**；我们面向**组内日常尝试**，颗粒度更细。
2. 它们不做**跨条目条件比较**；我们按九个维度对位，并区分「真冲突」与「条件不同」。
3. 它们没有**入库即反查**——我们是主动拦住，而不是等人来检索。

## 一个可以顺手对齐的命名

把档案三段式命名为 **assertion / provenance / publicationInfo**，与 nanopublication 一致；答辩时可说「结构上对齐了成熟的数据发表范式」。

## 三条基于文献的具体改动

1. 引用正确率拆成 **citation precision + citation recall**（对齐 ALCE）。
2. 文档里写明 `confidence` 三档与 **GRADE 四档**的映射关系。
3. 立项检查可扩展 **8 类数据泄漏清单**（来自 Kapoor & Narayanan）。
