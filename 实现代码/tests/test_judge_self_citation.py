"""判分器不得允许「自引用刷分」（2026-09-22 后端审查 P2-6 的回归）。

刷分路径：把 `evidence_refs[].record` 写成**本档案自己的 id**、quote 抄自己 observation 的片段，
再在 `claimed_hits` 里填一个库里存在的编号 ——
引用校验把 payload 自己也放进了临时库，于是自引用"可复核"、citation_ok=True，
四个判据全绿，passed=True，而这条档案其实一份外部证据都没有。

要求：判分时剔除指向 payload 自身编号的引用；一条引用都不剩 → citation_ok=False。
指向真实库内档案的引用必须照旧通过（别把铁律变成"引用一律不算"）。
"""

import unittest

from rra.eval.cases import Case, CaseKind, CaseRegistry
from rra.eval.runner import CaseOutput, EvalRunner, Judge

TARGET = {
    "id": "R-001", "attempt": "直接用 batch=32 跑 seq_len=2048 的微调",
    "expectation": "一晚跑完", "observation": "第 40 step 触发 CUDA OOM",
    "blocker": "长序列训练显存不足",
    "attribution": {"text": "怀疑激活值超 24G", "type": "assumption"},
    "boundary": "单卡 24G", "confidence": "low", "status": "进行中",
    "provenance": {"author": "模拟", "date": "2026-07-14", "source": "模拟"},
}
OWN_QUOTE = "第 40 step 触发 CUDA OOM"


def case(no, kind=CaseKind.SAME_ISSUE_DIFFERENT_WORDING):
    return Case(no=no, kind=kind, summary="t", expectation="e", blind=False)


def self_referential(id_="R-900", extra_refs=None, attribution_type="assumption"):
    """一条把自己的 observation 抄成"证据"的档案。"""
    payload = dict(TARGET)
    payload["id"] = id_
    payload["attribution"] = {"text": TARGET["attribution"]["text"], "type": attribution_type}
    payload["evidence_refs"] = [{"record": id_, "quote": OWN_QUOTE}] + list(extra_refs or [])
    return CaseOutput(raw=payload, claimed_hits=("R-001",), note="专家输出")


class TestSelfReferenceIsNotEvidence(unittest.TestCase):
    def setUp(self):
        self.judge = Judge()

    def test_self_reference_alone_does_not_count_as_citation(self):
        r = self.judge.judge(case(1), self_referential(), [TARGET])
        self.assertFalse(r.citation_ok, "自引用被当成了证据：%s" % r.note)
        self.assertFalse(r.passed, r.note)
        self.assertIn("自身", r.note)

    def test_self_reference_boost_no_longer_raises_pass_rate(self):
        """端到端：这条档案刷不出分，通过率必须还是 0。"""
        reg = CaseRegistry([case(1)])
        out = self_referential()
        report = EvalRunner(reg, executor=lambda c: out, judge=Judge()).run(reg.open_cases(), [TARGET])
        self.assertEqual(0.0, report.pass_rate())
        self.assertFalse(any(x.passed for x in report.results))

    def test_observed_self_reference_is_still_unfounded(self):
        """自称"已观察"却只有自引用 —— 仍然是无依据归因。"""
        r = self.judge.judge(case(1), self_referential(attribution_type="observed"), [TARGET])
        self.assertFalse(r.citation_ok, r.note)
        self.assertTrue(r.fabricated_attribution, r.note)
        self.assertFalse(r.passed)

    def test_real_library_reference_still_passes(self):
        payload = dict(TARGET)
        payload["id"] = "R-901"
        payload["evidence_refs"] = [{"record": "R-001", "quote": OWN_QUOTE}]
        r = self.judge.judge(case(1), CaseOutput(raw=payload, claimed_hits=("R-001",)), [TARGET])
        self.assertTrue(r.citation_ok, r.note)
        self.assertTrue(r.hit, r.note)
        self.assertTrue(r.passed, r.note)

    def test_other_refs_survive_after_dropping_the_self_one(self):
        """自引用被剔掉，但真实引用还在 —— 不能因为有一条自引用就把整条判死。"""
        extra = [{"record": "R-001", "quote": OWN_QUOTE}]
        r = self.judge.judge(case(1), self_referential(extra_refs=extra), [TARGET])
        self.assertTrue(r.citation_ok, r.note)
        self.assertTrue(r.passed, r.note)


if __name__ == "__main__":
    unittest.main()
