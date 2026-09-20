"""契约校验：必填、枚举、引用格式、dim 合法性。用例 25 的判据落在这里。"""

import json
import unittest
from pathlib import Path

from rra.contracts.validator import Validator

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "contracts" / "fixtures"


class TestValidator(unittest.TestCase):
    def setUp(self):
        self.v = Validator()

    def load(self, name):
        return json.loads((FIX / name).read_text(encoding="utf-8"))

    def test_missing_required_field(self):
        """缺 expectation（夹具 invalid_missing_field.json）必须报出具体路径。"""
        vs = self.v.validate_archive(self.load("invalid_missing_field.json"))
        self.assertTrue(any(x.path == "expectation" for x in vs), vs)

    def test_free_text_dim_rejected(self):
        """dim 写自由文本（夹具 invalid_free_text_dim.json）必须被拒绝。"""
        vs = self.v.validate_archive(self.load("invalid_free_text_dim.json"))
        self.assertTrue(any(x.path.startswith("links[0].same[0].dim") for x in vs), vs)

    def test_short_quote_rejected(self):
        """证据引用的原文片段过短（夹具 invalid_quote_too_short.json）必须被拒绝。"""
        vs = self.v.validate_archive(self.load("invalid_quote_too_short.json"))
        self.assertTrue(any(x.path.startswith("evidence_refs[0].quote") for x in vs), vs)

    def test_dim_is_enum(self):
        self.assertTrue(self.v.dim_is_enum("seq_len"))
        self.assertFalse(self.v.dim_is_enum("序列长度差不多"))

    def test_violation_str_has_all_three(self):
        """Violation 的字符串必须含路径、原因、期望三要素，不允许只说「有问题」。"""
        from rra.contracts.validator import Violation
        s = str(Violation(path="blocker", reason="缺失", expected="非空字符串"))
        for part in ("blocker", "缺失", "非空字符串"):
            self.assertIn(part, s)

    def test_unknown_key_rejected(self):
        """契约声明了 additionalProperties: false，未知字段必须被拒。"""
        raw = self.load("valid_record.json")
        raw["foo"] = 1
        vs = self.v.validate_archive(raw)
        self.assertTrue(any(x.path == "foo" for x in vs), [str(x) for x in vs])

    def test_non_string_required_field_rejected(self):
        raw = self.load("valid_record.json")
        raw["attempt"] = 42
        vs = self.v.validate_archive(raw)
        self.assertTrue(any(x.path == "attempt" for x in vs), [str(x) for x in vs])

    def test_library_with_null_element_reports_violation_not_crash(self):
        """畸形库（records 里有 null）必须报违规，而不是把校验器打崩。"""
        vs = self.v.validate_library({"version": "0.1", "records": [None]})
        self.assertTrue(vs)
        self.assertTrue(any("records[0]" in x.path for x in vs), [str(x) for x in vs])

    def test_evidence_record_format_checked(self):
        raw = self.load("valid_record.json")
        raw["evidence_refs"] = [{"record": "R-8", "quote": "足够长的原文片段"}]
        vs = self.v.validate_archive(raw)
        self.assertTrue(any("evidence_refs[0].record" in x.path for x in vs), [str(x) for x in vs])

    def test_valid_fixture_passes(self):
        vs = self.v.validate_archive(self.load("valid_record.json"))
        self.assertEqual([], vs, [str(x) for x in vs])


if __name__ == "__main__":
    unittest.main()
