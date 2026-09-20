"""技能 4：归纳孵化。同一阻塞点多条记录 → 待验证假设清单（H 编号）。"""

from ..library.refutation import exclude_refutations
from .base import SkillBase, SkillInput, SkillOutput


class InductionSkill(SkillBase):
    name = "induction"
    prompt_path = "prompts/induction.md"

    MIN_SUPPORTING = 3

    def build(self, payload: SkillInput) -> SkillOutput:
        """支撑记录不足 MIN_SUPPORTING 时必须拒绝，不得硬产出假设。"""
        raise NotImplementedError

    def eligible_groups(self, records: list[dict]) -> dict[str, list[dict]]:
        """按阻塞点分组，只保留达到 MIN_SUPPORTING 条的分组。

        未达门槛的分组不出现——「证据不足就不产出假设」这条规则在这里落地。

        **先剔除人工纠错记录**（与网页端 `web/js/views/incubation.js` 同一口径）：
        纠错不是一次尝试，否则 2 条真实记录 + 1 条纠错就能凑满 3 条、凭空产出假设。
        """
        groups: dict[str, list[dict]] = {}
        for r in exclude_refutations(records):
            groups.setdefault(r.get("blocker", ""), []).append(r)
        return {k: v for k, v in groups.items()
                if k and len(v) >= self.MIN_SUPPORTING}
