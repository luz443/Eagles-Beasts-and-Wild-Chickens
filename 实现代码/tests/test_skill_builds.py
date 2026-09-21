"""六个技能的 `build()`：把「确定性把关」逐条钉住。

分工前提（见 `src/rra/skills/base.py` 模块文档）：平台上技能脚本**调不到模型**，
语义判断由 LearnBuddy 专家完成，技能代码只做确定性把关。所以这里的测试全部是
「专家交回这份产出时，代码该拦下什么、该放行什么」——不涉及任何语义推断。

每个技能都覆盖三类：
1. 合法产出 → 放行，且规范化符合契约；
2. 违规产出 → `ValueError`（格式/规则问题）；
3. 证据不足 → `SkillRefusal`（该拒绝而不是硬产出）。
"""

import unittest

from rra.contracts.validator import Validator
from rra.skills.base import SkillInput, SkillRefusal
from rra.skills.condition_compare import ConditionCompareSkill
from rra.skills.extract import ExtractSkill
from rra.skills.induction import InductionSkill
from rra.skills.resurrection import ResurrectionSkill
from rra.skills.reverse_lookup import ReverseLookupSkill
from rra.skills.reviewer2 import Reviewer2Skill


def archive(rid="R-013", **over):
    """一条通过契约的档案（与 contracts/fixtures/valid_record.json 同形，但更小）。"""
    base = {
        "id": rid,
        "attempt": "把 micro-batch 降到 2 跑长序列",
        "expectation": "在 24G 显存上完成 seq_len=2048 训练",
        "observation": "显存仍不足，200 step 内 OOM 两次",
        "blocker": "长序列训练显存不足",
        "attribution": {"text": "怀疑是注意力矩阵开销随序列长度平方增长", "type": "assumption"},
        "missing_info": ["micro-batch 实际生效值"],
        "boundary": "单卡 24G、未开 flash-attention 时成立",
        "confidence": "low",
        "status": "进行中",
        "provenance": {"author": "测试", "date": "2026-09-20", "source": "模拟"},
    }
    base.update(over)
    return base


def library(*records):
    return {"version": "1", "records": list(records)}


def inp(expert=None, lib=None, raw="一段实验记录"):
    context = {} if expert is None else {"expert_output": expert}
    return SkillInput(raw_text=raw, library=lib or {}, context=context)


class TestExtractBuild(unittest.TestCase):
    def setUp(self):
        self.skill = ExtractSkill()

    def test_valid_output_passes_and_is_normalized(self):
        raw = archive(conditions={"seq_len": " 2048 ", "batch": "   "},
                      missing_info=["a", "a", " b ", ""])
        out = self.skill.build(inp(raw))
        self.assertEqual({"seq_len": "2048"}, out.payload["conditions"])   # trim + 丢空值
        self.assertEqual(["a", "b"], out.payload["missing_info"])          # 去重保序
        self.assertEqual([], Validator().validate_archive(out.payload))

    def test_assumption_is_warned_not_silently_accepted(self):
        out = self.skill.build(inp(archive()))
        self.assertTrue(any("assumption" in w for w in out.warnings), out.warnings)

    def test_missing_key_fields_refuses_with_names(self):
        for key in ("observation", "blocker", "boundary"):
            with self.assertRaises(SkillRefusal) as ctx:
                self.skill.build(inp(archive(**{key: "   "})))
            self.assertIn(key, ctx.exception.missing)

    def test_bad_enum_is_a_violation_not_a_refusal(self):
        with self.assertRaises(ValueError):
            self.skill.build(inp(archive(attribution={"text": "x", "type": "maybe"})))

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(ValueError):
            self.skill.build(inp(archive(made_up="x")))

    def test_missing_expert_output_refuses(self):
        with self.assertRaises(SkillRefusal):
            self.skill.build(inp())

    def test_run_refuses_on_empty_input(self):
        with self.assertRaises(SkillRefusal):
            self.skill.run(inp(archive(), raw="   "))


