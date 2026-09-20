"""库读写、合并去重与重编号：重编号必须记录 remap_from，不得静默覆盖。"""

import json
import tempfile
import unittest
from pathlib import Path

from rra.contracts.models import Library
from rra.library.store import LibraryStore


def rec(rid, attempt="长序列训练", blocker="显存不足"):
    return {
        "id": rid,
        "attempt": attempt,
        "expectation": "跑通训练",
        "observation": "OOM",
        "blocker": blocker,
        "attribution": {"text": "怀疑注意力开销", "type": "assumption"},
        "boundary": "单卡 24G",
        "confidence": "low",
        "status": "进行中",
        "provenance": {"author": "甲", "date": "2026-08-01", "source": "模拟"},
        "dedup_key": "长序列训练|显存不足",
    }


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "library.json"
        self.store = LibraryStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_save_roundtrip(self):
        lib = Library(version="0.1", records=[])
        raw = json.loads(json.dumps({}))  # placeholder to keep imports honest
        self.store.save(lib)
        loaded = self.store.load()
        self.assertEqual(lib.version, loaded.version)

    def test_merge_dedup_by_fingerprint(self):
        base = Library(version="0.1", records=[])
        base.records.append(__import__("rra.contracts.models", fromlist=["Archive"]).Archive.from_dict(rec("R-001")))
        incoming = Library(version="0.1", records=[])
        incoming.records.append(__import__("rra.contracts.models", fromlist=["Archive"]).Archive.from_dict(rec("R-002")))
        merged, report = self.store.merge(base, incoming)
        self.assertEqual(1, len(merged.records))
        self.assertIn("R-002", report.duplicated)

    def test_merge_same_id_different_content_renumbers(self):
        from rra.contracts.models import Archive
        base = Library(version="0.1", records=[Archive.from_dict(rec("R-001", attempt="A"))])
        incoming = Library(version="0.1", records=[Archive.from_dict(rec("R-001", attempt="完全不同的尝试"))])
        merged, report = self.store.merge(base, incoming)
        self.assertEqual(2, len(merged.records))
        self.assertIn("R-001", report.renumbered)
        remapped = report.renumbered["R-001"]
        got = [r for r in merged.records if r.id == remapped]
        self.assertEqual(1, len(got))
        self.assertEqual("R-001", got[0].provenance.remap_from)

    def test_next_id(self):
        from rra.contracts.models import Archive
        lib = Library(version="0.1", records=[Archive.from_dict(rec("R-001")), Archive.from_dict(rec("R-003"))])
        self.assertEqual("R-004", self.store.next_id(lib))


if __name__ == "__main__":
    unittest.main()
