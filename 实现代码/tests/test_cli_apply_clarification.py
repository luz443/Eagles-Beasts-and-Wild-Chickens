"""CLI 澄清留痕（P2-10 的 CLI 侧缺口）。

技能层早已支持把答复原文写进 `clarifications`，但 CLI 的 `apply-clarification`
没把答复透传进去——专家走 CLI 澄清时答复只进 warnings、档案里查不到，日后无从复核。
这里用 subprocess 调**真实 CLI**，覆盖两条路径：带 `--answer` 留痕 / 不带时显式 warning。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RRA_CLI = ROOT / "tools" / "rra_cli.py"
KEY = "micro-batch 实际生效值"
ANSWER = "micro-batch 实际生效值是 2"


def _env():
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)          # rra_cli 必须自己找到引擎（与 test_cli_error_json 同口径）
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def run_cli(*args):
    return subprocess.run([sys.executable, str(RRA_CLI)] + list(args), cwd=str(ROOT),
                          env=_env(), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def _record():
    """一条含可澄清 missing_info 的档案（不追求过契约，本用例只关心留痕）。"""
    return {
        "id": "R-013",
        "attempt": "把 micro-batch 降到 2 跑长序列",
        "expectation": "在 24G 显存上完成 seq_len=2048 训练",
        "observation": "显存仍不足，200 step 内 OOM 两次",
        "blocker": "长序列训练显存不足",
        "attribution": {"text": "怀疑是注意力矩阵开销随序列长度平方增长", "type": "assumption"},
        "missing_info": [KEY],
        "boundary": "单卡 24G、未开 flash-attention 时成立",
        "confidence": "low",
        "status": "进行中",
        "provenance": {"author": "测试", "date": "2026-09-20", "source": "模拟"},
    }


class TestCliApplyClarification(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.record = Path(self._tmp.name) / "record.json"
        self.record.write_text(json.dumps(_record(), ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_answer_is_persisted_into_archive(self):
        r = run_cli("apply-clarification", str(self.record), KEY, "--answer", ANSWER)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        data = json.loads(r.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(ANSWER, data["payload"]["clarifications"][0]["answer"])
        self.assertEqual(KEY, data["payload"]["clarifications"][0]["key"])
        self.assertTrue(data["payload"]["clarifications"][0]["at"])
        self.assertEqual([], data["payload"]["missing_info"])
        self.assertNotIn("未提供 --answer",
                         json.dumps(data["warnings"], ensure_ascii=False))

    def test_without_answer_warns_and_leaves_no_trace(self):
        r = run_cli("apply-clarification", str(self.record), KEY)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        data = json.loads(r.stdout)
        self.assertNotIn("clarifications", data["payload"])
        self.assertTrue(any("未提供 --answer" in w for w in data["warnings"]),
                        "少了「只记账、不留痕」的显式提示：%s" % data["warnings"])


if __name__ == "__main__":
    unittest.main()
