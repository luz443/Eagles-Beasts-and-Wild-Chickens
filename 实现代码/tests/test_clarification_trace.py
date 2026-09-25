"""P2-10：澄清答复必须留痕。

红的最小复现：澄清之后答复原文只出现在返回的 warnings 里，档案里查不到——
日后没人能复核「当时补的是什么」。修法是给档案加 `clarifications` 字段
（契约变更：schema + Python 校验器 + 网页端 ALLOWED_TOP），把答复持久化进去。

跨端一致性由 `web/tests/contract-parity.mjs` 盯着：正例夹具
`contracts/fixtures/valid_clarifications.json` 必须两端都判为「无违规」，反例夹具
`contracts/fixtures/invalid_clarifications.json`（`at` 为空）必须两端都报出同一违规路径
`clarifications[0].at`——为此 JS 侧补齐了 `checkClarifications`，与 Python 端逐条对齐。
"""

import json
import unittest
from pathlib import Path

from rra.contracts.models import Archive
from rra.contracts.validator import Validator
from rra.skills.base import SkillOutput
from rra.skills.reverse_lookup import ReverseLookupSkill

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "fixtures" / "valid_clarifications.json"


def archive(**over):
    """一条通过契约的档案（含一个可被澄清的 missing_info）。"""
    data = {
        "id": "R-013",
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
    data.update(over)
    return data


ANSWER = "micro-batch 实际生效值是 2"


class TestClarificationTrace(unittest.TestCase):
    def setUp(self):
        self.skill = ReverseLookupSkill()

    def clarified(self):
        start = SkillOutput(payload=archive(), narrative="")
        return self.skill.update_after_clarification(start, ANSWER)

    def test_answer_is_persisted_into_archive(self):
        after = self.clarified()
        log = after.payload.get("clarifications")
        self.assertTrue(log, "澄清答复没有进档案：%s" % after.payload)
        self.assertEqual(["micro-batch 实际生效值"], [c["key"] for c in log])
        self.assertIn(ANSWER, [c["answer"] for c in log])
        for item in log:
            self.assertTrue(item["at"], "留痕缺时间戳：%s" % item)
        self.assertEqual([], after.payload["missing_info"])
        self.assertEqual(2, after.payload["version"])

    def test_persisted_answer_passes_contract(self):
        self.assertEqual([], Validator().validate_archive(self.clarified().payload))

    def test_apply_clarification_facts_also_records_answer(self):
        got = self.skill.apply_clarification_facts(
            SkillOutput(payload=archive(), narrative=""), ["micro-batch 实际生效值"],
            answer=ANSWER)
        self.assertEqual(ANSWER, got.payload["clarifications"][0]["answer"])

    def test_repeated_clarifications_append(self):
        """多轮澄清逐条追加，不覆盖上一轮留下的答复。"""
        first = self.skill.update_after_clarification(
            SkillOutput(payload=archive(missing_info=["micro-batch 实际生效值", "精度"]),
                        narrative=""), ANSWER)
        self.assertEqual(1, len(first.payload["clarifications"]))
        second = self.skill.update_after_clarification(first, "精度是 bf16")
        self.assertEqual(2, len(second.payload["clarifications"]))
        self.assertEqual(["micro-batch 实际生效值", "精度"],
                         [c["key"] for c in second.payload["clarifications"]])
        self.assertEqual(3, second.payload["version"])
        self.assertEqual([], second.payload["missing_info"])

    def test_unmatched_answer_leaves_no_trace(self):
        start = SkillOutput(payload=archive(), narrative="")
        after = self.skill.update_after_clarification(start, "嗯嗯好的")
        self.assertNotIn("clarifications", after.payload)


class TestClarificationsContract(unittest.TestCase):
    def setUp(self):
        self.v = Validator()

    def paths(self, raw):
        return [x.path for x in self.v.validate_archive(raw)]

    def test_must_be_a_list(self):
        self.assertIn("clarifications", self.paths(archive(clarifications="不是列表")))

    def test_item_must_be_object(self):
        self.assertIn("clarifications[0]", self.paths(archive(clarifications=["x"])))

    def test_item_needs_all_three_keys(self):
        self.assertIn("clarifications[0].at",
                      self.paths(archive(clarifications=[{"key": "k", "answer": "a"}])))

    def test_values_must_be_non_empty_strings(self):
        got = self.paths(archive(clarifications=[{"key": "", "answer": 3, "at": "  "}]))
        for expected in ("clarifications[0].key", "clarifications[0].answer",
                         "clarifications[0].at"):
            self.assertIn(expected, got)

    def test_valid_fixture_passes_and_survives_roundtrip(self):
        """正例夹具两端都要放行；且经模型往返后 clarifications 不丢。"""
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual([], self.v.validate_archive(raw))
        self.assertEqual(raw, Archive.from_dict(raw).to_dict())


if __name__ == "__main__":
    unittest.main()
