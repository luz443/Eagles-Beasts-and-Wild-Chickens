"""生成两端契约一致性的期望快照：reports/contract-parity.json

为什么要生成、而不是手写：
    这份文件是 JS 侧校验器比对的**基准**。若它不随 Python 校验器一起更新，
    两边就会拿一份过期的基准去比 —— 测试照过，而两端其实已经分叉。
    2026-09-19 外部代码审查把这类问题归为「测试可以自我满足」，本脚本就是修它：
    `run_tests.py` 每次跑之前都会重新生成这里的 dims 与 fixtures。

保留策略：
    `dedup_samples`（去重指纹样本）是从旧文件里**原样继承**的，只增不改——
    它们是对着两个实现写死的历史样本，重建会丢掉覆盖面。

用法：python tools/make_contract_parity.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "contract-parity.json"
FIXTURES = ROOT / "contracts" / "fixtures"

sys.path.insert(0, str(ROOT / "src"))

from rra.contracts.dims import Dim                      # noqa: E402
from rra.contracts.validator import Validator            # noqa: E402


def build_snapshot() -> dict:
    validator = Validator()
    fixtures = {}
    for path in sorted(FIXTURES.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        # 快照只记路径：原因与期望属于人看的细节，两端比的是「哪些字段违规」这一结论
        fixtures[path.name] = [v.path for v in validator.validate_archive(raw)]

    old = {}
    if REPORT.exists():
        try:
            old = json.loads(REPORT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            old = {}

    return {
        "_note": "由 tools/make_contract_parity.py 从 Python 校验器生成；run_tests.py 会自动重建。",
        "_generated_at": datetime.now().isoformat(timespec="seconds"),
        "dims": [d.value for d in Dim],
        "fixtures": fixtures,
        "dedup_samples": old.get("dedup_samples", []),
    }


def main() -> int:
    snapshot = build_snapshot()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("已生成 %s：dims %d 个，fixtures %d 个，dedup_samples %d 个"
          % (REPORT.relative_to(ROOT), len(snapshot["dims"]),
             len(snapshot["fixtures"]), len(snapshot["dedup_samples"])))
    for name, paths in snapshot["fixtures"].items():
        print("  %-32s %s" % (name, paths or "（无违规）"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
