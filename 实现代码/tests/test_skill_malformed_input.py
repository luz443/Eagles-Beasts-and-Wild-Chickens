"""P2-7：技能层的取值处必须自己判类型，畸形输入抛 ValueError 而不是 AttributeError。

红的最小复现（三个入口）：
- `ConditionCompareSkill().differing_dims({"conditions": "seq_len=2048"}, ...)`
- `InductionSkill().eligible_groups(["not-a-dict"])`
- `ResurrectionSkill().candidates({"records": ["x"]})`

原实现直接 `.items()` / `.get()`，畸形输入把 AttributeError 抛给调用方——
按 `skills/base.py` 的契约，规格问题要给出「哪里不对、实际是什么类型」的 ValueError。
"""

import unittest

from rra.skills.condition_compare import ConditionCompareSkill
from rra.skills.induction import InductionSkill
from rra.skills.resurrection import ResurrectionSkill


class TestMalformedInputRaisesValueError(unittest.TestCase):
    def assert_type_named(self, ctx, expected_type="str"):
        text = str(ctx.exception)
        self.assertIn(expected_type, text, "错误信息没指出元素类型：%s" % text)

    def test_condition_compare_string_conditions(self):
        with self.assertRaises(ValueError) as ctx:
            ConditionCompareSkill().differing_dims(
                {"conditions": "seq_len=2048"}, {"conditions": {"seq_len": "512"}})
        self.assert_type_named(ctx)

    def test_condition_compare_non_object_record(self):
        with self.assertRaises(ValueError) as ctx:
            ConditionCompareSkill().verdict("不是对象", {})
        self.assert_type_named(ctx)

    def test_induction_non_object_record(self):
        with self.assertRaises(ValueError) as ctx:
            InductionSkill().eligible_groups(["not-a-dict"])
        self.assert_type_named(ctx)

    def test_resurrection_non_object_record(self):
        with self.assertRaises(ValueError) as ctx:
            ResurrectionSkill().candidates({"records": ["x"]})
        self.assert_type_named(ctx)

    def test_well_formed_input_still_works(self):
        """补类型判断不得改变正常路径的结论。"""
        self.assertEqual(["seq_len"], ConditionCompareSkill().differing_dims(
            {"conditions": {"seq_len": "2048"}}, {"conditions": {"seq_len": "512"}}))
        recs = [{"id": "R-00%d" % i, "blocker": "显存不足"} for i in (1, 2, 3)]
        self.assertEqual(["R-001", "R-002", "R-003"],
                         [r["id"] for r in InductionSkill().eligible_groups(recs)["显存不足"]])
        self.assertEqual(["R-001"], [r["id"] for r in ResurrectionSkill().candidates(
            {"records": [{"id": "R-001", "status": "已放弃", "blocker": "显存不足"}]})])


if __name__ == "__main__":
    unittest.main()
