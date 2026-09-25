# 研究复盘助手 · 真实评测首跑报告（用例 15 / 21 / 18）

- 跑批时间：2026-09-23 21:5x（GMT+8）
- 专家包：`%USERPROFILE%\.learnbuddy\plugins\marketplaces\my-experts\plugins\research-retro-assistant`
- 引擎入口：`bin/rra_cli.py`（纯标准库，不联网、不调模型）
- 本轮**未写入任何档案/库文件**；仓库既有文件全部未改动（见文末「无写入证据」）

## 0. 库文件说明（本轮的口径）

CLI 需要一个显式库文件参数。本轮同时测了两个库，**以工作区库为准**，包内样例库作对照：

| 代号 | 路径 | 记录数 | 最后修改 | 含 `conditions` |
| --- | --- | --- | --- | --- |
| **工作区库（口径基准）** | `实现代码/data/library.seed.json` | 15 | 2026-09-22 20:02 | 有 |
| 包内样例库（对照） | 专家包 `bin/samples/library.seed.json` | 14 | 2026-09-19 20:58 | 无 |

> 说明：两库并非同一份数据。工作区库新增了 R-015，并给记录补了 `conditions`，还修正了 R-002 的归因类型（详见第 4 节）。

---

## 1. 用例 15（库内无相关经验）— **通过**

### ① 调用的命令原文

```bash
cd "%USERPROFILE%/.learnbuddy/plugins/marketplaces/my-experts/plugins/research-retro-assistant" && "%USERPROFILE%/.workbuddy/binaries/python/envs/default/Scripts/python.exe" bin/rra_cli.py recall "<库文件>" "光学字符识别"
```

三个变体、两个库各跑一遍（共 6 次），命令形态相同，仅替换 `<库文件>` 与查询词：

```bash
... bin/rra_cli.py recall "实现代码/data/library.seed.json" "光学字符识别"
... bin/rra_cli.py recall "实现代码/data/library.seed.json" "OCR"
... bin/rra_cli.py recall "实现代码/data/library.seed.json" "手写数字识别"
```

### ② 输出的关键字段

工作区库：

```json
{ "ok": true, "query": "光学字符识别", "count": 0, "hits": [],
  "note": "宁少不凑：没有区分度的查询返回空列表，不要据此编造命中" }
```

包内样例库、以及 `OCR` / `手写数字识别` 两个变体，输出形态完全一致：`count: 0`、`hits: []`。

### ③ 判定与依据

- **依据（CLI 输出）**：`count = 0`、`hits = []`，且 note 明写「宁少不凑……不要据此编造命中」。
- **依据（库内容核对）**：工作区库 15 条记录的 `blocker` / `attempt` / `observation` / `boundary` 逐条核对，主题分别为——长序列显存（R-001/002/003/005）、梯度累积成功经验（R-004）、70B 权重放不下（R-006）、ring-attention 数值稳定性（R-007）、去重副作用（R-008）、学习率发散（R-009）、kv-cache 并发（R-010）、fp16 溢出（R-011）、数据配比（R-012）、数据版本回归（R-013）、论文复现差距（R-014）、量化后激活超限（R-015）。**无一涉及光学字符识别 / OCR / 手写数字识别**。
- **依据（专家包规则）**：`skills/reverse-lookup/SKILL.md` 拒绝条件第 1 条——「`recall` 返回空 → 明说「库内无同类记录」，不要用你自己的联想补一个"相似记录"」。
- **阳性对照（证明不是引擎一律返回空）**：`recall "<库文件>" "显存不足"` 返回 `count = 5`，命中 R-003(10.0) / R-002(7.0) / R-001(6.0) / R-005(6.0) / R-010(3.0)。可见空召回是查询主题真的不存在，而非引擎故障。

### ④ 结论

**通过**。明确判定「库内无 OCR 相关记录」，**未编造任何档案编号或原文片段**。

---

## 2. 用例 21（孵化门限）— **通过（门槛达到，H 假设已列出并标注强度）**

### ① 调用的命令原文

```bash
cd "%USERPROFILE%/.learnbuddy/plugins/marketplaces/my-experts/plugins/research-retro-assistant" && "%USERPROFILE%/.workbuddy/binaries/python/envs/default/Scripts/python.exe" bin/rra_cli.py induction-candidates "<库文件>"
```

辅助（取各阻塞点记录数，确定性输出）：

