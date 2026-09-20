# 后端审查处置报告（2026-09-19）

> 对应审查作业书：`docs/review-prompt-backend.md`；本文逐条回应审查结果：**核实结论 → 处置 → 证据**。
> 验证状态：`python run_tests.py` **116 条全绿**（原 98 条 + 新增 18 条护栏）；`sync_expert.py --check`（仓库镜像）
> 与 `--check --platform`（本机已装包）均摘要一致。所有改动集中在后端与两端边界，网页视觉未动。

## 一、P0（2 条，全部确认成立并已修复）

### P0-1 CLI 与专家包无法按文档命令运行 → **确认，已修**

- **核实**：属实，且是我的缺陷——我把包内 `bin/rra_cli.py` 直接复制成了仓库 `tools/rra_cli.py`，
  而它内部的引擎定位写死为"与 CLI 同目录"。两条复现（`ModuleNotFoundError`、设了 `PYTHONPATH`
  又撞样例路径）都对。
- **处置**：
  1. `tools/rra_cli.py` 增 `_bootstrap_engine()`：按「包内 `bin/rra/`」→「仓库 `src/rra/`」两个位置自举，
     **不再要求任何外部 `PYTHONPATH`**；
  2. 样例与契约路径改为双候选（包内 `bin/samples/` → 仓库 `data/` + `contracts/`）；
  3. 找不到引擎时输出可读错误并 exit 1，不再抛 `ModuleNotFoundError`；
  4. **专家包镜像改为整份复制**（含 `bin/rra`、`bin/samples` 等生成物）——克隆仓库即可安装，
     一致性由 `--check` 摘要守着。
- **证据**：`tests/test_cli_bootstrap.py`（3 条：无 PYTHONPATH / 无关 cwd / 孤立目录给可读错误）；
  实测在 `C:\Users\Lenovo` 下 `python tools/rra_cli.py selftest` → **exit 0**；
  `sync_expert.py` 同步后镜像 66 个文件、引擎摘要 `True`。

### P0-2 证据引用只查编号与长度 → **确认，已修**

- **核实**：属实。原校验链只有：编号格式 → 库内是否存在 → quote 长度 ≥4，
  **没有任何一处比对引文内容**，编造 4 个字即可通过。
- **处置**：
  1. `validate_library` 新增跨档案检查「引文可复核」：引文必须真的出现在被引用档案的
     `attribution.text / observation / blocker`（字段集与网页端 `refute.js` 取引文的位置一致，
     避免制造新的跨端分叉）；
  2. 规范化复用去重指纹那一套（NFKC + 去标点 + 去空白 + 小写），空白与全半角差异不误报；
  3. 空引文一律判不匹配（否则 `"" in 任何字符串` 恒真，等于把检查关掉）；
  4. **两端同步实现**：`web/js/contracts.js` 加同一条规则。
- **证据**：`tests/test_evidence_quote.py`（7 条，含"虚构引文必须被拒""三字段各自可过""空白容错"）；
  两端一致性测试 5 个夹具结论逐条相等。
  **重要副产品**：现有 14 条种子数据的引用**全部可核验**，无需迁移数据。

## 二、P1（6 条，全部确认成立并已修复）

### P1-1 畸形嵌套 JSON 抛异常 → **确认，已修（范围比报告更大）**

- **核实**：属实；**并且 `validate_library` 里也有同一段逻辑**（报告只点了 archive 层），
  所以 `links: [null]` 在整库校验时同样会崩。
- **处置**：Python 侧加列表型字段的容器类型检查（`links / evidence_refs / artifacts / missing_info`）
  与元素类型检查（`links[i]`、`same/diff[i]`、`evidence_refs[i]`）；JS 侧同步（`asList` / `isPlainObject`）。
- **证据**：`tests/test_validator_hardening.py`（4 条，含报告给的最小输入 `{"id":"R-001","links":[null]}`）；
  新增夹具 `contracts/fixtures/invalid_nested_null.json` 已进入两端一致性测试 ——
  护栏先红（JS 在 `contracts.js:91` 抛 `TypeError`）后绿。

### P1-2 网页导入写入失败后内存仍被污染 → **确认，已修**

- **核实**：属实，`store.js` 是 `this.library = next; this.save();`；`refute.js` 同款写法。
- **处置**：`LibraryStore.commit(next)` —— **先落盘成功、才替换内存**；`importLibrary` 与
  `RefutationController.submit` 一律改走 `commit()`。
- **证据**：`web/tests/store-commit-safety.mjs`（10 项：正常路径 / 写失败后内存未污染 / 存储仍是旧库 /
  契约不合规时不碰存储 / 反驳路径同样原子）。

### P1-3 盲测冻结可绕过 → **确认，已修（三条都改了）**

- **处置**：
  1. `seal()` 必须给提示词路径且文件存在，哈希必须是 64 位 sha256；否则 `ValueError`；
  2. `FreezeRecord` 增记 `prompt_path`；**读取盲测用例前重新计算当前哈希并比对**，不一致即 `PermissionError`；
  3. `run_eval.py --blind` 真正走 `BlindGuard`：未冻结 / 哈希不符 → **退出码 1**；
     另加 `--create-freeze`，否则守门不可用（冻结这一步此前根本没有入口）。
- **证据**：`tests/test_blind.py`（9 条，含"冻结后改提示词 → 读用例被拦"）+ `tests/test_eval_cli.py`（4 条端到端）。

### P1-4 评测结果可以"自我满足" → **确认，已修（改了接口）**

