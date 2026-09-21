"""`tools/` 下三个入口的冒烟：能跑通、产物对得上，而且**能失败**。

为什么单独测工具：`tools/` 是给人用的命令行入口（不是被 import 的库），
`run_tests.py` 只覆盖了 `run_eval.py` 与 `make_contract_parity.py`。
剩下这两个是「种子数据 → 库文件 → 同步给网页」这条链上的人工步骤，
坏了不会有任何测试响——而它一坏，网页拿到的就是旧数据。

第三条测试最要紧：「验证脚本自身也要能被证伪」是本项目踩过的坑——
曾经因为正则被双重转义，报出「0/0 全干净」的假阴性。所以这里专门喂一份坏库，
要求工具**报错并退 1**，而不是一律返回成功。
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_tool(relative: str):
    """按文件路径加载 tools/ 下的脚本（tools/ 不是包，没有 __init__.py）。"""
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location("tool_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMakeSeed(unittest.TestCase):
    def test_generates_expected_library(self):
        mod = load_tool("tools/make_seed.py")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "seed.json"
            self.assertEqual(0, mod.MakeSeedCli(str(out)).run())
            self.assertTrue(out.is_file())
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(15, len(data["records"]))
            self.assertEqual({r["provenance"]["source"] for r in data["records"]}, {"模拟"})

    def test_self_check_can_fail(self):
        """自检必须能被证伪：把门槛抬到不可能满足的高度，必须报错并退 1。"""
        from rra.seed.generator import SeedGenerator, SeedPlan
        gen = SeedGenerator(SeedPlan(total=15, same_blocker_cluster=99))
        self.assertTrue(gen.check_plan(gen.generate()))


class TestValidateLibrary(unittest.TestCase):
    def setUp(self):
        self.mod = load_tool("tools/validate_library.py")
        self.seed_mod = load_tool("tools/make_seed.py")
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.source = self.dir / "library.seed.json"
        self.target = self.dir / "web" / "library.sample.json"
        self.seed_mod.MakeSeedCli(str(self.source)).run()

    def tearDown(self):
        self.tmp.cleanup()

    def test_syncs_valid_library(self):
        rc = self.mod.ValidateLibraryCli(str(self.source), str(self.target)).run()
        self.assertEqual(0, rc)
        self.assertTrue(self.target.is_file())
        # 网页要用三份产物：json（fetch）、js（file:// 回落）、scoring.json（召回权重）
        self.assertTrue(self.target.with_suffix(".js").is_file())
        self.assertTrue((self.target.parent / "scoring.json").is_file())
        self.assertIn("SAMPLE_LIBRARY",
                      self.target.with_suffix(".js").read_text(encoding="utf-8"))

    def test_invalid_library_fails_loudly(self):
        """坏库必须退 1——否则网页会安静地拿到一份非法数据。"""
        raw = json.loads(self.source.read_text(encoding="utf-8"))
        raw["records"][0]["evidence_refs"] = [{"record": "R-404", "quote": "指向不存在的档案"}]
        self.source.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        self.assertEqual(1, self.mod.ValidateLibraryCli(str(self.source), str(self.target)).run())


if __name__ == "__main__":
    unittest.main()