```bash
... bin/rra_cli.py blocker-digest "<库文件>"
```

### ② 输出的关键字段

`induction-candidates`（工作区库与包内样例库结果一致）：

```json
{ "ok": true, "group_count": 1,
  "groups": { "长序列训练显存不足": ["R-001", "R-002", "R-003", "R-005"] },
  "note": "只给达到门槛（同一阻塞点 >= 3 条）的分组；写假设由专家完成" }
```

`blocker-digest` 给出的各阻塞点记录数（工作区库）：

| 阻塞点 | 记录数 | 记录编号 |
| --- | --- | --- |
| **长序列训练显存不足** | **4** | R-001、R-002、R-003、R-005 |
| 无（此条为已解决的成功经验） | 1 | R-004 |
| 单卡放不下 70B 的权重与优化器状态 | 1 | R-006 |
| ring-attention 的数值稳定性难以对齐 | 1 | R-007 |
| 数据量下降的损失大于质量收益 | 1 | R-008 |
| 学习率过大导致发散 | 1 | R-009 |
| 长输入下 kv-cache 显存挤占并发 | 1 | R-010 |
| fp16 溢出导致 NaN | 1 | R-011 |
| 领域与通用此消彼长 | 1 | R-012 |
| 数据版本变更引入回归 | 1 | R-013 |
| 论文关键细节未披露（数据划分与后处理） | 1 | R-014 |
| 量化加载后长序列激活值仍超 24G | 1 | R-015 |

> 门槛（≥3 条）**只有 1 个阻塞点达到**：长序列训练显存不足（4 条）。其余 11 个阻塞点均为 1 条，**不立假设**。

### ③ 判定与依据（逐条带编号 + 原文片段）

组内 4 条原文（引用自工作区库）：

- **R-001**（进行中 / conf=low / attribution=`assumption`）
  - `attempt`：「直接用 batch=32 跑 seq_len=2048 的微调」
  - `observation`：「第 40 step 触发 CUDA OOM」
  - `attribution.text`：「**怀疑** batch=32 在 seq_len=2048 下激活值超出 24G」
  - `conditions`：`seq_len=2048, batch=32, hardware=RTX 4090（24G）, precision=bf16, stage=微调`
  - `missing_info`：`["micro-batch 实际值", "是否启用 flash-attention"]`
- **R-002**（进行中 / conf=medium / attribution=`assumption`）
  - `observation`：「512 下稳定，放大回 2048 又 OOM」
  - `attribution.text`：「**怀疑**序列长度回到 2048 后注意力开销随长度平方增长（**未做分解实验验证**）」
  - `conditions`：`seq_len=512（稳定） / 2048（OOM）, batch=4, hardware=RTX 4090（24G）`
- **R-003**（已绕过 / conf=high / attribution=`observed`）
  - `attempt`：「开启 gradient checkpointing 换显存」
  - `observation`：「显存降到 19G，单步耗时约 2.4 倍，能跑但极慢」
  - `conditions`：`seq_len=2048, hardware=RTX 4090`
- **R-005**（进行中 / conf=medium / attribution=`observed`）
  - `observation`：「仍然 OOM；累积并不能降低单步激活峰值」
  - `attribution.text`：「梯度累积不减少单步激活显存，对激活主导的 OOM 无效」
  - `conditions`：`seq_len=4096, model=Llama-3-8B, micro_batch=4, batch=32（等效）`
  - `missing_info`：`["4096 下 flash-attention 是否开启"]`

**共同点（可落到条件维度）**：`hardware` 一致（单卡 RTX 4090 / 24G）、`stage` 一致（长序列微调）、差异全在 `seq_len`（2048 / 512→2048 / 2048 / 4096）——即「单卡 24G 下，seq_len 增长触发的显存不足」。

**反例检查（按 `skills/induction/SKILL.md` 步骤 2、拒绝条件第 3 条）**：组内**无**结论相反的反例；R-003 只说明该阻塞**可被绕过**（显存降到 19G），并不推翻阻塞本身。但有两处**必须标注的削弱项**，不作为「一致支持」处理：
1. R-001、R-002 的 `attribution.type = assumption`（原文分别写「怀疑」「未做分解实验验证」）——机制部分**未被日志证实**；
2. R-001、R-005 的 `missing_info` 未闭合（flash-attention 开关、micro-batch 实际值）。

