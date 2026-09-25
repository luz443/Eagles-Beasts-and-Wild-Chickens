"""生成两端契约一致性的期望快照：reports/contract-parity.json

为什么要生成、而不是手写：
    这份文件是 JS 侧校验器比对的**基准**。若它不随 Python 校验器一起更新，
    两边就会拿一份过期的基准去比 —— 测试照过，而两端其实已经分叉。
    2026-09-19 外部代码审查把这类问题归为「测试可以自我满足」，本脚本就是修它：
    `run_tests.py` 每次跑之前都会重新生成这里的 dims 与 fixtures。

保留策略：
    `dedup_samples`（去重指纹样本）里**人工维护**的纠错样本随本脚本一起生成（幂等、可重复跑），
    历史样本从旧文件里原样继承、只增不改——它们是对着两个实现写死的历史样本，重建会丢掉覆盖面。

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
from rra.contracts.models import Archive                 # noqa: E402
from rra.contracts.validator import Validator            # noqa: E402
from rra.library.dedup import Deduplicator               # noqa: E402

# 纠错记录引用的目标档案。quote 必须取自它可核验的字段（否则整库校验不过）。
_REF_TARGET_BLOCKER = "长序列下单卡显存不足"


def _refutation(rid, reason, *, target="R-001", links=None, attempt=None, observation=None):
    """网页端「反驳」按钮写出的完整合法记录（形状见 web/js/refute.js）。

    `observation` 缺省用 `reason` 填充；显式传空串可造出「observation 为空、
    理由只落在 attribution.text」的记录——用来覆盖 `Deduplicator._refutation_key`
    里 `observation or attribution.text` 那条**理由回退分支**（`dedup.py:64`）。
    """
    return {
        "id": rid,
        "attempt": attempt if attempt is not None else ("对 %s 的人工纠错" % target),
        "expectation": "修正 %s 的判断" % target,
        "observation": reason if observation is None else observation,
        "blocker": _REF_TARGET_BLOCKER,
        "attribution": {"text": "人工纠错：" + reason, "type": "observed"},
        "boundary": "仅针对 %s 的判断，不改变其原始记录" % target,
        "confidence": "medium",
        "status": "进行中",
        "missing_info": [],
        "artifacts": [],
        "links": links if links is not None else [
            {"target": target, "relation": "冲突", "same": [], "diff": [], "transferable": ""}],
        "evidence_refs": [{"record": target, "quote": _REF_TARGET_BLOCKER}],
        "version": 1,
        "provenance": {"author": "人工纠错", "date": "2026-09-23", "source": "真实"},
    }


def build_refutation_dedup_samples() -> list:
    """纠错记录（方案 C）的去重指纹样本：键由 Python 侧算出，JS 侧必须逐条相等。

    覆盖四条路径：冲突链接取目标；同目标不同理由（两者的键必须不同）；
    无冲突链接时从 attempt 正则抓编号；**observation 为空时退回 attribution.text 取理由**。
    """
    dedup = Deduplicator()
    raws = [
        _refutation("R-101", "显存不足其实是因为 batch 开太大，先降 batch"),
        _refutation("R-102", "这次 OOM 是数据加载瓶颈，与注意力开销无关"),
        _refutation("R-103", "对 R-007 的判断有异议", target="R-007",
                   links=[{"target": "R-007", "relation": "相似", "same": [], "diff": [],
                           "transferable": ""}],
                   attempt="人工纠错：对 R-007 的判断有异议"),
        # observation 为空串，理由只写在 attribution.text：逼两端都走
        # `reason = observation or attribution.text` 的回退分支并给出同一个键。
        _refutation("R-104", "理由只落在 attribution.text 的回退分支", observation=""),
    ]
    return [{"input": raw, "key": dedup.key_of(Archive.from_dict(raw))} for raw in raws]


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

    # 纠错样本由本脚本管理：先按 input.id 摘掉旧的同类样本，再追加新算的，保证重复跑幂等。
    managed = build_refutation_dedup_samples()
    managed_ids = {s["input"]["id"] for s in managed}
    inherited = [s for s in old.get("dedup_samples", [])
                 if s.get("input", {}).get("id") not in managed_ids]

    return {
        "_note": "由 tools/make_contract_parity.py 从 Python 校验器生成；run_tests.py 会自动重建。",
        "_generated_at": datetime.now().isoformat(timespec="seconds"),
        "dims": [d.value for d in Dim],
        "fixtures": fixtures,
        "dedup_samples": inherited + managed,
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
