"""人工纠错记录的过滤规则（两端一致性护栏）。

规则真源：`src/rra/library/refutation.py`；
网页端对应实现：`web/js/refute.js` 与 `web/js/views/incubation.js`。

本文件锁住的是一类**静默不一致**：同一个库，网页说「还没积累到 3 条」，
专家侧却认为够 3 条并产出假设。改任何一端都会在这里或
`web/tests/refutation-rule-parity.mjs` 失败。
"""

import unittest

from rra.library.refutation import MARKER, exclude_refutations, is_refutation
from rra.skills.induction import InductionSkill


def rec(rid, blocker, attempt=None):
    return {"id": rid, "attempt": attempt if attempt is not None else "尝试 " + rid,
            "blocker": blocker, "status": "进行中", "confidence": "low",
            "attribution": {"text": "x", "type": "assumption"}}


def refutation(rid, target, blocker):
    """网页端「反驳」按钮实际写出的记录形状（见 web/js/refute.js）。"""
    return {"id": rid, "attempt": "对 " + target + " 的人工纠错", "blocker": blocker,
            "status": "进行中", "confidence": "medium",
            "attribution": {"text": "人工纠错：理由", "type": "observed"}}


class TestIsRefutation(unittest.TestCase):
    def test_exact_marker(self):
        self.assertTrue(is_refutation(refutation("R-015", "R-001", "显存不足")))

    def test_marker_inside_longer_attempt(self):
        self.assertTrue(is_refutation(rec("R-016", "b", attempt="补充：有人工纠错标记的尝试")))

    def test_normal_record_is_not_refutation(self):
        self.assertFalse(is_refutation(rec("R-001", "显存不足")))

    def test_missing_or_bad_shape(self):
        self.assertFalse(is_refutation({}))
        self.assertFalse(is_refutation(None))
        self.assertFalse(is_refutation("对 R-001 的人工纠错"))
        self.assertFalse(is_refutation({"attempt": 12345}))

    def test_marker_literal_matches_web(self):
        """字面量必须与网页端逐字一致——这是两端规则的连接点。"""
        self.assertEqual(MARKER, "人工纠错")


class TestInductionGate(unittest.TestCase):
    def test_two_real_plus_one_refutation_produces_no_group(self):
        """网页端注释里的那个反例：2 条真实 + 1 条纠错，不得凑满 3 条产出假设。"""
        records = [rec("R-001", "显存不足"), rec("R-002", "显存不足"),
                   refutation("R-015", "R-001", "显存不足")]
        self.assertEqual(InductionSkill().eligible_groups(records), {})

    def test_three_real_plus_refutation_group_has_exactly_three(self):
        records = [rec("R-001", "显存不足"), rec("R-002", "显存不足"), rec("R-003", "显存不足"),
                   refutation("R-015", "R-001", "显存不足")]
        groups = InductionSkill().eligible_groups(records)
        self.assertEqual(list(groups.keys()), ["显存不足"])
        self.assertEqual([r["id"] for r in groups["显存不足"]], ["R-001", "R-002", "R-003"])

    def test_exclude_keeps_order_and_does_not_mutate(self):
        records = [rec("R-001", "b"), refutation("R-015", "R-001", "b"), rec("R-002", "b")]
        before = list(records)
        out = exclude_refutations(records)
        self.assertEqual([r["id"] for r in out], ["R-001", "R-002"])
        self.assertEqual(records, before)

    def test_non_list_input_safe(self):
        self.assertEqual(exclude_refutations(None), [])
        self.assertEqual(exclude_refutations("x"), [])


if __name__ == "__main__":
    unittest.main()
