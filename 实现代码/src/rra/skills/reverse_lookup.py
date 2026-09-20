"""技能 2：入库即反查。输出候选证据 + 缺失信息；澄清后更新结论强度。"""

from .base import SkillBase, SkillInput, SkillOutput


class ReverseLookupSkill(SkillBase):
    name = "reverse_lookup"
    prompt_path = "prompts/reverse_lookup.md"

    def build(self, payload: SkillInput) -> SkillOutput:
        raise NotImplementedError

    def update_after_clarification(self, output: SkillOutput, answer: str) -> SkillOutput:
        """人在补充信息之后重算。最终确认的那一版才是入库版本。

        需要语义重判（结论强度、证据引用是否更新），属平台专家侧职责，本方法只做调用编排。
        """
        raise NotImplementedError

    def apply_clarification_facts(self, output: SkillOutput, resolved_keys: list[str]) -> SkillOutput:
        """确定性记账：把已澄清的字段从 missing_info 移除，并把档案版本 +1。

        版本递增是刻意的：入库版本与澄清前那一版必须可区分
        （对应设计方案 3.2 的「最终确认的那一版才是入库版本」）。
        """
        payload = dict(output.payload)
        missing = [m for m in payload.get("missing_info", []) if m not in set(resolved_keys)]
        payload["missing_info"] = missing
        payload["version"] = int(payload.get("version", 1)) + 1
        warnings = list(output.warnings) + [
            "已澄清字段：%s；文档版本递增至 v%d" % ("、".join(resolved_keys), payload["version"])]
        return SkillOutput(payload=payload, narrative=output.narrative, warnings=warnings)