class TestReverseLookupBuild(unittest.TestCase):
    def setUp(self):
        self.skill = ReverseLookupSkill()
        self.lib = library(archive("R-008"))

    def test_valid_output_passes(self):
        raw = archive("R-013",
                      evidence_refs=[{"record": "R-008", "quote": "显存仍不足，200 step 内 OOM 两次"}])
        out = self.skill.build(inp(raw, self.lib))
        self.assertEqual([], Validator().validate_archive(out.payload))

    def test_fabricated_record_id_is_rejected(self):
        raw = archive("R-013", evidence_refs=[{"record": "R-999", "quote": "一段够长的引文"}])
        with self.assertRaises(ValueError) as ctx:
            self.skill.build(inp(raw, self.lib))
        self.assertIn("R-999", str(ctx.exception))

    def test_fabricated_link_target_is_rejected(self):
        raw = archive("R-013", links=[{"target": "R-777", "relation": "相似"}])
        with self.assertRaises(ValueError):
            self.skill.build(inp(raw, self.lib))

    def test_short_quote_is_rejected(self):
        raw = archive("R-013", evidence_refs=[{"record": "R-008", "quote": "太短"}])
        with self.assertRaises(ValueError):
            self.skill.build(inp(raw, self.lib))

    def test_no_hits_is_allowed_but_warned(self):
        out = self.skill.build(inp(archive("R-013"), self.lib))
        self.assertEqual([], out.payload.get("evidence_refs", []))
        self.assertTrue(any("没有相关记录" in w for w in out.warnings), out.warnings)

    def test_empty_library_refuses(self):
        with self.assertRaises(SkillRefusal):
            self.skill.build(inp(archive("R-013"), library()))

    def test_clarification_updates_bookkeeping(self):
        start = self.skill.build(inp(archive("R-013"), self.lib))
        after = self.skill.update_after_clarification(start, "micro-batch 实际生效值是 2")
        self.assertEqual([], after.payload["missing_info"])
        self.assertEqual(2, after.payload["version"])
        self.assertTrue(any("已澄清字段" in w for w in after.warnings))

    def test_unmatched_answer_does_not_bump_version(self):
        start = self.skill.build(inp(archive("R-013"), self.lib))
        after = self.skill.update_after_clarification(start, "嗯嗯好的")
        self.assertEqual(1, int(after.payload.get("version", 1)))
        self.assertEqual(start.payload["missing_info"], after.payload["missing_info"])
        self.assertTrue(any("未匹配到任何缺失字段" in w for w in after.warnings), after.warnings)

    def test_empty_answer_refuses(self):
        start = self.skill.build(inp(archive("R-013"), self.lib))
        with self.assertRaises(SkillRefusal):
            self.skill.update_after_clarification(start, "   ")


class TestConditionCompareBuild(unittest.TestCase):
    def setUp(self):
        self.skill = ConditionCompareSkill()
        self.nine = {"model": "8B", "seq_len": "512", "batch": "32", "micro_batch": "4",
                     "precision": "bf16", "hardware": "4090", "dataset_version": "v1",
                     "stage": "训练", "framework": "torch"}

    def build(self, a, b):
        payload = SkillInput(raw_text="比较", context={"records": [a, b]})
        return self.skill.build(payload)

    def test_differing_dim_blocks_conflict(self):
        a = archive("R-001", conditions=dict(self.nine))
        b = archive("R-002", conditions={**self.nine, "seq_len": "2048"})
        out = self.build(a, b)
        self.assertEqual("条件不同", out.payload["verdict"])
        self.assertEqual(["seq_len"], out.payload["differing_dims"])
        self.assertEqual([], self.skill.validate(out))

    def test_missing_dim_is_inconclusive(self):
        a = archive("R-001", conditions={"seq_len": "512"})
        b = archive("R-002", conditions={"seq_len": "512"})
        out = self.build(a, b)
        self.assertEqual("条件不全", out.payload["verdict"])
        self.assertTrue(out.payload["missing_dims"])
        self.assertTrue(any("不得下任何方向性结论" in w for w in out.warnings))

    def test_real_conflict_needs_marker_and_full_conditions(self):
        a = archive("R-001", conditions=dict(self.nine), conclusions_conflict=True)
        b = archive("R-002", conditions=dict(self.nine))
        self.assertEqual("真冲突", self.build(a, b).payload["verdict"])

    def test_requires_two_records(self):
        with self.assertRaises(SkillRefusal):
            self.skill.build(SkillInput(raw_text="x", context={"records": [archive()]}))

    def test_validate_flags_bad_verdict(self):
        from rra.skills.base import SkillOutput
        bad = SkillOutput(payload={"verdict": "看起来还行", "differing_dims": [], "missing_dims": []})
        self.assertTrue(self.skill.validate(bad))


