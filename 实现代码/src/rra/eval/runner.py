"""跑批与结果落盘。**判据由代码算，执行器只能交回原始输出。**

2026-09-19 外部代码审查 P1：原实现里执行器直接返回 `CaseResult(hit=True, citation_ok=True, ...)`，
跑批器照单全收 —— 只要把布尔值设成 True，用例就会"通过"，指标可以凭空造出来。
现在的分工是：

    执行器（可能是真人、专家、或占位桩）→ 只交回 `CaseOutput`：原始输出 + 它声称命中的档案编号；
    判分器 `Judge`                        → 拿原始输出与库，自己算 契约 / 引用 / 无依据归因 / 命中。

命中判据无法凭空推断，所以按 **显式的按类型规则表**（`HIT_EXPECTATION`）决定：
规则表里写 `None` 的类型表示"判据是语义性的，当前不计通过"，宁可标成待人工，也不假装判过。
新增 CaseKind 必须同时在规则表里给出决定，否则
`tests/test_runner.py::TestJudge::test_every_case_kind_has_an_explicit_decision` 会失败。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..contracts.validator import Validator
from .cases import Case, CaseKind, CaseRegistry

# 每种用例类型对"是否应当命中库里已有记录"的显式决定：
#   True  = 应命中（没有命中就是能力问题，不计通过）
#   False = 不应命中（"库内无相关经验"类，给出编号即为编造）
#   None  = 判据是语义性的（低置信度、是否产出假设、质询是否带证据…），当前不计通过，等人工/语义判定
HIT_EXPECTATION: dict[CaseKind, bool | None] = {
    CaseKind.SAME_ISSUE_DIFFERENT_WORDING: True,
    CaseKind.SAME_KEYWORD_DIFFERENT_CONDITION: True,
    CaseKind.LOOKS_CONFLICTING: True,
    CaseKind.REAL_CONFLICT: True,
    CaseKind.CLOSURE: True,
    CaseKind.NO_PRIOR_EXPERIENCE: False,
    CaseKind.HALLUCINATION_BAIT: False,
    CaseKind.INSUFFICIENT_EVIDENCE: None,
    CaseKind.INCUBATION: None,
    CaseKind.CONTRACT: None,
    CaseKind.RESURRECTION: None,
    CaseKind.REVIEWER2: None,
}


@dataclass
class CaseResult:
    """单条用例结果。四个判据与 docs/plans 的口径一致。"""

    no: int
    hit: bool = False
    citation_ok: bool = False
    fabricated_attribution: bool = False
    contract_ok: bool = False
    note: str = ""

    @property
    def passed(self) -> bool:
        return (self.hit and self.citation_ok
                and not self.fabricated_attribution and self.contract_ok)


@dataclass
class CaseOutput:
    """执行器唯一被允许交回的东西：原始输出，以及它声称命中的档案编号。

    不许交回布尔判据 —— 那是判分器的活。
    """

    raw: object = None
    claimed_hits: tuple[str, ...] = ()
    note: str = ""


@dataclass
class EvalReport:
    """一次跑批的汇总。指标从这里算。"""

    prompt_version: str = ""
    results: list[CaseResult] = field(default_factory=list)

    def citation_accuracy(self) -> float:
        if not self.results:
            return 0.0
        ok = sum(1 for r in self.results if r.citation_ok)
        return ok / len(self.results)

    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    def to_markdown_table(self) -> str:
        """生成记录表（7.3 模板），直接贴进 PPT 的实测结果页。"""
        lines = [
            "# 评测记录表（提示词版本：%s）" % self.prompt_version, "",
            "| 用例 | 是否命中 | 引用编号正确 | 无依据归因 | 契约合法 | 结论 | 备注 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for r in self.results:
            lines.append("| %d | %s | %s | %s | %s | %s | %s |" % (
                r.no, "是" if r.hit else "否",
                "是" if r.citation_ok else "否",
                "否" if not r.fabricated_attribution else "是",
                "是" if r.contract_ok else "否",
                "通过" if r.passed else "失败",
                r.note.replace("|", "／")))
        lines.append("")
        lines.append("引用正确率：%.1f%%　通过率：%.1f%%" % (
            self.citation_accuracy() * 100, self.pass_rate() * 100))
        return "\n".join(lines)

    def save(self, path: Path) -> None:
        data = {
            "prompt_version": self.prompt_version,
            "citation_accuracy": self.citation_accuracy(),
            "pass_rate": self.pass_rate(),
            "results": [
                {"no": r.no, "hit": r.hit, "citation_ok": r.citation_ok,
                 "fabricated_attribution": r.fabricated_attribution,
                 "contract_ok": r.contract_ok, "passed": r.passed, "note": r.note}
                for r in self.results],
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json_dumps(data), encoding="utf-8")


def json_dumps(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


class Judge:
    """从「原始输出 + 库」算出四个判据。全程确定性，不采信执行器的自报成绩。"""

    def __init__(self, validator: Validator | None = None) -> None:
        self.validator = validator or Validator()

    def judge(self, case: Case, output: object,
              records: list[dict] | None = None) -> CaseResult:
        records = list(records or [])
        if not isinstance(output, CaseOutput):
            output = CaseOutput(raw=output)
        result = CaseResult(no=case.no)
        notes: list[str] = [output.note] if output.note else []

        payload = output.raw if isinstance(output.raw, dict) else None
        if payload is None:
            notes.append("执行器未返回可解析的档案对象")
            result.note = "；".join(notes)
            return result

        # 1) 契约：输出本身是否合法（字段、枚举、结构）
        contract_violations = self.validator.validate_archive(payload)
        result.contract_ok = not contract_violations
        if contract_violations:
            notes.append("契约违规 %d 处（%s）"
                         % (len(contract_violations), contract_violations[0].path))

        # 2) 引用：必须真有引用，且每条引文都能在库里对上（引用编号 + 原文片段）
        refs = payload.get("evidence_refs") if isinstance(payload.get("evidence_refs"), list) else []
        lib = {"version": "0.1.0", "generated_at": "", "records": records + [payload]}
        prefix = "records[%d].evidence_refs" % len(records)
        ref_violations = [v for v in self.validator.validate_library(lib)
                          if v.path.startswith(prefix)]
        result.citation_ok = bool(refs) and not ref_violations
        if not refs:
            notes.append("输出没有任何证据引用")
        elif ref_violations:
            notes.append("引用不可复核 %d 处（%s）" % (len(ref_violations), ref_violations[0].path))

        # 3) 无依据归因：引用对不上，或声称"已观察"却拿不出可核验引用
        attribution = payload.get("attribution") if isinstance(payload.get("attribution"), dict) else {}
        observed_without_evidence = (attribution.get("type") == "observed"
                                     and not result.citation_ok)
        result.fabricated_attribution = bool(ref_violations) or observed_without_evidence
        if observed_without_evidence:
            notes.append("归因写成 observed 却无可核验引用")

        # 4) 命中：按显式规则表，而不是让执行器自己说
        expect = HIT_EXPECTATION.get(case.kind)
        claimed = tuple(output.claimed_hits or ())
        known = {str(r.get("id", "")) for r in records if isinstance(r, dict)}
        unknown = [rid for rid in claimed if rid not in known]
        if expect is None:
            notes.append("该类型用例的命中判据是语义性的，当前不计通过（待人工/语义判定）")
        elif expect is True:
            result.hit = bool(claimed) and not unknown
            if not claimed:
                notes.append("期望命中库内记录，但执行器未给出命中编号")
            elif unknown:
                notes.append("声称命中的编号在库里不存在：%s" % "、".join(unknown))
        else:  # expect is False
            result.hit = not claimed
            if claimed:
                notes.append("该用例期望「库内无相关记录」，却给出了命中编号：%s"
                             % "、".join(claimed))

        result.note = "；".join(notes)
        return result


class EvalRunner:
    """跑批器。执行器只交回原始输出；判据一律由 `Judge` 计算。"""

    def __init__(self, registry: CaseRegistry,
                 executor: Callable[[Case], CaseOutput],
                 judge: Judge | None = None) -> None:
        self.registry = registry
        self.executor = executor
        self.judge = judge or Judge()

    def run(self, cases: list[Case], records: list[dict] | None = None) -> EvalReport:
        report = EvalReport()
        for case in cases:
            output = self.executor(case)
            report.results.append(self.judge.judge(case, output, records))
        return report
