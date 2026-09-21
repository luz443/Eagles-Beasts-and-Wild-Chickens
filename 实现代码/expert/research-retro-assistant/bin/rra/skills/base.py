"""技能基类：统一输入装载、输出契约化、以及「证据不足就拒绝」的行为。

模板方法 run()：装载 → build（子类实现）→ 契约校验 → 返回。
任一步失败都不产出半成品。

**分工（2026-09-19 平台实测后的修订，见 docs/HANDOFF.md）**：
平台上技能脚本**无法调用模型**，所以语义判断由 LearnBuddy 专家本身完成，
技能代码只做**确定性把关**。因此 `build()` 的输入是「专家已经交回的产出」
（放在 `SkillInput.context["expert_output"]`），它要做的是：
规范化 → 规则门禁 → 违规抛 `ValueError` / 证据不足抛 `SkillRefusal`。
本层**不联网、不导入任何模型 SDK**——这是「网页侧零模型调用」之外的第二条硬边界。
"""

from dataclasses import dataclass, field
from typing import Any

from ..contracts.validator import Validator, Violation


@dataclass
class SkillInput:
    """技能输入：原始记录文本 + 库快照 + 可选上下文。"""

    raw_text: str = ""
    library: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillOutput:
    """技能输出：契约对象 + 给人看的措辞。两者必须一致。"""

    payload: dict[str, Any]
    narrative: str = ""
    warnings: list[str] = field(default_factory=list)


class SkillRefusal(Exception):
    """证据不足时拒绝产出。宁可拒绝，也不产出无依据的结论。"""

    def __init__(self, reason: str, missing: list[str] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.missing = missing or []


EXPERT_OUTPUT_KEY = "expert_output"


def expert_output(payload: SkillInput) -> Any:
    """取出专家交回的产出（语义判断的载体）。

    技能脚本调不到模型，所以"专家产出"由调用方通过 `context["expert_output"]` 传入。
    缺失即拒绝——绝不能因为拿不到专家产出就自己编一个。
    """
    value = (payload.context or {}).get(EXPERT_OUTPUT_KEY)
    if value is None:
        raise SkillRefusal("缺少专家产出（context.%s）" % EXPERT_OUTPUT_KEY,
                           missing=[EXPERT_OUTPUT_KEY])
    return value


def normalize_archive(raw: dict) -> dict:
    """规范化专家交回的档案：只做**不改变语义**的清洗。

    - 字符串字段去掉首尾空白（引文核验本就按规范化文本比对，不影响可复核性）；
    - `conditions` 去掉空白取值（空白等于缺失，与校验器口径一致）；
    - `missing_info` 去重且保序（重复项会让"还缺什么"看起来更长）；
    - 列表型字段保证是列表，避免下游逐字符迭代。

    刻意**不做**的事：不补默认值、不猜条件、不改写措辞——那是语义判断。
    """
    if not isinstance(raw, dict):
        raise ValueError("档案不是对象：%r" % type(raw).__name__)
    out = dict(raw)

    for key, value in list(out.items()):
        if isinstance(value, str):
            out[key] = value.strip()

    conditions = out.get("conditions")
    if isinstance(conditions, dict):
        cleaned = {dim: value.strip() for dim, value in conditions.items()
                   if isinstance(value, str) and value.strip()}
        if cleaned:
            out["conditions"] = cleaned
        else:
            out.pop("conditions", None)      # 空对象与缺失等价（见 docs/record-format.md）

    missing = out.get("missing_info")
    if isinstance(missing, list):
        seen: set[str] = set()
        deduped: list[str] = []
        for item in missing:
            text = str(item).strip()
            if text and text not in seen:
                seen.add(text)
                deduped.append(text)
        out["missing_info"] = deduped

    for key in ("links", "evidence_refs", "artifacts"):
        if key in out and not isinstance(out[key], list):
            raise ValueError("%s 不是列表" % key)

    for key in ("resurrection", "challenge"):
        if key in out and not isinstance(out[key], dict):
            raise ValueError("%s 不是对象" % key)

    return out


def first_missing(payload: dict, keys: tuple[str, ...]) -> list[str]:
    """列出 payload 中「取不到非空字符串」的字段名（用于拒绝时逐项说明缺什么）。"""
    out = []
    for key in keys:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            out.append(key)
    return out


class SkillBase:
    """所有技能的公共骨架。子类只实现 `build()`。

    `build()` 保持抽象（`NotImplementedError`）是**有意为之**：它是子类的契约，
    给一个"默认实现"会让「忘了写门禁」的技能静默通过。子类必须显式交出把关逻辑。
    """

    name = "skill"
    prompt_path = ""

    def __init__(self, validator: Validator | None = None) -> None:
        self.validator = validator or Validator()

    def run(self, payload: SkillInput) -> SkillOutput:
        """模板方法：子类 build 抛 SkillRefusal 则原样上抛；输出经校验后返回。"""
        if not payload.raw_text.strip():
            raise SkillRefusal("输入为空", missing=["raw_text"])
        output = self.build(payload)
        violations = self.validate(output)
        if violations:
            raise ValueError(
                "技能输出未通过契约校验：" + "；".join(str(v) for v in violations))
        return output

    def build(self, payload: SkillInput) -> SkillOutput:
        """子类实现：**确定性把关**专家交回的产出（取 `expert_output(payload)`）。

        子类要做的四步：取专家 JSON → 规则门禁 → 规范化 → 违规抛 `ValueError` /
        证据不足抛 `SkillRefusal`。语义判断不在这里发生（见模块文档的分工说明），
        所以这里既不该联网，也不该导入任何模型 SDK。
        """
        raise NotImplementedError

    def validate(self, output: SkillOutput) -> list[Violation]:
        """对 payload 做校验：当且仅当 payload 形如档案（含 id 字段）时走档案校验。

        不是所有技能的 payload 都是完整档案（例如归纳技能输出的是假设清单），
        对这类输出由子类自行覆盖 validate；基类默认只对档案形状的对象做校验，
        避免把非档案输出误判为「缺一堆必填字段」。
        """
        payload = output.payload
        if isinstance(payload, dict) and "id" in payload:
            return self.validator.validate_archive(payload)
        return []
