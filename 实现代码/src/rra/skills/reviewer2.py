"""技能 6（附录 D.1 的 D5）：审稿人 2 号。

立项检查从「给你看历史」升级为「主动质询」；每条质疑必须带证据编号。
"""

from .base import SkillBase, SkillInput, SkillOutput


class Reviewer2Skill(SkillBase):
    name = "reviewer2"
    prompt_path = "prompts/reviewer2.md"

    def build(self, payload: SkillInput) -> SkillOutput:
        raise NotImplementedError

    def is_grounded(self, challenge: dict) -> bool:
        """没有证据编号的质疑一律视为不合格，必须丢弃。

        规则写死：列表非空且每一项都必须匹配 R-###；缺编号的质询不进输出。
        """
        import re
        pattern = re.compile(r"^R-[0-9]{3,}$")
        ids = (challenge or {}).get("evidence_ids") or []
        return bool(ids) and all(isinstance(i, str) and pattern.match(i) for i in ids)