class TestInductionBuild(unittest.TestCase):
    def setUp(self):
        self.skill = InductionSkill()
        self.three = [archive("R-001"), archive("R-002"), archive("R-003")]

    def hyp(self, **over):
        base = {"blocker": "长序列训练显存不足", "supporting": ["R-001", "R-002", "R-003"],
                "consensus": "降低 micro-batch 可稳定显存", "unverified": "梯度累积能否补回等效 batch",
                "unlocks": "seq_len 2048 以上的配置", "min_action": "micro-batch=4 + 累积 8 步跑 200 step"}
        base.update(over)
        return base

    def test_valid_hypotheses_pass(self):
        out = self.skill.build(inp({"hypotheses": [self.hyp()]}, library(*self.three)))
        self.assertEqual(1, len(out.payload["hypotheses"]))
        self.assertEqual([], self.skill.validate(out))

    def test_gate_refuses_when_group_too_small(self):
        with self.assertRaises(SkillRefusal):
            self.skill.build(inp({"hypotheses": []}, library(*self.three[:2])))

    def test_refutation_record_does_not_count_towards_gate(self):
        refut = archive("R-015", attempt="对 R-001 的人工纠错")
        with self.assertRaises(SkillRefusal):
            self.skill.build(inp({"hypotheses": []}, library(*self.three[:2], refut)))

    def test_blocker_below_gate_is_rejected(self):
        bad = self.hyp(blocker="另一个阻塞点", supporting=["R-001"])
        with self.assertRaises(ValueError):
            self.skill.build(inp({"hypotheses": [bad]}, library(*self.three)))

    def test_supporting_id_outside_group_is_rejected(self):
        bad = self.hyp(supporting=["R-001", "R-002", "R-003", "R-014"])
        with self.assertRaises(ValueError):
            self.skill.build(inp({"hypotheses": [bad]}, library(*self.three)))

    def test_hypothesis_without_min_action_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.skill.build(inp({"hypotheses": [self.hyp(min_action="")]}, library(*self.three)))
        self.assertIn("min_action", str(ctx.exception))

    def test_reports_eligible_but_unproduced_group(self):
        out = self.skill.build(inp({"hypotheses": []}, library(*self.three)))
        self.assertTrue(any("已达门槛但未产出假设" in w for w in out.warnings), out.warnings)


class TestResurrectionBuild(unittest.TestCase):
    def setUp(self):
        self.skill = ResurrectionSkill()
        self.abandoned = archive("R-006", status="已放弃", blocker="单卡放不下 70B 的权重与优化器状态")
        self.lib = library(self.abandoned, archive("R-001"))

    def test_valid_unblock_passes(self):
        raw = archive("R-015",
                      resurrection={"unblocks": [{"record": "R-006", "basis": "R-015",
                                                  "quote": "显存仍不足，200 step 内 OOM 两次"}]})
        out = self.skill.build(inp(raw, self.lib))
        self.assertEqual("R-006", out.payload["resurrection"]["unblocks"][0]["record"])

    def test_target_must_be_an_abandoned_candidate(self):
        raw = archive("R-015",
                      resurrection={"unblocks": [{"record": "R-001", "basis": "R-015",
                                                  "quote": "显存仍不足，200 step 内 OOM 两次"}]})
        with self.assertRaises(ValueError):
            self.skill.build(inp(raw, self.lib))

    def test_basis_must_exist(self):
        raw = archive("R-015",
                      resurrection={"unblocks": [{"record": "R-006", "basis": "R-999",
                                                  "quote": "显存仍不足，200 step 内 OOM 两次"}]})
        with self.assertRaises(ValueError):
            self.skill.build(inp(raw, self.lib))

    def test_unverifiable_quote_is_rejected(self):
        """解除依据的原文必须在依据档案里找得到 —— 编一段像样的文字不算依据。"""
        raw = archive("R-015",
                      resurrection={"unblocks": [{"record": "R-006", "basis": "R-015",
                                                  "quote": "这一段话在依据档案里根本不存在"}]})
        with self.assertRaises(ValueError):
            self.skill.build(inp(raw, self.lib))

    def test_no_candidates_refuses(self):
        with self.assertRaises(SkillRefusal):
            self.skill.build(inp(archive("R-015"), library(archive("R-001"))))

    def test_no_unblock_is_allowed_but_warned(self):
        out = self.skill.build(inp(archive("R-015"), self.lib))
        self.assertTrue(any("未解除任何已放弃记录" in w for w in out.warnings), out.warnings)


