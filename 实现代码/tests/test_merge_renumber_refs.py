"""P1-3：合并重编号必须同步改写引用、不与既有编号撞车、库级版本递增。

红的最小复现：base=[R-001]，incoming=[R-001(内容不同), R-002(links.target=R-001)]。
原实现在 `next_id` 上「边加边判」——第一次重编号把 R-002 占掉之后，
第二条 incoming 记录（本来就叫 R-002）又被判成撞号、再次改名，
而它的 `links.target` 仍写着 R-001，于是指向了**另一条**记录；
`validate_library` 却报不出任何违规（引用的编号确实存在，只是指错了人）。
"""

import unittest
from pathlib import Path

from rra.contracts.models import Archive, Library
from rra.contracts.validator import Validator
from rra.library.store import LibraryStore


def rec(rid, **over):
    """一条通过契约的档案（编号字段留给调用方覆盖）。"""
    data = {
        "id": rid,
        "attempt": "尝试 %s" % rid,
        "expectation": "跑通训练",
        "observation": "OOM 两次",
        "blocker": "长序列训练显存不足",
        "attribution": {"text": "怀疑注意力开销", "type": "assumption"},
        "boundary": "单卡 24G",
        "confidence": "low",
        "status": "进行中",
        "provenance": {"author": "甲", "date": "2026-08-01", "source": "模拟"},
    }
    data.update(over)
    return data


def lib(version, *records):
    return Library(version=version, records=[Archive.from_dict(r) for r in records])


def version_parts(version):
    return [int(x) for x in str(version).split(".")]


class TestMergeRenumbering(unittest.TestCase):
    def setUp(self):
        self.store = LibraryStore(Path("unused.json"))
        self.base = lib("0.1.0", rec("R-001"))

    def incoming_with_link(self):
        return lib("0.1.0",
                   rec("R-001", attempt="完全不同的另一次尝试"),
                   rec("R-002", links=[{"target": "R-001", "relation": "相似"}]))

    def test_renumbering_rewrites_references(self):
        merged, report = self.store.merge(self.base, self.incoming_with_link())
        self.assertIn("R-001", report.renumbered)
        new_id = report.renumbered["R-001"]
        self.assertNotIn("R-002", report.renumbered,
                         "没撞号的 R-002 不该被级联重命名：%s" % report.renumbered)
        got = merged.index()["R-002"]
        self.assertEqual([new_id], [link.target for link in got.links],
                         "重编号后 links.target 没跟着改写，指向了另一条记录")
        self.assertEqual([], Validator().validate_library(merged.to_dict()))

    def test_renumbering_does_not_collide(self):
        merged, report = self.store.merge(self.base, self.incoming_with_link())
        ids = [r.id for r in merged.records]
        self.assertEqual(len(ids), len(set(ids)), "编号撞车：%s" % ids)
        self.assertEqual(sorted(["R-001", "R-002", report.renumbered["R-001"]]), sorted(ids))

    def test_library_version_is_bumped(self):
        merged, _ = self.store.merge(self.base, self.incoming_with_link())
        self.assertGreater(version_parts(merged.version), version_parts(self.base.version),
                           "库级版本没有递增：%s" % merged.version)

    def test_remap_from_keeps_earlier_hop(self):
        """重编号不得覆盖既有 remap_from：它记录的是更早的一跳。"""
        base = lib("0.1", rec("R-001"))
        incoming = lib("0.1", rec("R-001", attempt="另一次尝试",
                                  provenance={"author": "甲", "date": "2026-08-01",
                                              "source": "模拟", "remap_from": "R-900"}))
        merged, report = self.store.merge(base, incoming)
        got = merged.index()[report.renumbered["R-001"]]
        self.assertEqual("R-900", got.provenance.remap_from)

    def test_invalid_merge_result_raises(self):
        """合并末尾必须校验结果：指向库外编号时抛 ValueError，而不是静默返回坏库。"""
        base = lib("0.1", rec("R-001"))
        incoming = lib("0.1", rec("R-002", links=[{"target": "R-777", "relation": "相似"}]))
        with self.assertRaises(ValueError):
            self.store.merge(base, incoming)


if __name__ == "__main__":
    unittest.main()
