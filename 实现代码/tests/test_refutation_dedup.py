"""人工纠错记录的去重口径（两端一致性护栏的 Python 侧）。

背景（2026-09-23 去重口径修改）：纠错记录的 `attempt` 固定是「对 R-00X 的人工纠错」、
`blocker` 拷贝目标记录、`links[].same/diff` 与 `artifacts` 全为空 —— 通用指纹的四段
**与理由无关**。结果：同一档案被反驳两次、理由完全不同，指纹相同，第二条被当重复丢弃。

方案 C：按记录类型选键。
- 普通记录：指纹一个字都不改（下面 test_normal_records_semantics_unchanged 锁住）。
- 纠错记录：新键 = 「人工纠错」标记 + 目标档案编号 + 归一化理由（复用 Deduplicator.normalize）。

两端对应实现：`src/rra/library/dedup.py::key_of` / `web/js/store.js::dedupKey`
（去重指纹样本一致性见 `reports/contract-parity.json` 的 dedup_samples 与
`web/tests/contract-parity.mjs`）。
"""

import tempfile
import unittest
from pathlib import Path

from rra.contracts.models import Archive, Library
from rra.library.dedup import Deduplicator
from rra.library.store import LibraryStore

# 纠错记录引用的目标档案（quote 必须取自它可核验的字段之一）。
TARGET = {
    "id": "R-001",
    "attempt": "把 micro-batch 从 8 降到 2 并开启梯度累积跑长序列",
    "expectation": "在 24G 显存上完成训练",
    "observation": "显存仍不足，200 step 内 OOM 两次",
    "blocker": "长序列下单卡显存不足",
    "attribution": {"text": "怀疑是注意力矩阵开销随序列长度平方增长", "type": "assumption"},
    "boundary": "该结论仅在单卡 24G 时成立",
    "confidence": "low",
    "status": "进行中",
    "provenance": {"author": "甲", "date": "2026-08-14", "source": "模拟"},
}


def refutation(rid, reason, target="R-001", links=None, attempt=None):
    """网页端「反驳」按钮写出的记录形状（见 web/js/refute.js）。"""
    return {
        "id": rid,
        "attempt": attempt if attempt is not None else ("对 %s 的人工纠错" % target),
        "expectation": "修正 %s 的判断" % target,
        "observation": reason,
        "blocker": TARGET["blocker"],
        "attribution": {"text": "人工纠错：" + reason, "type": "observed"},
        "boundary": "仅针对 %s 的判断，不改变其原始记录" % target,
        "confidence": "medium",
        "status": "进行中",
        "missing_info": [],
        "artifacts": [],
        "links": links if links is not None else [
            {"target": target, "relation": "冲突", "same": [], "diff": [], "transferable": ""}],
        "evidence_refs": [{"record": target, "quote": TARGET["blocker"]}],
        "version": 1,
        "provenance": {"author": "人工纠错", "date": "2026-09-23", "source": "真实"},
    }


def normal(rid, observation):
    """普通记录：除 observation 外，四段指纹输入（attempt/blocker/links/artifacts）全同。"""
    rec = dict(TARGET)
    rec["id"] = rid
    rec["observation"] = observation
    return rec


class TestRefutationDedupKey(unittest.TestCase):
    def setUp(self):
        self.d = Deduplicator()
        self.tmp = tempfile.TemporaryDirectory()
        self.store = LibraryStore(Path(self.tmp.name) / "library.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _base(self):
        return Library(version="0.1", records=[Archive.from_dict(TARGET)])

    def _incoming(self, *raw):
        return Library(version="0.1", records=[Archive.from_dict(r) for r in raw])

    def test_same_target_different_reason_both_merge(self):
        a = refutation("R-002", "显存不足其实是因为 batch 开太大，先降 batch")
        b = refutation("R-003", "这次 OOM 是数据加载瓶颈，与注意力开销无关")
        self.assertNotEqual(self.d.key_of(Archive.from_dict(a)),
                            self.d.key_of(Archive.from_dict(b)))
        merged, report = self.store.merge(self._base(), self._incoming(a, b))
        self.assertEqual(["R-002", "R-003"], report.added)
        self.assertEqual([], report.duplicated)

    def test_same_target_same_reason_is_idempotent(self):
        a = refutation("R-002", "显存不足")
        b = refutation("R-003", "  显存，不足  ")          # 仅空白/标点差异
        self.assertEqual(self.d.key_of(Archive.from_dict(a)),
                         self.d.key_of(Archive.from_dict(b)))
        merged, report = self.store.merge(self._base(), self._incoming(a, b))
        self.assertEqual(["R-002"], report.added)
        self.assertEqual(["R-003"], report.duplicated)

    def test_normal_records_semantics_unchanged(self):
        """普通记录指纹一个字都不改：仅 observation 不同仍判重复。"""
        a = normal("R-010", "OOM 两次")
        b = normal("R-011", "收敛太慢，与显存无关")
        self.assertEqual(self.d.key_of(Archive.from_dict(a)),
                         self.d.key_of(Archive.from_dict(b)))
        # base 用空库：R-010 与 TARGET 同形，放进 base 会让它先被判重复。
        empty = Library(version="0.1", records=[])
        merged, report = self.store.merge(empty, self._incoming(a, b))
        self.assertEqual(["R-010"], report.added)
        self.assertEqual(["R-011"], report.duplicated)

    def test_reason_falls_back_to_attribution_text(self):
        """理由取 observation；为空时退到 attribution.text（与网页端写入的两处同源）。"""
        raw = refutation("R-002", "占位")
        raw["observation"] = ""
        raw["attribution"] = {"text": "其实瓶颈在数据加载", "type": "observed"}
        key = self.d.key_of(Archive.from_dict(raw))
        expected = "\x1f".join([self.d.normalize("人工纠错"), self.d.normalize("R-001"),
                                self.d.normalize("其实瓶颈在数据加载")])
        self.assertEqual(expected, key)

    def test_unresolvable_target_falls_back_without_raising(self):
        raw = refutation("R-050", "这条判断有问题", links=[],
                         attempt="人工纠错：这条判断有问题")
        archive = Archive.from_dict(raw)
        key = self.d.key_of(archive)                      # 不得抛异常
        expected = "\x1f".join([self.d.normalize(archive.attempt),
                                self.d.normalize(archive.blocker), "", ""])
        self.assertEqual(expected, key)                   # 退回现行通用键（四段）


if __name__ == "__main__":
    unittest.main()