class TestReviewer2Build(unittest.TestCase):
    def setUp(self):
        self.skill = Reviewer2Skill()
        self.lib = library(archive("R-004"), archive("R-008"))

    def test_grounded_challenge_is_kept(self):
        raw = {"challenges": [{"text": "这个方向已有多次记录，请说明条件差异。",
                               "evidence_ids": ["R-004", "R-008"]}]}
        out = self.skill.build(inp(raw, self.lib))
        self.assertEqual(1, len(out.payload["challenges"]))
        self.assertEqual([], self.skill.validate(out))

    def test_ungrounded_challenge_is_dropped(self):
        raw = {"challenges": [
            {"text": "有编号的", "evidence_ids": ["R-004"]},
            {"text": "没有编号的，听起来再对也不许进", "evidence_ids": []},
            {"text": "编号格式不对", "evidence_ids": ["R4"]},
        ]}
        out = self.skill.build(inp(raw, self.lib))
        self.assertEqual(1, len(out.payload["challenges"]))
        self.assertEqual(2, len(out.payload["dropped"]))
        self.assertTrue(any("已丢弃" in w for w in out.warnings), out.warnings)

    def test_all_ungrounded_refuses(self):
        raw = {"challenges": [{"text": "无出处", "evidence_ids": []}]}
        with self.assertRaises(SkillRefusal):
            self.skill.build(inp(raw, self.lib))

    def test_nonexistent_evidence_id_is_rejected(self):
        raw = {"challenges": [{"text": "引用不存在的档案", "evidence_ids": ["R-999"]}]}
        with self.assertRaises(ValueError):
            self.skill.build(inp(raw, self.lib))

    def test_is_grounded_rule(self):
        self.assertTrue(self.skill.is_grounded({"evidence_ids": ["R-004"]}))
        self.assertFalse(self.skill.is_grounded({"evidence_ids": []}))
        self.assertFalse(self.skill.is_grounded({"evidence_ids": ["R4"]}))
        self.assertFalse(self.skill.is_grounded({}))


class TestSkillsShareOneGate(unittest.TestCase):
    """六个技能的公共纪律：没有专家产出就拒绝，绝不自己编一个。"""

    def test_every_skill_refuses_without_expert_output(self):
        lib = library(archive("R-001"), archive("R-002"), archive("R-003"))
        payload = SkillInput(raw_text="一段记录", library=lib, context={})
        for skill in (ExtractSkill(), ReverseLookupSkill(), InductionSkill(),
                      ResurrectionSkill(), Reviewer2Skill()):
            with self.assertRaises(SkillRefusal, msg=skill.name):
                skill.build(payload)

    def test_build_is_still_abstract_in_base(self):
        """base.build 保持抽象是有意的：默认实现会让「忘了写门禁」静默通过。"""
        from rra.skills.base import SkillBase
        with self.assertRaises(NotImplementedError):
            SkillBase().build(SkillInput(raw_text="x"))


if __name__ == "__main__":
    unittest.main()
