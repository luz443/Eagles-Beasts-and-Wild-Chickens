"""召回分词：关键词多一个字就召不回（2026-09-22 后端审查 P1-5 的回归）。

原实现把中文按「非重叠 2-gram」切：`显存` → ['显存']，`查显存` → ['查显','存']，
丢单字后真关键词「显存」直接消失，于是
`recall data/library.seed.json 查显存` 命中 0 条并打印「没有区分度…不要编造命中」——
它会把用例 15-17（"库内无相关经验须如实报告"）反向带偏：库里明明有经验，却被报成没有。

本文件钉三件事：
1. 重叠 bigram：`显存` 与 `查显存` 必须召回**同一条**记录；
2. explain 里必须出现真正命中的 token 原文（不能只剩「查显」这类碎片当唯一解释）；
3. 单字查询仍返回空——「宁少不凑」的门限不许被顺手改坏（tests/test_scorer.py 也盯着）。
"""

import json
import unittest
from pathlib import Path

from rra.contracts.models import Archive, Library
from rra.recall.scorer import RecallScorer, _tokens

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "library.seed.json"


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


class TestTokensKeepKeywords(unittest.TestCase):
    def test_longer_query_still_produces_the_keyword(self):
        self.assertIn("显存", _tokens("显存"))
        self.assertIn("显存", _tokens("查显存"))

    def test_single_char_is_still_dropped(self):
        self.assertEqual([], _tokens("不"))


class TestRecallIsStableAcrossQueryLength(unittest.TestCase):
    def test_short_and_long_query_recall_the_same_record(self):
        lib = Library(version="0.1", records=[rec("R-001")])
        short = {h.record_id for h in RecallScorer().recall("显存", lib)}
        longer = {h.record_id for h in RecallScorer().recall("查显存", lib)}
        self.assertTrue(short, "`显存` 应当召回")
        self.assertEqual(short, longer, "多一个字就把命中全丢了：%s vs %s" % (short, longer))

    def test_explain_carries_the_matched_token_text(self):
        hit = RecallScorer().score("查显存", rec("R-001"))
        joined = "；".join(hit.explain)
        self.assertIn("显存", joined,
                      "explain 必须写明真正命中的词，而不是只剩切出来的碎片：%s" % joined)

    def test_seed_library_answers_both_wordings(self):
        """真实种子库上钉一遍：`显存` 与 `查显存` 都必须召回同一条库内记录。"""
        lib = Library.from_dict(json.loads(SEED.read_text(encoding="utf-8")))
        scorer = RecallScorer()
        short = scorer.recall("显存", lib)
        longer = scorer.recall("查显存", lib)
        self.assertTrue(short, "`显存` 在种子库上应当有命中")
        self.assertTrue(longer, "`查显存` 在种子库上应当有命中（否则用例 15-17 会被带偏）")
        shared = {h.record_id for h in short} & {h.record_id for h in longer}
        self.assertTrue(shared, "两种问法应能召回同一条记录，实际：%s / %s"
                        % (sorted(h.record_id for h in short),
                           sorted(h.record_id for h in longer)))

    def test_single_char_query_returns_empty(self):
        self.assertEqual([], RecallScorer().recall("不", Library(version="0.1", records=[rec("R-001")])))

    def test_unrelated_query_still_returns_empty(self):
        lib = Library(version="0.1", records=[rec("R-001")])
        self.assertEqual([], RecallScorer().recall("文献综述怎么写", lib))


if __name__ == "__main__":
    unittest.main()
