"""技能 1：杂乱记录 → 结构化档案。必须区分「观察到的」与「推测的」。"""

from .base import SkillBase, SkillInput, SkillOutput


class ExtractSkill(SkillBase):
    name = "extract"
    prompt_path = "prompts/extract.md"

    def build(self, payload: SkillInput) -> SkillOutput:
        raise NotImplementedError
