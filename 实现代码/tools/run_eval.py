"""跑用例并生成记录表。

用法：
    python tools/run_eval.py                        # 无真实执行器 → 退出码 1（不再假装成功）
    python tools/run_eval.py --placeholder          # 显式占位：只写 *.local.json，退出码 1
    python tools/run_eval.py --executor mod:func     # 真实执行器（调用平台专家）
    python tools/run_eval.py --blind --freeze reports/prompt-freeze.json
    python tools/run_eval.py --blind --freeze f.json --prompts-dir <提示词目录>   # 显式钉住"必须覆盖哪个目录"
    python tools/run_eval.py --create-freeze reports/prompt-freeze.json --prompts-dir prompts --version v1.0-frozen --by 名字
    python tools/run_eval.py --create-freeze f.json --prompt prompts/extract.md --prompt prompts/induction.md --version v1 --by 名字

三条纪律（2026-09-19 外部代码审查 P1 的修复）：
1. **没有真实执行器就退 1**，并且不写正式记录 —— 占位数据不许冒充评测结果；
2. 占位运行只写 `reports/eval-results/<日期>-<模式>.local.json`，**绝不覆盖** `reports/eval-log.md`；
3. `--blind` 必须真正经过 `BlindGuard`：未冻结、或冻结后提示词被改动 → 退出码 1。

2026-09-22 后端审查 P2-8 补上第 4 条：
4. `--blind` 还要校验**冻结粒度**——冻结必须覆盖它涉及的提示词目录下的全部 `*.md`，
   缺一份即退 1 并列出缺失文件（只冻一份 = 放行其余规则）；
   `--create-freeze` 只收到部分文件时给出显式警告，并提示"盲测时会被拒"。

冻结为什么是「一组」而不是「一份」：本作品的判断规则分散在六个技能提示词里，
只冻结其中一份等于放行另外五份。`--prompts-dir` 会把该目录下的 `*.md` 全部纳入冻结。

判据由 `rra.eval.runner.Judge` 从原始输出与库算出，执行器只能交回 `CaseOutput`
（原始输出 + 声称命中的编号），**无法自报成绩**。
"""

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rra.eval.blind import BlindGuard, FreezeRecord        # noqa: E402
from rra.eval.cases import CaseRegistry                    # noqa: E402
from rra.eval.runner import CaseOutput, EvalRunner, Judge  # noqa: E402

REPORTS = ROOT / "reports"
LIBRARY = ROOT / "data" / "library.seed.json"


def arg(flag: str, default: str = "") -> str:
    """取旗标的值。

    2026-09-22 后端审查 P2-9：旗标写在末尾（例如 `--blind --freeze`）时，
    原实现直接 `sys.argv[i + 1]` → IndexError 堆栈。这里补边界检查：
    缺值就说明白是哪个旗标缺值，而不是把人扔进栈里。
    """
    if flag not in sys.argv:
        return default
    i = sys.argv.index(flag) + 1
    if i >= len(sys.argv):
        print("参数 %s 缺少取值：请写成 `%s <值>`" % (flag, flag))
        raise SystemExit(2)
    return sys.argv[i]


def args_all(flag: str) -> list[str]:
    """取重复出现的旗标（例如 `--prompt a --prompt b`）。arg() 只返回第一个。"""
    return [sys.argv[i + 1] for i, token in enumerate(sys.argv[:-1]) if token == flag]


def load_library_records() -> list[dict]:
    if not LIBRARY.is_file():
        print("找不到库文件（判定引用需要它）：%s" % LIBRARY)
        sys.exit(1)
    return json.loads(LIBRARY.read_text(encoding="utf-8")).get("records", [])


