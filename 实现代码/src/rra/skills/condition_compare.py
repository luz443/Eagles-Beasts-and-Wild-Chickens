"""技能 3：条件比较。任一维度不同即不得判为冲突。"""

from .base import SkillBase, SkillInput, SkillOutput


def _known_conditions(record: dict) -> dict[str, str]:
    """比较时只采用去除首尾空白后仍有内容的字符串条件。"""
    return {dim: value.strip() for dim, value in (record.get("conditions") or {}).items()
            if isinstance(value, str) and value.strip()}


class ConditionCompareSkill(SkillBase):
    name = "condition_compare"
    prompt_path = "prompts/condition_compare.md"

    DIM_ORDER = [
        "model", "seq_len", "batch", "micro_batch", "precision",
        "hardware", "dataset_version", "stage", "framework",
    ]

    def build(self, payload: SkillInput) -> SkillOutput:
        raise NotImplementedError

    def differing_dims(self, a: dict, b: dict) -> list[str]:
        """两侧都给出了取值、且取值不同的维度（缺一侧不算差异——缺信息不是差异）。"""
        ca = _known_conditions(a)
        cb = _known_conditions(b)
        out = []
        for dim in self.DIM_ORDER:
            if dim in ca and dim in cb and str(ca[dim]) != str(cb[dim]):
                out.append(dim)
        return out

    def verdict(self, a: dict, b: dict) -> str:
        """返回 条件不同 / 条件不全 / 真冲突 / 同一问题。

        核心规则：**任一维度不同即不得判为冲突**——条件不同时直接返回「条件不同」，
        不再交给结论比对。结论是否对立由调用方通过 `conclusions_conflict` 传入
        （该判断需要语义理解，属专家侧职责；本方法只做条件门禁）。
        """
        ca = _known_conditions(a)
        cb = _known_conditions(b)
        if self.differing_dims(a, b):
            return "条件不同"
        # 九维条件必须双方齐全，否则不能把局部相同误判为完整条件相同。
        if any(dim not in ca or dim not in cb for dim in self.DIM_ORDER):
            return "条件不全"
        if a.get("conclusions_conflict") or b.get("conclusions_conflict"):
            return "真冲突"
        return "同一问题"
