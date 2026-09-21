"""技能 1：杂乱记录 → 结构化档案。必须区分「观察到的」与「推测的」。

分工（见 base.py 模块文档）：**抽取本身是语义判断，由专家完成**；
本文件只负责把关——专家交回的档案必须合法、干净、且关键字段不缺。
缺「观察 / 阻塞点 / 适用边界」时**拒绝建档**，请用户补原文，而不是替它编。
"""

from .base import (
    SkillBase, SkillInput, SkillOutput, SkillRefusal, expert_output, first_missing,
    normalize_archive,
)

# 契约里的必填项由校验器负责；这三个字段额外单独检，因为它们对应的是
# 「这条记录还不成立」而不是「字段格式错了」——前者该拒绝，后者该报违规。
_REQUIRED_FOR_A_RECORD = ("observation", "blocker", "boundary")


class ExtractSkill(SkillBase):
    name = "extract"
    prompt_path = "prompts/extract.md"

    def build(self, payload: SkillInput) -> SkillOutput:
        """把关专家交回的档案：契约校验 + 规范化 + 缺关键字段即拒绝。"""
        raw = expert_output(payload)
        if not isinstance(raw, dict):
            raise ValueError("抽取结果不是对象：%r" % type(raw).__name__)

        # 先判「还不成立」：这类缺口要给用户可执行的补法，而不是一串 schema 报错。
        missing = first_missing(raw, _REQUIRED_FOR_A_RECORD)
        if missing:
            raise SkillRefusal(
                "记录还不足以建档：缺少 %s，请补充原文" % "、".join(missing),
                missing=missing)

        archive = normalize_archive(raw)
        violations = self.validator.validate_archive(archive)
        if violations:
            raise ValueError("抽取结果未通过契约校验：" + "；".join(str(v) for v in violations))

        context = payload.context or {}
        warnings = [str(w) for w in (context.get("warnings") or [])]
        # 归因类型是假设时留一条提示：它不是结论，后续引用时要保持这个口径。
        attribution = archive.get("attribution") or {}
        if attribution.get("type") == "assumption":
            warnings.append("归因类型为 assumption：原文未给出原因，引用时必须保留「假设」口径。")
        if not archive.get("conditions"):
            warnings.append("本次未提取到结构化条件：条件对比矩阵将显示「未提供」，不做推测。")

        return SkillOutput(
            payload=archive,
            narrative=str(context.get("narrative", "")),
            warnings=warnings,
        )
