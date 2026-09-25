"""盲测守门必须校验「冻结粒度」（2026-09-22 后端审查 P2-8 的回归）。

现象：`--create-freeze f.json --prompt tmp_one.md --version v-partial`（只冻一份）退出 0，
随后 `--blind --freeze f.json --placeholder` 照样打印「盲测守门通过」——
守门只复核冻结记录里**出现过**的那些文件，没冻的六份规则等于放行。

要求：
- `--blind` 必须校验冻结记录覆盖提示词目录下的**全部** `*.md`，缺一份即退 1 并列出缺失文件；
  `--prompts-dir` 可显式指定基准目录；
- `--create-freeze` 只收到部分文件时给出显式警告（说清"盲测时会被拒"），但仍是警告而非拒绝。
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


def run(*args):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run([sys.executable, str(CLI)] + list(args), cwd=str(ROOT), env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


class FreezeCoverageCase(unittest.TestCase):
    def setUp(self):
        self.before = EVAL_LOG.read_bytes() if EVAL_LOG.is_file() else None

    def tearDown(self):
        after = EVAL_LOG.read_bytes() if EVAL_LOG.is_file() else None
        self.assertEqual(self.before, after, "eval-log.md 被这次运行改动了")

    def make_prompts(self, d: Path, names=("extract.md", "induction.md")) -> Path:
        prompts = Path(d) / "prompts"
        prompts.mkdir()
        for name in names:
            (prompts / name).write_text("规则 %s" % name, encoding="utf-8")
        return prompts


class TestBlindRefusesPartialFreeze(FreezeCoverageCase):
    def test_partial_freeze_is_refused_at_blind(self):
        with tempfile.TemporaryDirectory() as d:
            prompts = self.make_prompts(d)
            freeze = Path(d) / "f.json"
            r1 = run("--create-freeze", str(freeze), "--prompt", str(prompts / "extract.md"),
                     "--version", "v-partial", "--by", "测试")
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            self.assertIn("未覆盖", r1.stdout, "部分冻结必须给出显式警告：%s" % r1.stdout)

            r2 = run("--blind", "--freeze", str(freeze), "--placeholder")
            self.assertEqual(r2.returncode, 1, r2.stdout + r2.stderr)
            self.assertIn("induction.md", r2.stdout, "缺失文件必须被列出来：%s" % r2.stdout)
            self.assertNotIn("盲测守门通过", r2.stdout)

    def test_partial_freeze_is_refused_with_explicit_prompts_dir(self):
        with tempfile.TemporaryDirectory() as d:
            prompts = self.make_prompts(d)
            freeze = Path(d) / "f.json"
            run("--create-freeze", str(freeze), "--prompt", str(prompts / "extract.md"),
                "--version", "v-partial", "--by", "测试")
            r = run("--blind", "--prompts-dir", str(prompts), "--freeze", str(freeze), "--placeholder")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("induction.md", r.stdout)

    def test_full_freeze_passes_the_guard(self):
        with tempfile.TemporaryDirectory() as d:
            prompts = self.make_prompts(d)
            freeze = Path(d) / "f.json"
            r1 = run("--create-freeze", str(freeze), "--prompts-dir", str(prompts),
                     "--version", "v-full", "--by", "测试")
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            self.assertNotIn("未覆盖", r1.stdout, "整目录冻结不该报缺：%s" % r1.stdout)

            r2 = run("--blind", "--freeze", str(freeze), "--placeholder")
            self.assertIn("盲测守门通过", r2.stdout, r2.stdout + r2.stderr)
            self.assertNotIn("被守门拦下", r2.stdout)

            r3 = run("--blind", "--prompts-dir", str(prompts), "--freeze", str(freeze), "--placeholder")
            self.assertIn("盲测守门通过", r3.stdout, r3.stdout + r3.stderr)

    def test_freezing_one_of_six_repo_prompts_is_refused(self):
        """照 P2-8 的实测命令：只冻 prompts/ 里的一份，盲测必须被拒。"""
        with tempfile.TemporaryDirectory() as d:
            freeze = Path(d) / "f.json"
            r1 = run("--create-freeze", str(freeze), "--prompt", "prompts/induction.md",
                     "--version", "v-partial", "--by", "测试")
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            self.assertIn("未覆盖", r1.stdout)

            r2 = run("--blind", "--freeze", str(freeze), "--placeholder")
            self.assertEqual(r2.returncode, 1, r2.stdout + r2.stderr)
            self.assertIn("extract.md", r2.stdout)
            self.assertNotIn("盲测守门通过", r2.stdout)

    def test_freeze_record_is_still_written_on_partial(self):
        """部分冻结是"警告 + 盲测被拒"，不是"命令失败"：记录照写，便于事后复核。"""
        with tempfile.TemporaryDirectory() as d:
            prompts = self.make_prompts(d)
            freeze = Path(d) / "f.json"
            run("--create-freeze", str(freeze), "--prompt", str(prompts / "extract.md"),
                "--version", "v-partial", "--by", "测试")
            self.assertTrue(freeze.is_file())
            self.assertEqual(1, len(json.loads(freeze.read_text(encoding="utf-8"))["prompt_hashes"]))


if __name__ == "__main__":
    unittest.main()
