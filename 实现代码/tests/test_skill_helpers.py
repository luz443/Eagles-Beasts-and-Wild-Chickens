"""五个技能的确定性部分：条件门禁、孵化门槛、复活候选、质询有据、澄清回填。"""

import unittest

from rra.skills.condition_compare import ConditionCompareSkill
from rra.skills.induction import InductionSkill
from rra.skills.reverse_lookup import ReverseLookupSkill
from rra.skills.resurrection import ResurrectionSkill
from rra.skills.reviewer2 import Reviewer2Skill
from rra.skills.base import SkillInput, SkillOutput


class TestConditionCompare(unittest.TestCase):
    """核心规则：任一维度不同 → 不得判为冲突。"""

    def setUp(self):
        self.s = ConditionCompareSkill()
        self.full = {dim: dim + "-value" for dim in self.s.DIM_ORDER}

    def test_differing_dim_blocks_conflict(self):
        a = {"conditions": {"seq_len": "2048"}, "conclusions_conflict": True}
        b = {"conditions": {"seq_len": "512"}, "conclusions_conflict": True}
        self.assertEqual("条件不同", self.s.verdict(a, b))

    def test_same_conditions_plus_conflict_is_real_conflict(self):
        a = {"conditions": self.full, "conclusions_conflict": True}
        b = {"conditions": dict(self.full), "conclusions_conflict": True}
        self.assertEqual("真冲突", self.s.verdict(a, b))

    def test_same_conditions_no_conflict_is_same_issue(self):
        a = {"conditions": self.full, "conclusions_conflict": False}
        b = {"conditions": dict(self.full), "conclusions_conflict": False}
        self.assertEqual("同一问题", self.s.verdict(a, b))

    def test_any_missing_dim_makes_verdict_inconclusive(self):
        partial = dict(self.full)
        partial.pop("hardware")
        a = {"conditions": self.full, "conclusions_conflict": True}
        b = {"conditions": partial, "conclusions_conflict": True}
        self.assertEqual("条件不全", self.s.verdict(a, b))

    def test_no_shared_dim_is_inconclusive(self):
        """两侧没有任何共同维度时必须报"条件不全"，不得下结论。"""
        a = {"conditions": {"model": "A"}, "conclusions_conflict": True}
        b = {"conditions": {"seq_len": "2048"}, "conclusions_conflict": True}
        self.assertEqual("条件不全", self.s.verdict(a, b))

    def test_whitespace_only_condition_is_missing_not_different(self):
        a = {"conditions": dict(self.full), "conclusions_conflict": True}
        b = {"conditions": dict(self.full, hardware=" \t "), "conclusions_conflict": True}
        self.assertEqual([], self.s.differing_dims(a, b))
        self.assertEqual("条件不全", self.s.verdict(a, b))

    def test_condition_comparison_trims_values(self):
        a = {"conditions": self.full}
        b = {"conditions": dict(self.full, hardware=" hardware-value ")}
        self.assertEqual("同一问题", self.s.verdict(a, b))

    def test_differing_dims_listed(self):
        a = {"conditions": {"seq_len": "2048", "precision": "bf16"}}
        b = {"conditions": {"seq_len": "512", "precision": "bf16"}}
        self.assertEqual(["seq_len"], self.s.differing_dims(a, b))


class TestInduction(unittest.TestCase):
    def test_eligible_groups_need_three(self):
        recs = [
            {"id": "R-001", "blocker": "显存不足"}, {"id": "R-002", "blocker": "显存不足"},
            {"id": "R-003", "blocker": "显存不足"}, {"id": "R-004", "blocker": "收敛慢"},
        ]
        groups = InductionSkill().eligible_groups(recs)
        self.assertEqual(1, len(groups))
        self.assertEqual("显存不足", list(groups)[0])
        self.assertEqual(3, len(groups["显存不足"]))


class TestResurrection(unittest.TestCase):
    def test_candidates_are_abandoned_with_blocker(self):
        lib = {"records": [
            {"id": "R-001", "status": "已放弃", "blocker": "显存不足"},
            {"id": "R-002", "status": "进行中", "blocker": "显存不足"},
            {"id": "R-003", "status": "已放弃", "blocker": ""},
        ]}
        got = ResurrectionSkill().candidates(lib)
        self.assertEqual(["R-001"], [r["id"] for r in got])


class TestReviewer2(unittest.TestCase):
    def test_challenge_without_evidence_is_invalid(self):
        s = Reviewer2Skill()
        self.assertFalse(s.is_grounded({"text": "这个方向已经失败过", "evidence_ids": []}))
        self.assertFalse(s.is_grounded({"text": "无编号的质疑"}))

    def test_challenge_with_evidence_is_valid(self):
        s = Reviewer2Skill()
        self.assertTrue(s.is_grounded({"text": "已有失败", "evidence_ids": ["R-001", "R-009"]}))


class TestReverseLookupBookkeeping(unittest.TestCase):
    def test_apply_clarification_removes_resolved_keys(self):
        out = SkillOutput(payload={
            "id": "R-013", "attempt": "a", "expectation": "b", "observation": "c",
            "blocker": "d", "attribution": {"text": "x", "type": "assumption"},
            "boundary": "", "confidence": "low", "status": "进行中",
            "provenance": {"author": "甲", "date": "2026-09-19", "source": "模拟"},
            "missing_info": ["micro-batch", "精度"], "version": 1,
        })
        got = ReverseLookupSkill().apply_clarification_facts(out, ["micro-batch"])
        self.assertEqual(["精度"], got.payload["missing_info"])
        self.assertEqual(2, got.payload["version"])
        self.assertTrue(got.warnings)


if __name__ == "__main__":
    unittest.main()
