"""跑用例并生成记录表。

用法：
    python tools/run_eval.py                        # 无真实执行器 → 退出码 1（不再假装成功）
    python tools/run_eval.py --placeholder          # 显式占位：只写 *.local.json，退出码 1
    python tools/run_eval.py --executor mod:func     # 真实执行器（调用平台专家）
    python tools/run_eval.py --blind --freeze reports/prompt-freeze.json
    python tools/run_eval.py --create-freeze reports/prompt-freeze.json --prompt prompts/induction.md --version v1 --by 名字

三条纪律（2026-09-19 外部代码审查 P1 的修复）：
1. **没有真实执行器就退 1**，并且不写正式记录 —— 占位数据不许冒充评测结果；
2. 占位运行只写 `reports/eval-results/<日期>-<模式>.local.json`，**绝不覆盖** `reports/eval-log.md`；
3. `--blind` 必须真正经过 `BlindGuard`：未冻结、或冻结后提示词被改动 → 退出码 1。

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
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def load_library_records() -> list[dict]:
    if not LIBRARY.is_file():
        print("找不到库文件（判定引用需要它）：%s" % LIBRARY)
        sys.exit(1)
    return json.loads(LIBRARY.read_text(encoding="utf-8")).get("records", [])


def load_freeze(path: str) -> FreezeRecord:
    p = Path(path)
    if not p.is_file():
        print("盲测需要冻结记录，但文件不存在：%s\n"
              "先冻结：python tools/run_eval.py --create-freeze %s --prompt <提示词文件> "
              "--version <版本> --by <冻结人>" % (p, path))
        sys.exit(1)
    data = json.loads(p.read_text(encoding="utf-8"))
    return FreezeRecord(
        prompt_version=data.get("prompt_version", ""),
        frozen_at=data.get("frozen_at", ""),
        frozen_by=data.get("frozen_by", ""),
        prompt_hash=data.get("prompt_hash", ""),
        prompt_path=data.get("prompt_path", ""),
    )


def create_freeze(path: str) -> int:
    prompt = arg("--prompt")
    if not prompt:
        print("--create-freeze 需要 --prompt <提示词文件>")
        return 1
    guard = BlindGuard()
    try:
        record = guard.seal(arg("--version", "v1"), arg("--by", "unknown"), prompt)
    except (ValueError, RuntimeError) as e:
        print("冻结失败：%s" % e)
        return 1
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record.__dict__, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print("已冻结：%s（prompt_hash=%s…）" % (out, record.prompt_hash[:12]))
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
