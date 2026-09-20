"""去重指纹：同一档案多次计算结果必须一致；内容不同指纹必须不同。"""

import unittest

from rra.contracts.models import Archive
from rra.library.dedup import Deduplicator


def rec(attempt="长序列训练", blocker="显存不足", cond=""):
    return Archive.from_dict({
        "id": "R-001",
        "attempt": attempt,
        "expectation": "跑通",
        "observation": "OOM",
        "blocker": blocker,
        "attribution": {"text": "猜", "type": "assumption"},
        "boundary": "",
        "confidence": "low",
        "status": "进行中",
        "provenance": {"author": "甲", "date": "2026-08-01", "source": "模拟"},
        "artifacts": [{"kind": "code", "ref": cond}] if cond else [],
    })


class TestDedup(unittest.TestCase):
    def test_fingerprint_stable(self):
        d = Deduplicator()
        self.assertEqual(d.key_of(rec()), d.key_of(rec()))

    def test_fingerprint_normalizes_whitespace_and_case(self):
        d = Deduplicator()
        a = rec(attempt="长序列 训练", blocker="显存不足")
        b = rec(attempt="长序列训练", blocker=" 显存不足 ")
        self.assertEqual(d.key_of(a), d.key_of(b))

    def test_fingerprint_includes_link_conditions(self):
        """指纹必须包含关键条件（文档口径：尝试 + 阻塞点 + 关键条件）。"""
        from rra.contracts.models import Archive
        base = {
            "id": "R-001", "attempt": "长序列训练", "expectation": "跑通",
            "observation": "OOM", "blocker": "显存不足",
            "attribution": {"text": "猜", "type": "assumption"},
            "boundary": "", "confidence": "low", "status": "进行中",
            "provenance": {"author": "甲", "date": "2026-08-01", "source": "模拟"},
        }
        a = dict(base, links=[{"target": "R-002", "relation": "相似",
                               "same": [{"dim": "seq_len", "value": "512"}], "diff": []}])
        b = dict(base, links=[{"target": "R-002", "relation": "相似",
                               "same": [{"dim": "seq_len", "value": "2048"}], "diff": []}])
        d = Deduplicator()
        self.assertNotEqual(d.key_of(Archive.from_dict(a)), d.key_of(Archive.from_dict(b)))

    def test_fingerprint_differs_on_content(self):
        d = Deduplicator()
        self.assertNotEqual(d.key_of(rec(blocker="显存不足")),
                            d.key_of(rec(blocker="收敛太慢")))


if __name__ == "__main__":
    unittest.main()
