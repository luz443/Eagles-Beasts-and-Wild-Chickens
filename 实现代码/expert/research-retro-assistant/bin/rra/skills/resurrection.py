"""技能 5（附录 D.1 的 S2）：死实验复活。

新记录入库时反向检查：它是否解除了某条已放弃记录的阻塞点。

分工（见 base.py 模块文档）：**「有没有被解除」是语义判断，由专家完成**；
本文件把住三条确定性规则：
- 被解除的必须是「已放弃且阻塞点非空」的记录（候选规则与网页端同口径）；
- 每条解除结论必须带可复核的解除依据（编号 + 原文片段）；
- 「它被放弃过」不构成任何判决——本层不允许出现方向性结论。
"""

from .base import (
    SkillBase, SkillInput, SkillOutput, SkillRefusal, expert_output, normalize_archive,
)

# 候选规则的唯一真源：只有「已放弃」且阻塞点非空的记录才可能被复活。
# 网页侧对应实现见 web/js/util/resurrection.js（RESURRECTION_STATUS）；
# 两端字面量各由一个测试盯着（tests/test_resurrection_filter.py 与
# web/tests/resurrection-rule-parity.mjs）——改一端就会响。
CANDIDATE_STATUS = "已放弃"


class ResurrectionSkill(SkillBase):
    name = "resurrection"
    prompt_path = "prompts/resurrection.md"

    def build(self, payload: SkillInput) -> SkillOutput:
        """把关专家交回的解除结论：依据必须真实存在、引文必须可复核。"""
        library = payload.library or {}
        if not library.get("records"):
            raise SkillRefusal("没有库文件就无法做反向检查", missing=["library"])
        candidates = self.candidates(library)
        if not candidates:
            raise SkillRefusal(
                "库内没有「已放弃且阻塞点非空」的记录，无从判断是否被解除",
                missing=["已放弃且阻塞点明确的记录"])

        archive = normalize_archive(expert_output(payload))
        basis_ids = {str(r.get("id", "")) for r in library.get("records", [])
                     if isinstance(r, dict) and r.get("id")}
        # 解除依据可以就是**本条新记录自己**（它带来的观察正是解除理由），
        # 所以把自身的编号也算作合法依据；此时它还没进库。
        if archive.get("id"):
            basis_ids.add(str(archive["id"]))
        candidate_ids = {str(r.get("id")) for r in candidates}

        unblocks = ((archive.get("resurrection") or {}).get("unblocks")) or []
        for i, item in enumerate(unblocks):
            if not isinstance(item, dict):
                raise ValueError("resurrection.unblocks[%d] 不是对象" % i)
            record = str(item.get("record", ""))
            basis = str(item.get("basis", ""))
            if record not in candidate_ids:
                raise ValueError(
                    "resurrection.unblocks[%d].record（%s）不是「已放弃且阻塞点非空」的候选"
                    % (i, record))
            if basis not in basis_ids:
                raise ValueError("resurrection.unblocks[%d].basis 指向库内不存在的档案：%s"
                                 % (i, basis))

        warnings = []
        if not unblocks:
            warnings.append("本次记录未解除任何已放弃记录的阻塞点（不得为有输出而硬凑）。")

        # 契约与「引文可复核」交给整库校验：把新档案并进库再校验一次，
        # 只挑与解除依据相关的违规——已存在的历史问题不由本技能负责。
        merged = {
            "version": str(library.get("version", "1")),
            "records": [r for r in library.get("records", [])
                        if isinstance(r, dict) and str(r.get("id")) != str(archive.get("id"))]
                       + [archive],
        }
        stray = [str(v) for v in self.validator.validate_library(merged)
                 if "resurrection" in v.path]
        if stray:
            raise ValueError("解除依据未通过校验：" + "；".join(stray))

        return SkillOutput(
            payload=archive,
            narrative=str((payload.context or {}).get("narrative", "")),
            warnings=warnings + ["部分解除必须写明「仍未解除的部分」——不得当作完全解除。"],
        )

    def candidates(self, library: dict) -> list[dict]:
        """先筛出「已放弃且阻塞点明确」的记录，再交给专家判断是否被解除。

        这是纯筛选：不做任何语义推断，也不因「放弃过」就给方向下判决。
        """
        return [r for r in (library or {}).get("records", [])
                if r.get("status") == CANDIDATE_STATUS and str(r.get("blocker", "")).strip()]