**同族但不得并入计数的旁证**：R-015 的 `blocker` 是「量化加载后长序列激活值仍超 24G」，与组内阻塞点**字面不同**，故 CLI 精确分组不含它；其 `transferable` 写「对长序列激活开销无效（与 R-005 的结论方向一致）」，方向一致但属另一阻塞点，**不计入 H1 支持条数**。

### H 假设清单

**H1（候选）**：在**单卡 24G + bf16 的长序列微调**下，显存瓶颈由 `seq_len` 增长带来的**激活/注意力开销**主导，而非权重与优化器状态；因此**降 batch、加梯度累积无效**，只有削减激活的手段（如 gradient checkpointing）才生效。

- **依据档案编号**：R-001、R-002、R-003、R-005（4 条）
- **反例**：0 条（组内无相反结论）
- **验证方法**：固定 `model` / `precision` / `hardware`，做一次 `seq_len` 扫描（512 / 1024 / 2048 / 4096），分别记录权重、优化器状态、激活三类显存峰值。
- **判据**：激活峰值随 `seq_len` 超线性增长且占比 > 60% → 证实；若激活占比 < 30% 而其它项主导 → 证伪。
- **证据强度**：4 条支持（其中 **2 条归因为推测**）／0 条反例／**4 条全部为模拟数据**（`provenance.source = "模拟"`）。
- **可迁移边界**：仅适用于「激活主导」的显存压力；对权重/优化器主导（如 R-006 的 70B）**不适用**；对短序列（`seq_len=512`，R-004 已解决）**不适用**。

### ④ 结论

**通过**。门槛达到（4 ≥ 3，由 CLI 判定，未自算），已列出 H1 及其支撑编号；同时按技能要求标注了「2/4 为推测归因」「全部为模拟数据」两项强度限制，未把 assumption 写成结论、未硬凑其他 11 个阻塞点。

---

## 3. 用例 18（闭环回归）— **通过（未写入任何文件）**

### ① 调用的命令原文

```bash
# 取下一个可用编号
... bin/rra_cli.py next-id "实现代码/data/library.seed.json"      # → R-016
... bin/rra_cli.py next-id "专家包/bin/samples/library.seed.json"  # → R-015（对照）

# 演示「新档案入库后同阻塞点会被命中」
... bin/rra_cli.py recall "实现代码/data/library.seed.json" "长序列训练显存不足"
... bin/rra_cli.py induction-candidates "实现代码/data/library.seed.json"
```

### ② 输出的关键字段

```json
next-id（工作区库）          → { "ok": true, "next_id": "R-016" }
next-id（包内样例库，对照）   → { "ok": true, "next_id": "R-015" }

recall "长序列训练显存不足"（工作区库）→ count = 5
  R-001 score 12.0  blocker 命中 4 词（权重 3.0）
  R-002 score 12.0  blocker 命中 4 词（权重 3.0）
  R-003 score 12.0  blocker 命中 4 词（权重 3.0）
  R-005 score 12.0  blocker 命中 4 词（权重 3.0）
  R-015 score  3.0  blocker 命中 1 词（权重 3.0）   ← 已入库的第 15 条

induction-candidates（工作区库）→ group_count = 1
  "长序列训练显存不足": ["R-001", "R-002", "R-003", "R-005"]
```

### ③ 编号分配与引用关系（演示，未落库）

**编号分配**：下一个可用编号由 CLI 的 `next-id` 给出，不由人手写——工作区库因已存在 R-001…R-015，故下一个是 **R-016**；包内样例库只有 14 条，故为 R-015。

**若把一条新档案（同阻塞点「长序列训练显存不足」）入库，引用关系会是**：
1. `merge-library` 将其编为 **R-016**（去重 + 重编号由 CLI 负责）；
2. 入库后 `recall "长序列训练显存不足"` 将命中 **R-016**，其 blocker 命中 4 词、得分 12.0，与 R-001/002/003/005 同档 → 条数由 5 变 6；
3. `induction-candidates` 该组由 4 条变 **5 条**，成员含 **R-016**；
4. H1 的「依据档案编号」栏相应追加为 **R-001、R-002、R-003、R-005、R-016**。

**已实测的等价证据（真实库上可观察）**：R-015 就是"已完成入库的新档案"，`recall` 已能命中它（score 3.0）——证明「新档案入库 → 同关键词召回命中」这一环在真实库上成立。但 R-015 的 blocker 字面为「量化加载后长序列激活值仍超 24G」，与组内不同，故 `induction-candidates` **未**收录它（仍为 4 条）。这恰好说明两条规则互相独立、不可混用：**recall 是词面召回（可跨 blocker 命中），induction 分组是阻塞点精确等值（不跨 blocker）**；引用一律用**档案编号**（输出即 `record_id` 列表）。