def load_freeze(path: str) -> FreezeRecord:
    p = Path(path)
    if not p.is_file():
        print("盲测需要冻结记录，但文件不存在：%s\n"
              "先冻结：python tools/run_eval.py --create-freeze %s --prompts-dir prompts "
              "--version <版本> --by <冻结人>" % (p, path))
        sys.exit(1)
    data = json.loads(p.read_text(encoding="utf-8"))
    hashes = data.get("prompt_hashes") or {}
    if not isinstance(hashes, dict):
        hashes = {}
    return FreezeRecord(
        prompt_version=data.get("prompt_version", ""),
        frozen_at=data.get("frozen_at", ""),
        frozen_by=data.get("frozen_by", ""),
        prompt_hash=data.get("prompt_hash", ""),
        prompt_path=data.get("prompt_path", ""),
        prompt_hashes={str(k): str(v) for k, v in hashes.items()},
    )


def collect_prompts() -> list[str]:
    """要冻结的提示词：`--prompt` 可重复，`--prompts-dir` 一次纳入整个目录的 *.md。

    路径统一写成正斜杠：冻结记录会进仓库、被别的机器复核，
    Windows 的反斜杠会让队友在 macOS / Linux 上一律「文件不存在」。
    """
    paths = [p.replace("\\", "/") for p in args_all("--prompt")]
    prompts_dir = arg("--prompts-dir")
    if prompts_dir:
        d = Path(prompts_dir)
        if not d.is_dir():
            print("--prompts-dir 不是目录：%s" % d)
            return []
        paths.extend(str(p).replace("\\", "/") for p in sorted(d.glob("*.md")))
    # 去重但保序：同一份文件被两种方式各点一次时不要算两份
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _display(path: Path) -> str:
    """给人看的路径：能相对仓库根就用相对路径，否则用绝对路径（统一正斜杠）。"""
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def coverage_gaps(freeze: FreezeRecord, prompts_dir: str = "") -> list[str]:
    """冻结**没覆盖到**的提示词文件；空列表表示覆盖完整。

    2026-09-22 后端审查 P2-8：原守门只复核「冻结记录里出现过」的那些文件，
    于是只冻一份（甚至一份无关文件）也照样打印「盲测守门通过」——没冻的规则等于放行。
    这里改成**目录级**口径：冻结必须覆盖它涉及的每个提示词目录下的全部 `*.md`。
    `--prompts-dir` 可显式指定基准目录（例如仓库的 prompts/），用于把口径钉在"要冻哪一组"上。

    为什么是"目录级"而不是"永远盯死 prompts/"：冻结单份自定义提示词（例如别人用临时目录
    做的一次性实验）时，只要那个目录里的 `*.md` 都冻住了就没有放行任何东西；
    反过来，`prompts/` 里只冻六份中的一份，就会被这里列出来并拦住。
    """
    frozen = {str(Path(p).resolve()) for p in freeze.prompt_hashes}
    if prompts_dir:
        dirs = [Path(prompts_dir)]
    else:
        dirs = sorted({Path(p).parent for p in freeze.prompt_hashes}, key=str)
    missing: list[str] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            if str(f.resolve()) not in frozen:
                missing.append(_display(f))
    return missing


def create_freeze(path: str) -> int:
    prompts = collect_prompts()
    if not prompts:
        print("--create-freeze 需要 --prompt <提示词文件>（可重复）或 --prompts-dir <目录>")
        return 1
    guard = BlindGuard()
    try:
        record = guard.seal_many(arg("--version", "v1"), arg("--by", "unknown"), prompts)
    except (ValueError, RuntimeError) as e:
        print("冻结失败：%s" % e)
        return 1
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record.__dict__, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print("已冻结 %d 份提示词：%s（合并哈希 %s…）"
          % (len(record.prompt_hashes), out, record.prompt_hash[:12]))
    for one in sorted(record.prompt_hashes):
        print("  %-28s %s…" % (one, record.prompt_hashes[one][:12]))
    # P2-8：只冻结一部分就明确警告 —— 否则"冻了一份"看起来和"冻住了"一模一样，
    # 等到盲测时才发现被拒（或者更糟：以前根本不会拒）。
    gaps = coverage_gaps(record, arg("--prompts-dir"))
    if gaps:
        print("⚠️ 警告：本次冻结未覆盖 %d 份提示词，盲测时会被拒：%s\n"
              "   要冻住整个目录，请用 --prompts-dir <目录>（例如 --prompts-dir prompts）。"
              % (len(gaps), "、".join(gaps)))
    return 0


