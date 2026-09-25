"""技能 3：条件比较。任一维度不同即不得判为冲突。

分工（见 base.py 模块文档）：**「结论是否对立」是语义判断，由专家传入
`conclusions_conflict` 标记**；本文件是**纯门禁**——只按条件维度裁定，
并保证两条规则落地：任一维度不同 → 不得判冲突；九维不全 → 不得下结论。
"""

from ..contracts.dims import Dim
from ..contracts.validator import Violation
from .base import SkillBase, SkillInput, SkillOutput, SkillRefusal

VERDICTS = ("同一问题", "条件不同", "条件不全", "真冲突")


def _known_conditions(record: dict) -> dict[str, str]:
    """比较时只采用去除首尾空白后仍有内容的字符串条件。

    取值处必须自己判类型：`record` / `conditions` 不是对象时报 `ValueError`（规格问题），
    而不是让 `.get()` / `.items()` 把 AttributeError 抛给调用方（2026-09-22 审查 P2-7）。
    """
    if not isinstance(record, dict):
        raise ValueError("待比较的记录不是对象：%r" % type(record).__name__)
    conditions = record.get("conditions")
    if conditions is None:
        return {}
    if not isinstance(conditions, dict):
        raise ValueError("conditions 不是对象：%r" % type(conditions).__name__)
    return {dim: value.strip() for dim, value in conditions.items()
            if isinstance(value, str) and value.strip()}


class ConditionCompareSkill(SkillBase):
    name = "condition_compare"
    prompt_path = "prompts/condition_compare.md"

    DIM_ORDER = [
        "model", "seq_len", "batch", "micro_batch", "precision",
        "hardware", "dataset_version", "stage", "framework",
    ]

    def build(self, payload: SkillInput) -> SkillOutput:
        """裁定两条记录的关系。裁定完全由条件维度决定，不做语义推断。"""
        records = (payload.context or {}).get("records")
        if not isinstance(records, list) or len(records) < 2:
            raise SkillRefusal("条件比较至少需要两条记录", missing=["records"])
        a, b = records[0], records[1]
        if not isinstance(a, dict) or not isinstance(b, dict):
            raise ValueError("待比较的记录必须是对象")

        verdict = self.verdict(a, b)
        diff = self.differing_dims(a, b)
        missing = self.missing_dims(a, b)
        warnings = []
        if verdict == "条件不同":
            warnings.append("存在条件差异（%s）：不得据此判定结论冲突" % "、".join(diff))
        elif verdict == "条件不全":
            warnings.append("缺维度（%s）：条件不齐全，不得下任何方向性结论"
                            % "、".join(missing))
        elif verdict == "真冲突":
            warnings.append("条件一致且有人工冲突标记：需人工复核，不代表哪一方有误")

        return SkillOutput(
            payload={"verdict": verdict, "differing_dims": diff, "missing_dims": missing},
            narrative=str((payload.context or {}).get("narrative", "")),
            warnings=warnings,
        )

    def missing_dims(self, a: dict, b: dict) -> list[str]:
        """至少一侧未提供取值的维度（按固定顺序，便于两端对齐）。"""
        ca, cb = _known_conditions(a), _known_conditions(b)
        return [dim for dim in self.DIM_ORDER if dim not in ca or dim not in cb]

    def validate(self, output: SkillOutput) -> list[Violation]:
        """payload 是裁定而非档案，所以不用档案校验：只查裁定枚举与维度取值。"""
        payload = output.payload
        out: list[Violation] = []
        if not isinstance(payload, dict):
            return [Violation("$", "不是对象", "dict")]
        if payload.get("verdict") not in VERDICTS:
            out.append(Violation("verdict", "裁定不在枚举内", " / ".join(VERDICTS)))
        allowed = {d.value for d in Dim}
        for key in ("differing_dims", "missing_dims"):
            value = payload.get(key)
            if not isinstance(value, list):
                out.append(Violation(key, "不是列表", "list"))
                continue
            for i, dim in enumerate(value):
                if dim not in allowed:
                    out.append(Violation("%s[%d]" % (key, i), "维度不是枚举值", "九维枚举之一"))
        return out

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