### ④ 结论

**通过**。编号由 CLI 取值、引用关系可复现；**未写入任何库文件或档案文件**（`data/library.seed.json` 与包内样例库 mtime 仍为 09-22 / 09-19，今日未变）。

---

## 4. 本轮发现的两个阻断级问题（仅报告，未修改）

### 4.1 引擎/契约漂移：专家包会判「本项目自己的库」不合规

```
validate-library 包内样例库 → { "ok": true,  "records": 14, "violations": [] }
validate-library 工作区库   → { "ok": false, "error": "整库不符合契约，已拒绝（共 14 处）" }
```

14 处违规内容为：`records[0..14].conditions` 出现「契约未声明的字段」，另有 `records[4].challenge`、`records[14].resurrection`。

**根因（已用手工 diff 取证）**：

```bash
diff "<专家包>/bin/samples/contracts/record.schema.json" "实现代码/contracts/record.schema.json"
```

diff 结果：**仓内契约多出 4 个字段声明** —— `conditions`（含九维枚举限制）、`resurrection`、`challenge`、`clarifications`；包内契约没有。

| 文件 | 最后修改 | 是否声明 `conditions` |
| --- | --- | --- |
| 专家包 `bin/samples/contracts/record.schema.json` | 2026-09-19 20:58 | **否** |
| 仓内 `contracts/record.schema.json` | 2026-09-22 23:14 | **是** |

**且仓内契约永不被读取**：`bin/rra_cli.py` 第 80–81 行

```python
SAMPLE_CONTRACTS = _first_existing(HERE / "samples" / "contracts",
                                   HERE.parent / "contracts")
```

即优先 `bin/samples/contracts`（存在），回退才是包根 `contracts/`（不存在）——仓内 `contracts/` 不在解析路径上。

**影响**：**当前安装的插件是对项目自身库「判不合规」的过期快照，交付时会被质疑。**

### 4.1b 但仓库自带的 expert 副本是好的 —— 三份库文件/两套引擎对照

进一步比对发现，仓库内其实存在**两份**专家包：一份在仓库里（`实现代码/expert/research-retro-assistant/`），一份是当前安装的插件（`~/.learnbuddy/plugins/...`）。仓库那份是新的，插件那份是旧的。

| 对象 | 位置 | 时间 | `record.schema.json` 是否声明 `conditions` | 校验工作区库结果 |
| --- | --- | --- | --- | --- |
| **仓内 expert 副本** | `实现代码/expert/research-retro-assistant/` | **2026-09-23 15:27** | **是** | **`ok: true, records: 15, violations: []`** |
| 已安装插件（本轮所用） | `~/.learnbuddy/plugins/marketplaces/my-experts/plugins/research-retro-assistant/` | 2026-09-19 19:48 | 否 | `ok: false`，14 处违规 |

三份库文件的 sha256 指纹：

| sha256(前16) | 字节 | 路径 |
| --- | --- | --- |
| `9462b67bb1ab5041` | 16676 | `实现代码/data/library.seed.json` |
| `9462b67bb1ab5041` | 16676 | `实现代码/expert/research-retro-assistant/bin/samples/library.seed.json` ← **与项目库逐字节一致** |
| `1b409fd0bc86f6a9` | 13007 | 已安装插件 `bin/samples/library.seed.json` ← 旧快照，内容不同 |

命令原文：

```bash
# 用「仓内 expert 副本」的 CLI 校验项目库
cd "实现代码/expert/research-retro-assistant" && ".../python.exe" bin/rra_cli.py validate-library "实现代码/data/library.seed.json"
# → { "ok": true, "records": 15, "violations": [] }
```

**结论（修正上面的建议方向）**：仓库侧的引擎/契约/样例库已经自洽且正确；问题**只出在「已安装到 LearnBuddy 的插件是 09-19 的旧快照」**。因此正确修法是——**用仓库里的 `实现代码/expert/research-retro-assistant/` 重新安装/刷新该专家包**（而不是去改仓库），刷新后插件才能校验通过项目自己的库。

