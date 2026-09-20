"""CLI 自举回归：两种位置都能直接跑，不依赖外部 PYTHONPATH（2026-09-19 外部审查 P0）。

原缺陷：仓库里的 `tools/rra_cli.py` 把引擎路径写死为"与 CLI 同目录"，导致
`python tools/rra_cli.py selftest` 直接 ModuleNotFoundError；即使手工设 PYTHONPATH=src，
样例路径又写死成 `HERE/samples/...` 而失败。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "rra_cli.py"


def _clean_env():
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)          # 关键：不允许靠外部 PYTHONPATH 兜底
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


class TestCliBootstrap(unittest.TestCase):
    def test_runs_from_repo_root_without_pythonpath(self):
        r = subprocess.run([sys.executable, str(CLI), "selftest"], cwd=str(ROOT),
                           env=_clean_env(), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(json.loads(r.stdout)["ok"])

    def test_runs_from_unrelated_cwd(self):
        """在无关目录里跑（模拟"装好后随手调用"）也要通，并能自己找到样例与契约。"""
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, str(CLI), "selftest"], cwd=tmp,
                               env=_clean_env(), capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            data = json.loads(r.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue(Path(data["sample_library"]).is_file(),
                            "样例库路径应指向仓库 data/ 或包内 samples/：%s" % data.get("sample_library"))

    def test_missing_engine_reports_clearly(self):
        """把 CLI 单独复制到孤立目录：必须给出可读错误，而不是 ModuleNotFoundError。"""
        with tempfile.TemporaryDirectory() as tmp:
            lonely = Path(tmp) / "rra_cli.py"
            lonely.write_text(CLI.read_text(encoding="utf-8"), encoding="utf-8")
            r = subprocess.run([sys.executable, str(lonely), "contract-dims"], cwd=tmp,
                               env=_clean_env(), capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            both = (r.stdout or "") + (r.stderr or "")
            self.assertEqual(r.returncode, 1, both)
            self.assertIn("找不到 rra 引擎", both)
            self.assertNotIn("ModuleNotFoundError", both)


if __name__ == "__main__":
    unittest.main()
