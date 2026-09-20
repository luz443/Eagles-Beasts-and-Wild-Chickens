"""契约：数据类往返序列化不能丢字段，且必须与夹具一致。"""

import json
import unittest
from pathlib import Path

from rra.contracts.models import Archive

ROOT = Path(__file__).resolve().parents[1]


class TestModels(unittest.TestCase):
    def setUp(self):
        raw = (ROOT / "contracts" / "fixtures" / "valid_record.json").read_text(encoding="utf-8")
        self.raw = json.loads(raw)

    def test_roundtrip_keeps_all_fields(self):
        """往返一次后必须与原字典一致；version 缺省补 1。"""
        expected = dict(self.raw)
        expected.setdefault("version", 1)
        self.assertEqual(expected, Archive.from_dict(self.raw).to_dict())

    def test_version_defaults_to_1(self):
        self.assertEqual(1, Archive.from_dict(self.raw).version)

    def test_citation_format(self):
        self.assertTrue(Archive.from_dict(self.raw).citation().startswith("R-013@v"))

    def test_library_roundtrip_and_index(self):
        """库往返不能丢档案；编号重复必须报错。"""
        from rra.contracts.models import Library
        raw = {"version": "0.1.0", "generated_at": "2026-08-14", "records": [self.raw]}
        lib = Library.from_dict(raw)
        self.assertEqual(1, len(lib.index()))
        expected = dict(raw)
        expected["records"] = [dict(self.raw, version=1)]
        self.assertEqual(expected, lib.to_dict())


if __name__ == "__main__":
    unittest.main()
