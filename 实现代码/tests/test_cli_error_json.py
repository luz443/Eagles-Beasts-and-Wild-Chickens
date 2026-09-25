"""CLI 参数写错时也要说人话（2026-09-22 后端审查 P2-9 的回归）。

两处：
1. `tools/rra_cli.py`（无子命令）→ 退出 2、用法只打到 stderr、stdout 一个字节都没有，
   违反它自己文档里的承诺「输出一律 JSON（stdout），错误也走 JSON，退出码非 0」——
   专家侧按 JSON 解析 stdout 时会直接炸，而不是拿到一条可读的失败。
2. `tools/run_eval.py --blind --freeze`（旗标在末尾、缺值）→ IndexError 堆栈，
   人看到的是栈而不是"你少写了一个值"。
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RRA_CLI = ROOT / "tools" / "rra_cli.py"
RUN_EVAL = ROOT / "tools" / "run_eval.py"


def _env():
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)          # rra_cli 必须自己找到引擎
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def run_cli(*args):
    return subprocess.run([sys.executable, str(RRA_CLI)] + list(args), cwd=str(ROOT),
                          env=_env(), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def run_eval(*args):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run([sys.executable, str(RUN_EVAL)] + list(args), cwd=str(ROOT), env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


class TestRraCliErrorsAreJson(unittest.TestCase):
    def assert_json_failure(self, r, needle=""):
        self.assertNotEqual(0, r.returncode, "参数错误必须是非 0 退出码")
        self.assertTrue(r.stdout.strip(), "stdout 必须是 JSON，而不是空的：stderr=%s" % r.stderr)
        data = json.loads(r.stdout)          # 解析失败即测试失败
        self.assertFalse(data["ok"])
        self.assertTrue(str(data.get("error", "")).strip(), "错误必须说明原因：%s" % data)
        if needle:
            self.assertIn(needle, json.dumps(data, ensure_ascii=False))

    def test_no_subcommand(self):
        self.assert_json_failure(run_cli())

    def test_unknown_subcommand(self):
        self.assert_json_failure(run_cli("不存在的命令"))

    def test_unknown_option(self):
        self.assert_json_failure(run_cli("selftest", "--没有这个参数"))

    def test_valid_command_still_json(self):
        r = run_cli("contract-dims")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertTrue(json.loads(r.stdout)["ok"])


class TestRunEvalArgBoundary(unittest.TestCase):
    def test_missing_value_for_freeze_is_not_a_traceback(self):
        r = run_eval("--blind", "--freeze")
        both = (r.stdout or "") + (r.stderr or "")
        self.assertNotIn("IndexError", both, both)
        self.assertNotIn("Traceback", both, both)
        self.assertNotEqual(0, r.returncode)
        self.assertIn("--freeze", both, "错误信息要指出是哪个旗标缺值：%s" % both)

    def test_missing_value_for_create_freeze_is_not_a_traceback(self):
        r = run_eval("--create-freeze")
        both = (r.stdout or "") + (r.stderr or "")
        self.assertNotIn("IndexError", both, both)
        self.assertNotIn("Traceback", both, both)
        self.assertNotEqual(0, r.returncode)


if __name__ == "__main__":
    unittest.main()
