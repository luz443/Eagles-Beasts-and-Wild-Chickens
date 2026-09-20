"""召回打分：命中解释不得为空；库内无相关记录时必须返回空。"""

import unittest
from pathlib import Path

from rra.contracts.models import Archive, Library
from rra.recall.scorer import RecallScorer

ROOT = Path(__file__).resolve().parents[1]


def rec(rid, blocker="长序列训练显存不足", attempt="降低 micro-batch"):
    return Archive.from_dict({
        "id": rid,
        "attempt": attempt,
        "expectation": "跑通",
        "observation": "OOM",
        "blocker": blocker,
        "attribution": {"text": "猜", "type": "assumption"},
        "boundary": "",
        "confidence": "low",
        "status": "进行中",
        "provenance": {"author": "甲", "date": "2026-08-01", "source": "模拟"},
    })


class TestScorer(unittest.TestCase):
    def test_weights_from_contract(self):
        s = RecallScorer()
        s.load_weights(str(ROOT / "contracts" / "scoring.json"))
        self.assertEqual(3.0, s.weights["blocker"])

    def test_explain_not_empty_when_hit(self):
        s = RecallScorer()
        hits = s.recall("显存不足怎么办", Library(version="0.1", records=[rec("R-001")]))
        self.assertTrue(hits)
        self.assertTrue(hits[0].score > 0)
        self.assertTrue(all(h.explain for h in hits))

    def test_empty_library_returns_empty(self):
        self.assertEqual([], RecallScorer().recall("任意方向", Library(version="0.1", records=[])))

    def test_single_char_query_returns_empty(self):
        """单字查询没有区分度，不得命中（否则"库内无相关记录"会被误报）。"""
        s = RecallScorer()
        lib = Library(version="0.1", records=[rec("R-001")])
        self.assertEqual([], s.recall("不", lib))

    def test_unrelated_query_returns_empty(self):
        s = RecallScorer()
        lib = Library(version="0.1", records=[rec("R-001")])
        self.assertEqual([], s.recall("文献综述怎么写", lib))


if __name__ == "__main__":
    unittest.main()
