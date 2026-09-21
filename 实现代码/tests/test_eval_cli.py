"""评测命令行纪律（2026-09-19 外部审查 P1 的回归）。

审查原话：占位运行会写正式文件并返回成功；--blind 未冻结也退 0。
这里的每条断言都对应一个"以前会过关"的场景。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "run_eval.py"
EVAL_LOG = ROOT / "reports" / "eval-log.md"
RESULTS = ROOT / "reports" / "eval-results"


def run(*args, cwd=ROOT):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run([sys.executable, str(CLI)] + list(args), cwd=str(cwd), env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


class TestEvalCliDiscipline(unittest.TestCase):
    def setUp(self):
        self.before = EVAL_LOG.read_bytes() if EVAL_LOG.is_file() else None

    def tearDown(self):
        after = EVAL_LOG.read_bytes() if EVAL_LOG.is_file() else None
        self.assertEqual(self.before, after, "eval-log.md 被这次运行改动了")

    def test_no_executor_exits_one(self):
        r = run()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("没有真实执行器", r.stdout)

    def test_blind_without_freeze_exits_one(self):
        r = run("--blind")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("冻结", r.stdout)

    def test_placeholder_requires_flag_and_writes_local_only(self):
        r = run("--placeholder")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("占位", r.stdout)
        locals_ = sorted(RESULTS.glob("*-local.json"))
        self.assertTrue(locals_, "占位运行应写 *-local.json")
        # 本地文件里的指标必须是全失败，不能被当成成绩
        data = json.loads(locals_[-1].read_text(encoding="utf-8"))
        self.assertEqual(0.0, data["pass_rate"])
        self.assertFalse(any(x["passed"] for x in data["results"]))

    def test_create_freeze_then_blind_passes_guard(self):
        with tempfile.TemporaryDirectory() as d:
            prompt = Path(d) / "prompt.md"
            prompt.write_text("提示词初始内容", encoding="utf-8")
            freeze = Path(d) / "freeze.json"
            r1 = run("--create-freeze", str(freeze), "--prompt", str(prompt),
                     "--version", "v-test", "--by", "测试")
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            rec = json.loads(freeze.read_text(encoding="utf-8"))
            self.assertEqual(64, len(rec["prompt_hash"]))

            # 冻结后改提示词 → 守门必须拦下（退出码 1，且说明原因）
            prompt.write_text("提示词被改过了", encoding="utf-8")
            r2 = run("--blind", "--freeze", str(freeze), "--placeholder")
            self.assertEqual(r2.returncode, 1, r2.stdout + r2.stderr)
            self.assertIn("冻结后被改动", r2.stdout + r2.stderr)

            # 重新冻结 → 放行（这里仍退 1，但只是因为有占位标记：输出里必须出现守门通过）
            prompt.write_text("提示词初始内容", encoding="utf-8")
            r3 = run("--create-freeze", str(Path(d) / "f2.json"), "--prompt", str(prompt),
                     "--version", "v-test", "--by", "测试")
            self.assertEqual(r3.returncode, 0)
            r4 = run("--blind", "--freeze", str(Path(d) / "f2.json"), "--placeholder")
            self.assertIn("盲测守门通过", r4.stdout)


    def test_prompts_dir_freezes_the_whole_set(self):
        """六个技能提示词必须能一次冻结；之后改**任意一份**都要被拦下。

        这是旧实现的漏洞：`--create-freeze` 只吃一个 `--prompt`，
        冻结了 induction.md 就等于放行另外五份规则。
        """
        with tempfile.TemporaryDirectory() as d:
            prompts = Path(d) / "prompts"
            prompts.mkdir()
            (prompts / "extract.md").write_text("抽取规则 v1", encoding="utf-8")
            (prompts / "induction.md").write_text("归纳规则 v1", encoding="utf-8")
            (prompts / "notes.txt").write_text("不是提示词，不该被纳入", encoding="utf-8")
            freeze = Path(d) / "freeze.json"

            r1 = run("--create-freeze", str(freeze), "--prompts-dir", str(prompts),
                     "--version", "v1.0-frozen", "--by", "测试")
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            rec = json.loads(freeze.read_text(encoding="utf-8"))
            self.assertEqual(2, len(rec["prompt_hashes"]), "只应纳入 *.md")
            self.assertEqual("v1.0-frozen", rec["prompt_version"])
            self.assertEqual(64, len(rec["prompt_hash"]))

            # 动第二份（不是第一份）——旧的单份口径会放行
            (prompts / "induction.md").write_text("归纳规则 v2（改过了）", encoding="utf-8")
            r2 = run("--blind", "--freeze", str(freeze), "--placeholder")
            self.assertEqual(r2.returncode, 1, r2.stdout + r2.stderr)
            self.assertIn("冻结后被改动", r2.stdout + r2.stderr)
            self.assertIn("induction.md", r2.stdout + r2.stderr)

    def test_create_freeze_without_prompt_exits_one(self):
        with tempfile.TemporaryDirectory() as d:
            r = run("--create-freeze", str(Path(d) / "f.json"))
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("--prompt", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
