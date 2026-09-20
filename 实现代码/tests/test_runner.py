"""跑批器与记录表：执行器只能交回原始输出，判据由判分器算。

2026-09-19 外部代码审查 P1：原接口让执行器直接返回 `CaseResult(hit=True, citation_ok=True, ...)`，
跑批器照单全收 —— 布尔值一设，用例就"通过"。现在执行器只能给 `CaseOutput`，
契约 / 引用 / 无依据归因 / 命中 四个判据全部由 `Judge` 从原始输出与库推导。
"""

import unittest

from rra.eval.cases import Case, CaseKind, CaseRegistry
from rra.eval.runner import CaseOutput, CaseResult, EvalReport, EvalRunner, Judge

TARGET = {
    "id": "R-001", "attempt": "直接用 batch=32 跑 seq_len=2048 的微调",
    "expectation": "一晚跑完", "observation": "第 40 step 触发 CUDA OOM",
    "blocker": "长序列训练显存不足",
    "attribution": {"text": "怀疑激活值超 24G", "type": "assumption"},
    "boundary": "单卡 24G", "confidence": "low", "status": "进行中",
    "provenance": {"author": "模拟", "date": "2026-07-14", "source": "模拟"},
}


def output_with_ref(quote="第 40 step 触发 CUDA OOM"):
    payload = dict(TARGET)
    payload["id"] = "R-900"
    payload["evidence_refs"] = [{"record": "R-001", "quote": quote}]
    return CaseOutput(raw=payload, claimed_hits=("R-001",), note="专家输出")


def case(no, kind=CaseKind.SAME_ISSUE_DIFFERENT_WORDING):
    return Case(no=no, kind=kind, summary="t", expectation="e", blind=False)


class TestJudge(unittest.TestCase):
    def setUp(self):
        self.judge = Judge()

    def test_executor_booleans_no_longer_count(self):
        """核心回归：执行器交回"全是 True 的结果对象"，一律判失败。"""
        claimed = CaseResult(no=1, hit=True, citation_ok=True, contract_ok=True)
        r = self.judge.judge(case(1), claimed, [TARGET])
        self.assertFalse(r.passed)
        self.assertFalse(r.contract_ok)

    def test_good_output_passes_when_kind_expects_hit(self):
        r = self.judge.judge(case(1), output_with_ref(), [TARGET])
        self.assertTrue(r.contract_ok, r.note)
        self.assertTrue(r.citation_ok, r.note)
        self.assertTrue(r.hit, r.note)
        self.assertFalse(r.fabricated_attribution)
        self.assertTrue(r.passed, r.note)

    def test_fabricated_quote_fails_citation(self):
        r = self.judge.judge(case(1), output_with_ref(quote="这是虚构证据够长了"), [TARGET])
        self.assertFalse(r.citation_ok)
        self.assertTrue(r.fabricated_attribution)
        self.assertFalse(r.passed)

    def test_observed_without_evidence_is_fabricated(self):
        payload = dict(TARGET)
        payload["id"] = "R-901"
        payload["attribution"] = {"text": "因为显存不够", "type": "observed"}   # 声称已观察
        r = self.judge.judge(case(1), CaseOutput(raw=payload, claimed_hits=("R-001",)), [TARGET])
        self.assertTrue(r.fabricated_attribution)
        self.assertFalse(r.passed)

    def test_claimed_hit_must_exist_in_library(self):
        payload = dict(TARGET)
        payload["id"] = "R-902"
        payload["evidence_refs"] = [{"record": "R-001", "quote": "第 40 step 触发 CUDA OOM"}]
        r = self.judge.judge(case(1), CaseOutput(raw=payload, claimed_hits=("R-777",)), [TARGET])
        self.assertFalse(r.hit)
        self.assertIn("不存在", r.note)

    def test_kind_expecting_no_hit_rejects_claimed_ids(self):
        r = self.judge.judge(case(15, CaseKind.NO_PRIOR_EXPERIENCE),
                             CaseOutput(raw=dict(TARGET, id="R-903",
                                                 evidence_refs=[{"record": "R-001",
                                                                 "quote": "第 40 step 触发 CUDA OOM"}]),
                                        claimed_hits=("R-001",)), [TARGET])
        self.assertFalse(r.hit)
        self.assertIn("无相关记录", r.note)

    def test_semantic_kind_is_not_counted_as_pass(self):
        r = self.judge.judge(case(21, CaseKind.INCUBATION), output_with_ref(), [TARGET])
        self.assertFalse(r.hit)
        self.assertIn("语义", r.note)

    def test_no_output_at_all_is_failure(self):
        r = self.judge.judge(case(1), CaseOutput(raw=None, note="占位：未接平台专家"), [TARGET])
        self.assertFalse(r.passed)
        self.assertIn("占位", r.note)

    def test_every_case_kind_has_an_explicit_decision(self):
        """新增 CaseKind 必须同时在规则表里给出决定，否则这条会失败。"""
        from rra.eval.runner import HIT_EXPECTATION
        missing = [k for k in CaseKind if k not in HIT_EXPECTATION]
        self.assertEqual(missing, [], "未决定命中期望的用例类型：%s" % missing)


class TestRunnerAndReport(unittest.TestCase):
    def test_runner_collects_judged_results(self):
        reg = CaseRegistry([case(1), case(2)])
        runner = EvalRunner(reg, executor=lambda c: output_with_ref(), judge=Judge())
        report = runner.run(reg.open_cases(), [TARGET])
        self.assertEqual(2, len(report.results))
        self.assertTrue(all(r.passed for r in report.results), [r.note for r in report.results])
        self.assertAlmostEqual(1.0, report.pass_rate())

    def test_placeholder_executor_yields_zero_pass_rate(self):
        """占位执行器交回"没有输出" → 通过率必须是 0，指标不可能被自造。"""
        reg = CaseRegistry([case(1), case(2)])
        runner = EvalRunner(reg, executor=lambda c: CaseOutput(raw=None, note="占位"), judge=Judge())
        report = runner.run(reg.open_cases(), [TARGET])
        self.assertEqual(0.0, report.pass_rate())

    def test_passed_requires_all_criteria(self):
        ok = CaseResult(no=1, hit=True, citation_ok=True, contract_ok=True)
        bad = CaseResult(no=2, hit=True, citation_ok=False, contract_ok=True)
        self.assertTrue(ok.passed)
        self.assertFalse(bad.passed)

    def test_citation_accuracy(self):
        r = EvalReport(prompt_version="v0.1", results=[
            CaseResult(no=1, hit=True, citation_ok=True, contract_ok=True),
            CaseResult(no=2, hit=True, citation_ok=True, contract_ok=True),
            CaseResult(no=3, hit=True, citation_ok=False, contract_ok=True),
        ])
        self.assertAlmostEqual(2 / 3, r.citation_accuracy())

    def test_markdown_table_has_header_and_rows(self):
        r = EvalReport(prompt_version="v0.1", results=[
            CaseResult(no=1, hit=True, citation_ok=True, contract_ok=True, note="x"),
        ])
        md = r.to_markdown_table()
        self.assertIn("| 用例 |", md)
        self.assertIn("| 1 |", md)
        self.assertIn("备注", md)


if __name__ == "__main__":
    unittest.main()
