# 相关工作与可借鉴文献（第一轮）

> 检索日期：2026-09-19　检索工具：WebSearch（web-access skill 规定的发现工具；未使用浏览器 CDP）
> 覆盖 6 条借鉴轴；每条都给出链接，可自行复核。**未核实的条目单列在文末，不得直接引用。**

## 轴一　负结果与出版偏倚（我们的问题论证）

| 来源 | 核心要点 | 我们怎么用 |
| --- | --- | --- |
| [「The ugly side of science」报道（UIC）](https://grad.uic.edu/news-stories/illuminating-the-ugly-side-of-science-fresh-incentives-for-reporting-negative-results/) | 「文件抽屉问题」由 Rosenthal 于 1979 年提出；1990–2007 年论文中含阳性结论的比例上升 22%，到 2007 年 85% 的论文为阳性结果；2022 年法国调查：81% 的研究者产生过有用的负结果、75% 愿意发表，但只有 12.5% 有机会发表 | PPT 第 2 页的问题论证用这三个数字；视频开场一句话 |
| [Journal of Trial & Error](https://grad.uic.edu/news-stories/illuminating-the-ugly-side-of-science-fresh-incentives-for-reporting-negative-results/)（2020 创刊） | 主编明确：只收「方法严谨但结果出乎意料」的，不收「做得糟糕、什么都没发现」的 | 明确我们的收录标准：条件可比、方法可复述；避免作品被当成垃圾桶 |
| [PLOS「Missing Pieces」合集](https://blogs.upstate.edu/library/2015/03/19/publish-negative-results-really-yes-really/)、[可发表负结果的渠道盘点（Editage）](https://www.editage.com/insights/how-can-i-publish-negative-results) | 已有 JNRBM、JASNH、microPublication、Wellcome Open Research、F1000Research、预印本等渠道 | 竞品与生态综述：这些渠道面向**已完成的完整研究**，没有覆盖「组内日常尝试」这一层——正是我们的空位 |
| [Negative equity（PMC11381924）](https://pmc.ncbi.nlm.nih.gov/articles/PMC11381924/) | 除了负结果本身，**缺失的元数据**同样造成损害（ARRIVE 报告指南常被忽略；公共存档中关键元数据缺失、同一特征用不同术语描述） | 支撑我们「缺失信息」字段的正当性：不只是「没做成」，而是「连条件都没记全」 |
| [「失败」的科研去哪儿了?（华东师大）](https://www.ecnu.edu.cn/info/1095/59649.htm) | 中文语境同题讨论；引用波普尔「证伪常常被视为一位科学家的失败」；JNRBM 2002 年创刊时的质疑与回应 | 中文 PPT 的引语来源；本土化叙事，避免全篇英文引用 |

## 轴二　案例推理（CBR）：我们机制的经典理论框架

| 来源 | 核心要点 | 我们怎么用 |
| --- | --- | --- |
| [Aamodt & Plaza 的 CBR 四阶段循环（多处引用）](https://www.sciencedirect.com/science/article/abs/pii/S0957417422024794) | Retrieve → Reuse → Revise → Retain：检索相似案例、复用其解、必要时修订、把新案例存回案例库 | 把「入库即反查 + 澄清后更新 + 留档」直接表述为经典 CBR 循环；实现命名也用 recall/reuse/revise/retain，答辩时可以说「我们落在 1994 年就成熟的框架里」 |
| [CBR 入门（Northwestern 讲义）](https://www.cs.northwestern.edu/courses/325/readings/cbr-intro.html) | **「如果改后的方案失败，系统也会把它存下来，并注明下次要注意什么」** | 这是我们做「失败档案 + 归因假设 + 适用边界」的**理论出处**，可直接引一句话 |
| [Empowering Explainable AI through CBR（UCL）](https://discovery.ucl.ac.uk/id/eprint/10214905/7/Wijekoon_Empowering%20Explainable%20Artificial%20Intelligence%20Through%20Case-Based%20Reasoning_VoR.pdf) | 案例表示三种形式：特征向量、结构化、文本；三者各有取舍；案例库是知识容器并可演化 | 支撑我们「结构化 dim 枚举 + 文本叙述并存」的档案模型；也解释了为什么必须有枚举（结构化才能对位比较） |

## 轴三　归因与证据（我们「禁止无依据归因」的学术对应）

| 来源 | 核心要点 | 我们怎么用 |
| --- | --- | --- |
| [Automatic Evaluation of Attribution by LLMs（AttrScore）](https://lacuna.tiptreesystems.com/paper/automatic-evaluation-of-attribution-by-large-language-models/art_5bb9cd3d07124206a8edfd2773b635f6) | 把「引用是否真的支持结论」三分类：Attributable / Extrapolatory / Contradictory；**实测生成式搜索引擎中只有约 52% 的陈述被所引文献完全支持** | ① 我们的三态判定（同一问题 / 条件不同 / 真冲突）与它同构，可引；② 52% 这个数字非常适合放进 PPT，说明「有引用」不等于「有依据」；③ Extrapolatory 率 ≈ 我们的「越界归因率」 |
| [FActScore](https://slavadubrov.github.io/blog/2026/05/10/rag-evaluation-metrics/)（Min et al., EMNLP 2023） | 长文本拆成原子事实，逐条核查是否被支持，报支持比例 | 用例判据借用「原子化 + 逐条核查」，避免「整体看起来对」 |
| [ALCE](https://slavadubrov.github.io/blog/2026/05/10/rag-evaluation-metrics/)（Gao et al., EMNLP 2023） | 用 NLI 实现 citation precision / citation recall | 把我们 7.3 的「引用正确率」升级为 precision + recall 两个口径，实现成本不变、更严谨 |
| [NoMIRACL](https://slavadubrov.github.io/blog/2026/05/10/rag-evaluation-metrics/)（Findings of EMNLP 2024）、[事实性综述](https://arxiv.org/html/2310.07521v1) | 拒绝回答（abstention）需要单独评测：该拒答时是否拒答、拒答是否过度 | 支撑我们的负向用例（诱导幻觉、证据不足必须拒绝），并给出评测口径 |

## 轴四　条件维度与证据分级（我们「条件比较 + 边界 + 置信度」的来源）

| 来源 | 核心要点 | 我们怎么用 |
| --- | --- | --- |
| [GRADE 与 PICO（NHMRC 说明）](https://www.nhmrc.gov.au/file/23340/download?token=WCPzDa7m)、[GRADE 手册](https://book.gradepro.org/guideline/principles-for-assessing-the-certainty-of-interventions) | 问题用 PICO 结构化；确定性分四档（high / moderate / low / very low）；降级维度：风险偏倚、不一致性、**间接性**、不精确性、发表偏倚；结论按**证据体**而非单条研究评确定性 | ① 我们的 `boundary` 字段就是「间接性」的落地；② `confidence` 与 GRADE 四档对应（我们在文档里写明映射关系，避免被问时答不出）；③ 「按证据体评级」正是我们归纳孵化的依据 |
| [GRADE 证据摘要表（Evidence Profile / Summary of Findings）](https://prhe.ucsf.edu/sites/g/files/tkssra341/f/GRADE-%20Assessing%20the%20Quality%20of%20Evidence.pdf) | 每个结局一行：效应量、确定性、升降级理由，要求透明写下理由 | 档案详情页的版式参考：结论 + 适用条件 + 确定性 + 降级理由四栏 |
| CHARMS 清单（经 Cochrane 摘要转引） | 预测模型研究的偏倚风险清单（结局、候选预测因子、缺失数据、模型开发） | 给「条件维度」一个现成清单来源，用于补充我们九维之外的可能维度 |

## 轴五　结构化主张与可引用编号（对应 S1 可引用失败记录、对比矩阵）

| 来源 | 核心要点 | 我们怎么用 |
| --- | --- | --- |
| [Nanopublication（Groth, Gibson & Velterop, 2010；PeerJ 综述转引）](https://peerj.com/articles/cs-1159) | 最小可归属的知识单元 = assertion（断言）+ provenance（来源）+ publicationInfo（元信息）三部分；用 Trusty URI 做内容寻址与签名；**「需要时撤回，但从不删除」** | ① 我们的档案三段式与它同构，可直说「对齐 nanopublication 结构」；② 「撤回不删除」正是「反驳我按钮新建档案而不覆盖原判断」的理论依据；③ 引用格式 `R-013@v2` 与它的内容寻址思路一致 |
| [ORKG（Jaradeh et al., 2019；综述转引）](https://arxiv.org/pdf/2402.08565v2) | 结构化描述论文并支持**对比**（约 25,000 篇、1,500 组对比） | 条件对比矩阵不是我们发明的，是已有范式；我们的差异是把它下沉到「组内日常尝试」这一层 |
| [Semantic units（PMC11131308）](https://www.ncbi.nlm.nih.gov/pmc/articles/pmc11131308/) | 把知识图切成语义单元，claim 级可引用、可归属 | 我们 `evidence_refs` 的实现参考：quote 必须带片段，避免只给编号 |

## 轴六　ML 领域的复现性（我们演示场景的直接背书）

| 来源 | 核心要点 | 我们怎么用 |
| --- | --- | --- |
| [Kapoor & Narayanan, Patterns 2023, 4(9):100804](https://pubmed.ncbi.nlm.nih.gov/37720327/)（DOI 10.1016/j.patter.2023.100804） | 17 个领域、294 篇论文受数据泄漏影响；给出 **8 类泄漏分类**；提出 **model info sheets**（模型信息表）逐类自查；内战预测案例中修正泄漏后复杂模型不再优于逻辑回归 | ① 在我们的演示领域，「元数据不全导致结论失效」有顶刊证据；② model info sheets 与我们「条件维度」是同类物，可引为「业界已在做」；③ 8 类泄漏清单可作为立项检查的扩展项；④ 给「条件比较」一个正经来源 |
| [Serra-Garcia & Gneezy, Sci. Adv. 2021（经 PubMed 参考文献转引）](https://pubmed.ncbi.nlm.nih.gov/37720327/) | 不可复现的论文被引次数反而更多 | 说明现行激励在鼓励坏实践——引出「负结果资产化」的必要性 |
| [催化剂 ML 只用阳性数据的报道（UIC）](https://grad.uic.edu/news-stories/illuminating-the-ugly-side-of-science-fresh-incentives-for-reporting-negative-results/) | 研究者从 1,866 篇文献与专利中挖数据训练模型，但「人们只收集了好数据，失败了就不报告」，导致模型给出过度乐观的性能预测 | 一句话说明「不给负结果留位置，AI 也会被带偏」，比抽象论证有力 |

## 三条可直接落地的改动建议

1. **档案三段式的命名对齐 nanopublication**：assertion / provenance / publicationInfo。零成本，答辩时可直接说「结构上对齐了成熟的数据发表范式」。
2. **引用正确率拆成 citation precision + citation recall**（对齐 ALCE 口径）：实现成本不变，但口径更严谨，也更能证明「不是关键词匹配」。
3. **在文档里写明 `confidence` 与 GRADE 四档的映射**：我们保留三档（原型够用），但把映射关系写清楚，被问到时能立刻回答，并说明「四档留作未来工作」。

## 需要额外准备的一句答词

评委会问「已经有人做负结果平台了，你们的不同在哪」。可用三条差异回答：
① 那些渠道面向**已完成的完整研究**（期刊、合集、预印本），我们面向**组内日常尝试**，颗粒度更细；
② 它们不做**跨条目的条件比较**，我们按九个维度对位并判「真冲突 / 条件不同」；
③ 它们没有**入库即反查**这个动作，我们是主动拦住，而不是等人来检索。

## 本轮未核实（仅模型知识，**不得直接引用**）

| 条目 | 状态 |
| --- | --- |
| NAS-Bench 系列把失败架构也记录进搜索空间（可作「工业界失败经验库」类比） | 未检索核实 |
| 电子实验记录本（ELN）与隐性知识捕获的实证研究 | 未检索核实 |
| NASA LLIS 等「经验教训库」的工业实践 | 未检索核实 |
| 团队共享记忆（transactive memory system）相关研究 | 未检索核实 |
| 中文数据库（知网、万方）与引文追溯 | 本轮未检索 |

下一轮若要做，应把上面五项逐一核实后再进 PPT；其中 NAS-Bench 与 ELN 两项最有可能出现「别人已经做过类似系统」，值得优先查清。
