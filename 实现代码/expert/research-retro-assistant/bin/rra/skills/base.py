"""技能基类：统一输入装载、输出契约化、以及「证据不足就拒绝」的行为。

模板方法 run()：装载 → build（子类实现，调平台专家）→ 契约校验 → 返回。
任一步失败都不产出半成品。
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


class SkillBase:
    """所有技能的公共骨架。子类只实现 `build()`。"""

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
        """子类实现：调用平台专家完成语义判断，返回契约对象。"""
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
