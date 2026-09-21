"""一键跑全部测试：python run_tests.py

存在的理由：`python -m unittest` 需要外部设置 PYTHONPATH 才能 import rra，
不同人不同机器上容易忘记，导致"测试跑不起来"被误判成"测试都过了"。
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    print("== Python 测试 ==")
    r1 = subprocess.run([sys.executable, "-m", "unittest", "discover",
                         "-s", "tests", "-t", "tests", "-v"],
                        cwd=ROOT, env=env)
    if r1.returncode != 0:
        return r1.returncode

    print("== 重新生成契约快照（Python 口径，避免两端测试拿过期基准静默通过）==")
    r0 = subprocess.run([sys.executable, str(ROOT / "tools" / "make_contract_parity.py")],
                        cwd=ROOT, env=env)
    if r0.returncode != 0:
        return r0.returncode

    print("== 前端测试（契约 / 路由 / 排序 / 纠错规则 / 复活规则 / 写失败原子性）==")
    node = os.environ.get("RRA_NODE", "node")
    for name in ("contract-parity.mjs", "route-roundtrip.mjs", "sort-order.mjs",
                 "refutation-rule-parity.mjs", "resurrection-rule-parity.mjs",
                 "store-commit-safety.mjs", "workbench.mjs"):
        r = subprocess.run([node, str(ROOT / "web" / "tests" / name)],
                           cwd=ROOT, env=env)
        if r.returncode != 0:
            return r.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
