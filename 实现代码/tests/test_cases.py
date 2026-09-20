"""用例登记：27 条、盲测 10 条、开放 17 条；编号可查。"""

import unittest

from rra.eval.cases import Case, CaseKind, CaseRegistry


class TestCases(unittest.TestCase):
    def setUp(self):
        self.reg = CaseRegistry.default()

    def test_total_27(self):
        self.assertEqual(27, len(self.reg.cases))

    def test_blind_10_open_17(self):
        self.assertEqual(10, len(self.reg.blind_cases()))
        self.assertEqual(17, len(self.reg.open_cases()))

    def test_numbering_continuous(self):
        nos = sorted(c.no for c in self.reg.cases)
        self.assertEqual(list(range(1, 28)), nos)

    def test_get_by_no(self):
        self.assertEqual(1, self.reg.get(1).no)
        with self.assertRaises(KeyError):
            self.reg.get(99)


if __name__ == "__main__":
    unittest.main()