- **处置**：`EvalRunner` 不再接受执行器返回的判据。执行器只能交回 `CaseOutput(raw, claimed_hits)`，
  四个判据全部由 `Judge` 从**原始输出 + 库**算：
  - `contract_ok`：输出过档案契约校验；
  - `citation_ok`：必须有引用，且每条引文的编号与原文都能在库里对上；
  - `fabricated_attribution`：引用对不上，或把归因写成 `observed` 却拿不出可核验引用；
  - `hit`：按**显式规则表** `HIT_EXPECTATION[CaseKind]` 决定（True 应命中 / False 不应命中 / None 语义性）。
- **必须如实说明的一点**：27 条用例目前**没有机器可判的期望**（`Case` 只有 `summary / expectation` 文字描述）。
  因此 5 类用例（证据不足、孵化、契约一致性、死实验复活、审稿人质询）的命中判据是语义性的，
  我把它们标为 **`None` = 当前不计通过**并在备注里写明"待人工/语义判定"。
  这不是掩盖，而是把它暴露出来——在此之前，这些用例的"通过"完全靠执行器自报。
  要让它们可判，需要给用例补机器可读的场景（输入 + 期望），这是评测设计的下一步。
- **证据**：`tests/test_runner.py`（12 条，含"执行器交回全 True 的结果对象一律判失败"、
  "占位执行器通过率必须为 0"、"声称命中的编号必须真实存在"）。

### P1-5 占位评测会写正式文件并返回成功 → **确认，已修**

- **处置**：无执行器 → 打印原因并 **exit 1**；`--placeholder` 必须显式声明，只写
  `reports/eval-results/<日期>-local.json`，**不写** `reports/eval-log.md`，且 exit 1 并提示指标无意义；
  此前由占位执行器生成的 `reports/eval-log.md` 已移至 `reports/eval-log.local.md`，
  正式文件重写为"尚未跑真实评测"的空档说明。
- **证据**：`tests/test_eval_cli.py`（断言 `eval-log.md` 字节不变；`*-local.json` 的 `pass_rate` 必须为 0）。

### P1-6 sync --check 依赖外部机器状态 → **确认，已修**

- **处置**：`--check` 默认比对**仓库镜像** `expert/research-retro-assistant/`（与机器无关，任何机器都能跑）；
  新增 `--platform` 才比对本机已安装的平台包；两种情况分别给出可读说明
  （"仓库镜像不一致" vs "本机未安装，不影响仓库交付"）。
- **证据**：`--check` → exit 0（镜像 = 源码）；`--check --platform` → exit 0（本机已装包 = 源码）。

## 三、报告未点到、我顺手发现的同类问题（3 处）

1. **`reports/contract-parity.json` 在仓库里没有任何生成器** —— 它是 JS 侧比对的基准，一旦过期，
   两端测试就会拿旧基准"静默通过"。已加 `tools/make_contract_parity.py`，
   并让 `run_tests.py` **每次跑之前重建**它。
2. `validate_library` 里同样存在 `links: [null]` 崩溃路径（报告只点了 archive 层）。
3. 仓库镜像缺生成物导致"克隆后不可安装"（报告点到了，我把它连同方案一起改了）。

## 四、无法本地验证的部分（与报告的判断一致）

- 平台真实调用成本、专家实际运行效果、平台插件注册状态：报告说无法验证，我这边**补了一条实测**——
  平台内一次性任务跑通"专家执行包内脚本"（回执 `_build/smoke-platform-run-2026-09-19.txt`，
  `ls` 与 `selftest` 退出码均 0，`result_success=1`），该会话计 **0.92 Credits**
  （`session_usage.credit_json`）。评测跑批的成本仍需按同类任务再测一次。

## 五、报告建议的"最该先修的三件"（已全部完成）

| 优先 | 事项 | 状态 |
| --- | --- | --- |
| 1 | 修复 CLI 与专家包自检路径 | ✅ `test_cli_bootstrap.py` 3 条 + 无关 cwd 实测 exit 0 |
| 2 | 修复证据引用的真实匹配校验 | ✅ 两端各实现 + `test_evidence_quote.py` 7 条 |
| 3 | 修复盲测与评测执行器 | ✅ `test_blind.py` 9 条 + `test_runner.py` 12 条 + `test_eval_cli.py` 4 条 |

## 六、本轮新增/修改的文件

| 类型 | 文件 |
| --- | --- |
| 新增测试 | `tests/test_cli_bootstrap.py`、`tests/test_evidence_quote.py`、`tests/test_validator_hardening.py`、`tests/test_eval_cli.py`、`web/tests/store-commit-safety.mjs` |
| 改写测试 | `tests/test_blind.py`、`tests/test_runner.py`（改为锁住新契约） |
| 新增工具 | `tools/make_contract_parity.py` |
| 新增夹具 | `contracts/fixtures/invalid_nested_null.json` |
| 修改实现 | `tools/rra_cli.py`、`tools/run_eval.py`、`tools/sync_expert.py`、`src/rra/contracts/validator.py`、`src/rra/eval/blind.py`、`src/rra/eval/runner.py`、`web/js/contracts.js`、`web/js/store.js`、`web/js/refute.js`、`run_tests.py` |

## 七、复现验证（三条命令）

```bash
# 1) 全套测试（含两端一致性、写失败原子性、评测纪律）
python run_tests.py                       # → 116 条全绿，exit 0

# 2) 专家包与仓库是否一致（默认查仓库镜像；--platform 查本机已装包）
python tools/sync_expert.py --check
python tools/sync_expert.py --check --platform

# 3) CLI 在任何目录、不设 PYTHONPATH 都能跑
cd C:\ && python <repo>\tools\rra_cli.py selftest    # → exit 0
```
