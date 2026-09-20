"""契约：维度枚举必须与 contracts/dim.json 一致。"""

import json
import unittest
from pathlib import Path

from rra.contracts.dims import DIM_LABELS, Dim

ROOT = Path(__file__).resolve().parents[1]


class TestDims(unittest.TestCase):
    def test_enum_matches_schema(self):
        raw = json.loads((ROOT / "contracts" / "dim.json").read_text(encoding="utf-8"))
        self.assertEqual([d["key"] for d in raw["dims"]], [d.value for d in Dim])

    def test_labels_cover_all_dims(self):
        self.assertEqual(len(Dim), len(DIM_LABELS))
        for d in Dim:
            self.assertTrue(DIM_LABELS[d])

    def test_schema_dim_enum_matches(self):
        """record.schema.json 里没有写死 dim 枚举，靠 validator 的枚举集合兜底；
        这里确认 validator 接受的集合与 Dim 完全一致。"""
        from rra.contracts.validator import Validator
        v = Validator()
        for d in Dim:
            self.assertTrue(v.dim_is_enum(d.value))
        self.assertFalse(v.dim_is_enum("序列长度"))


if __name__ == "__main__":
    unittest.main()
