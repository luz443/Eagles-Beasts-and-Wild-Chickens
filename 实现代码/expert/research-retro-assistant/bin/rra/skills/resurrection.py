"""技能 5（附录 D.1 的 S2）：死实验复活。

新记录入库时反向检查：它是否解除了某条已放弃记录的阻塞点。
"""

from .base import SkillBase, SkillInput, SkillOutput


class ResurrectionSkill(SkillBase):
    name = "resurrection"
    prompt_path = "prompts/resurrection.md"

    def build(self, payload: SkillInput) -> SkillOutput:
        raise NotImplementedError

    def candidates(self, library: dict) -> list[dict]:
        """先筛出「已放弃且阻塞点明确」的记录，再交给专家判断是否被解除。

        这是纯筛选：不做任何语义推断，也不因「放弃过」就给方向下判决。
        """
        return [r for r in (library or {}).get("records", [])
                if r.get("status") == "已放弃" and str(r.get("blocker", "")).strip()]
