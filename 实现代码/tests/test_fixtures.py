"""契约夹具：两端校验器必须对同一组夹具给出同样的结论。

夹具是防止「Python 与网页两份校验器漂移」的唯一手段。
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "contracts" / "fixtures"


class TestFixtures(unittest.TestCase):
    def load(self, name):
        return json.loads((FIX / name).read_text(encoding="utf-8"))

    def test_valid_record_passes(self):
        from rra.contracts.validator import Validator
        self.assertEqual([], Validator().validate_archive(self.load("valid_record.json")))

    def test_missing_field_rejected(self):
        from rra.contracts.validator import Validator
        self.assertTrue(Validator().validate_archive(self.load("invalid_missing_field.json")))

    def test_free_text_dim_rejected(self):
        from rra.contracts.validator import Validator
        self.assertTrue(Validator().validate_archive(self.load("invalid_free_text_dim.json")))

    def test_short_quote_rejected(self):
        from rra.contracts.validator import Validator
        self.assertTrue(Validator().validate_archive(self.load("invalid_quote_too_short.json")))


if __name__ == "__main__":
    unittest.main()
