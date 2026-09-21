"""证据引用的「原文核验」回归（2026-09-19 外部审查 P0）。

原缺陷：`validate_archive` 只检查引用编号格式、`validate_library` 只检查编号是否存在，
再加上 quote 长度 ≥4 —— 于是**编造一段 4 字以上的"原文"也能通过**，
"证据引用必须带档案编号 + 原文片段"这条核心约束在代码层是空的。

本文件锁住修复后的行为：`validate_library` 必须验证 quote 真的出现在**被引用档案**的
可核验字段里（与网页端 refute.js 取引文的字段集一致：attribution.text / observation / blocker）。
"""

import unittest

from rra.contracts.validator import Validator


def archive(rid, *, observation="观测到显存溢出", blocker="长序列训练显存不足",
            attribution_text="怀疑 batch 过大", evidence_refs=None, links=None):
    rec = {
        "id": rid, "attempt": "尝试 " + rid, "expectation": "跑完",
        "observation": observation, "blocker": blocker,
        "attribution": {"text": attribution_text, "type": "assumption"},
        "boundary": "单卡 24G", "confidence": "low", "status": "进行中",
        "provenance": {"author": "测试", "date": "2026-09-19", "source": "模拟"},
    }
    if evidence_refs is not None:
        rec["evidence_refs"] = evidence_refs
    if links is not None:
        rec["links"] = links
    return rec


def library(records):
    return {"version": "0.1.0", "generated_at": "2026-09-19", "records": records}


class TestEvidenceQuoteVerification(unittest.TestCase):
    def setUp(self):
        self.v = Validator()

    def test_fabricated_quote_is_rejected(self):
        """核心用例：引文与目标档案完全无关 → 必须报违规（原实现会放过）。"""
        lib = library([
            archive("R-001"),
            archive("R-002", evidence_refs=[{"record": "R-001", "quote": "这是虚构证据够长了"}]),
        ])
        vs = self.v.validate_library(lib)
        paths = [x.path for x in vs]
        self.assertIn("records[1].evidence_refs[0].quote", paths)
        msg = str([x for x in vs if x.path.endswith(".quote")][0])
        self.assertIn("原文", msg)          # 原因与期望都要说清「原文」这件事

    def test_quote_from_observation_passes(self):
        lib = library([
            archive("R-001", observation="第 40 step 触发 CUDA OOM"),
            archive("R-002", evidence_refs=[{"record": "R-001", "quote": "第 40 step 触发 CUDA OOM"}]),
        ])
        self.assertEqual(self.v.validate_library(lib), [])

    def test_quote_from_blocker_passes(self):
        lib = library([
            archive("R-001", blocker="长序列训练显存不足"),
            archive("R-002", evidence_refs=[{"record": "R-001", "quote": "训练显存不足"}]),
        ])
        self.assertEqual(self.v.validate_library(lib), [])

    def test_quote_from_attribution_text_passes(self):
        lib = library([
            archive("R-001", attribution_text="怀疑 batch 过大导致激活值超限"),
            archive("R-002", evidence_refs=[
                {"record": "R-001", "quote": "怀疑 batch 过大导致激活值超限"}]),
        ])
        self.assertEqual(self.v.validate_library(lib), [])

    def test_whitespace_and_width_are_tolerated(self):
        """引文里多打了空格、全角半角混用不该误报（复用去重同一套 normalize）。"""
        lib = library([
            archive("R-001", observation="第 40 step 触发 CUDA OOM"),
            archive("R-002", evidence_refs=[{"record": "R-001", "quote": "第40 step 触发CUDA　OOM"}]),
        ])
        self.assertEqual(self.v.validate_library(lib), [])

    def test_single_archive_validation_has_no_library_context(self):
        """明确边界：单档案校验拿不到别的档案，跨档案核验只发生在整库校验里。"""
        one = archive("R-002", evidence_refs=[{"record": "R-001", "quote": "这是虚构证据够长了"}])
        self.assertEqual(self.v.validate_archive(one), [])
        self.assertNotEqual(self.v.validate_library(library([
            archive("R-001"), one])), [])

    def test_seed_library_quotes_are_all_verifiable(self):
        """真实种子库自检：15 条记录里每一处 evidence_refs 都必须能在目标档案中找到原文。"""
        import json
        from pathlib import Path
        seed = Path(__file__).resolve().parents[1] / "data" / "library.seed.json"
        lib = json.loads(seed.read_text(encoding="utf-8"))
        bad = [str(v) for v in self.v.validate_library(lib) if "quote" in v.path]
        self.assertEqual(bad, [], "种子数据里出现了不可核验的引用片段：%s" % bad)


if __name__ == "__main__":
    unittest.main()