def bind_executor():
    """真实执行器：--executor <module:function>，函数签名 (Case) -> CaseOutput。"""
    spec = arg("--executor")
    if not spec or ":" not in spec:
        return None
    mod_name, func_name = spec.split(":", 1)
    sys.path.insert(0, str(ROOT))
    import importlib
    try:
        mod = importlib.import_module(mod_name)
        return getattr(mod, func_name)
    except (ImportError, AttributeError) as e:
        print("无法加载执行器 %s：%s" % (spec, e))
        sys.exit(1)


def placeholder_executor(_case):
    """占位执行器：明确交回"没有输出"，判分器据此判失败——不会产出好看的数字。"""
    return CaseOutput(raw=None, note="占位：未接平台专家")


def main() -> int:
    mode = "blind" if "--blind" in sys.argv else "open"

    if "--create-freeze" in sys.argv:
        return create_freeze(arg("--create-freeze"))

    registry = CaseRegistry.default()
    selected = registry.blind_cases() if mode == "blind" else registry.open_cases()

    freeze = None
    if mode == "blind":
        freeze_path = arg("--freeze", "reports/prompt-freeze.json")
        freeze = load_freeze(freeze_path)
        # P2-8：先查粒度，再查哈希。只冻了一份（或一份无关文件）时，
        # 逐份哈希复核照样全过 —— 那正是漏洞：没冻的规则等于放行。
        gaps = coverage_gaps(freeze, arg("--prompts-dir"))
        if gaps:
            print("盲测被守门拦下（退出码 1）：冻结记录未覆盖 %d 份提示词，缺：%s\n"
                  "冻结必须覆盖提示词目录下的全部 *.md（只冻一份 = 放行其余规则）。\n"
                  "重新冻结：python tools/run_eval.py --create-freeze %s "
                  "--prompts-dir <提示词目录> --version <版本> --by <冻结人>"
                  % (len(gaps), "、".join(gaps), freeze_path))
            return 1
        guard = BlindGuard(freeze)
        for case in selected:
            try:
                guard.assert_can_read(case)      # 未冻结 / 提示词被改动 → 这里拦住
            except PermissionError as e:
                print("盲测被守门拦下（退出码 1）：%s" % e)
                return 1
        print("盲测守门通过：提示词哈希与冻结记录一致（%s…）" % freeze.prompt_hash[:12])

    executor = bind_executor()
    is_placeholder = False
    if executor is None:
        if "--placeholder" not in sys.argv:
            print("没有真实执行器：请用 --executor <module:function> 接平台专家；\n"
                  "若只是验证管线连通，显式加 --placeholder（结果只写 *.local.json，且退出码 1）。")
            return 1
        executor = placeholder_executor
        is_placeholder = True

    records = load_library_records()
    report = EvalRunner(registry, executor, Judge()).run(selected, records)
    report.prompt_version = freeze.prompt_version if freeze else "unfrozen"

    out_dir = REPORTS / "eval-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "local" if is_placeholder else mode
    out_json = out_dir / ("%s-%s.json" % (date.today().isoformat(), suffix))
    report.save(out_json)
    print("结果已写入：%s" % out_json.relative_to(ROOT))

    if is_placeholder:
        print("⚠️ 这是占位运行：没有调用任何专家，指标无意义。\n"
              "   为避免被当成真实评测结果，本次**不写** reports/eval-log.md，且退出码为 1。")
        return 1

    (REPORTS / "eval-log.md").write_text(report.to_markdown_table(), encoding="utf-8")
    print("已写入正式记录表：reports/eval-log.md")
    print("引用正确率 %.1f%%，通过率 %.1f%%"
          % (report.citation_accuracy() * 100, report.pass_rate() * 100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