**影响面提醒**：本轮 3 条用例的**结论不受影响**（15/21/18 在两库两引擎下判定一致），但若评审直接拿「已安装插件」跑项目库，会先撞到这 14 处校验拒绝，观感风险高，建议交付前务必刷新。

### 4.2 数据漂移：R-002 的归因类型两库不一致

| 库 | R-002 `attribution` |
| --- | --- |
| 包内样例库 | `{"text": "序列长度回到 2048 后注意力开销随长度平方增长", "type": "observed"}` |
| **工作区库** | `{"text": "怀疑序列长度回到 2048 后注意力开销随长度平方增长（未做分解实验验证）", "type": "assumption"}` |

工作区库（较新）把它从 `observed` 降级为 `assumption`。这直接影响用例 21：口径若取包内库，R-002 会被当成「日志已证机制」；取工作区库则必须写成「待验证」。**本轮采用工作区库口径**。

### 4.3 建议（本轮禁止写操作，故未执行）

1. **用仓库里的 `实现代码/expert/research-retro-assistant/` 重新安装/刷新 LearnBuddy 专家包**，让插件侧的 `bin/rra`、`bin/samples/`、`skills/*/references` 与仓库对齐（对齐后 `validate-library` 对项目库应返回 `ok: true`）。
2. 刷新后**重跑本轮 3 条用例**复核结论未漂移（预计一致）。
3. 该刷新属**对外可见的交付动作**，建议在 2026-09-26 截止前完成并留一次跑批记录作证据。

---

## 5. 汇总表

| 用例 | 结论 | 关键证据（命令输出或档案编号） |
| --- | --- | --- |
| **15** 库内无相关经验 | **通过** | `recall "光学字符识别"` → `count: 0, hits: []`；变体 `OCR`、`手写数字识别` 同为 0；阳性对照 `recall "显存不足"` → `count: 5`（R-003/R-002/R-001/R-005/R-010）。库内 15 条记录主题逐一核对，无 OCR 相关。未编造编号或原文。 |
| **21** 孵化门限 | **通过** | `induction-candidates` → `group_count: 1`，`{"长序列训练显存不足": ["R-001","R-002","R-003","R-005"]}`（4 条 ≥ 3，由 CLI 判定）。已列 H1 及支撑编号；标注 2/4 归因为 `assumption`（R-001「怀疑…」、R-002「未做分解实验验证」）、4/4 为模拟数据。其余 11 个阻塞点各 1 条，不立项。 |
| **18** 闭环回归 | **通过** | `next-id`（工作区库）→ `R-016`；`next-id`（包内样例库）→ `R-015`。`recall "长序列训练显存不足"` → 5 命中（R-001/002/003/005 各 12.0，已入库的 R-015 为 3.0），证明新档案入库后必被召回且以编号引用。未写入任何文件。 |
| **附** 引擎/契约漂移 | **需修复（阻断级）** | 已安装插件 `validate-library "项目库"` → `ok: false`，14 处违规（`conditions`/`challenge`/`resurrection` 未声明）；改用**仓内 expert 副本**同一命令 → `ok: true, records: 15, violations: []`。根因＝已安装插件是 09-19 旧快照，而仓库 `expert/` 副本（09-23 15:27）已自洽。修法：用仓内副本重装/刷新专家包。 |

## 6. 无写入证据

- 本轮执行的全部 CLI 子命令均为只读：`selftest`、`validate-library`、`contract-dims`、`next-id`、`recall`、`induction-candidates`、`blocker-digest`、`eval-cases`、`--help`；另加只读取 JSON 的核对脚本。
- `实现代码/data/library.seed.json` mtime = **2026-09-22 20:02**；已安装插件 `bin/samples/library.seed.json` mtime = **2026-09-19 20:58** —— 均未改动。
- 会话期间（21:40 之后）被写入的文件**只有 3 个**，全部在工具目录，非仓库交付内容：

```
./.learnbuddy/memory/2026-09-23.md
./.workbuddy/automations/automation-1790171460183/memory.md
./.workbuddy/automations/automation-1790171460183/真实评测首跑_用例15-21-18_报告.md
```

- 说明：`find . -newermt "2026-09-23 00:00"` 会列出 `expert/research-retro-assistant/**` 等一批文件，但其精确 mtime 为 **2026-09-23 15:27:09**（早于本会话 21:53），**不是本轮改动**，是本日早先的同步动作留下的。
- 未调用 `merge-library`、未调用 `apply-clarification`、未落库、未修改任何游戏/交付源文件。
