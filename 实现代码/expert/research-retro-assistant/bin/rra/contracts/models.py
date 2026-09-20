"""档案数据模型。专家输出与网页输入共用这一套形状。

两条约定（解析器与校验器都以此为准）：

1. `to_dict()` 输出**规范化后的完整字段集**；`Provenance.remap_from` 与
   `Archive.conditions` 为空时不输出，兼容历史档案的往返结果。
2. `from_dict()` 不做静默兜底：必填字段缺失抛 `KeyError`，枚举非法抛 `ValueError`
   （含允许取值清单）。是否可接受由上游 Validator 决定，模型层只负责如实失败。
"""

from dataclasses import dataclass, field
from typing import Any

from .dims import Dim


def _to_dim(raw: str) -> Dim:
    """字符串转枚举；非法取值直接报错并列出允许值。"""
    try:
        return Dim(raw)
    except ValueError:
        allowed = ", ".join(d.value for d in Dim)
        raise ValueError("未知条件维度 %r，允许取值：%s" % (raw, allowed)) from None


@dataclass
class Attribution:
    """归因。类型只允许 assumption / observed，日志未给出原因时必须是 assumption。"""

    text: str
    type: str = "assumption"

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "type": self.type}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Attribution":
        return cls(text=raw["text"], type=raw.get("type", "assumption"))


@dataclass
class Artifact:
    """关联产物：代码版本、数据版本、实验日志。"""

    kind: str
    ref: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "ref": self.ref}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Artifact":
        return cls(kind=raw["kind"], ref=raw["ref"])


@dataclass
class DimValue:
    """相同点：某个条件维度上的相同取值。"""

    dim: Dim
    value: str

    def to_dict(self) -> dict[str, Any]:
        return {"dim": self.dim.value, "value": self.value}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DimValue":
        return cls(dim=_to_dim(raw["dim"]), value=raw["value"])


@dataclass
class DimDelta:
    """不同点：某个条件维度上的差异。网页对比矩阵的高亮依据。"""

    dim: Dim
    from_value: str
    to_value: str

    def to_dict(self) -> dict[str, Any]:
        return {"dim": self.dim.value, "from": self.from_value, "to": self.to_value}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DimDelta":
        return cls(dim=_to_dim(raw["dim"]), from_value=raw["from"], to_value=raw["to"])


@dataclass
class Link:
    """与库内另一条档案的关系。relation 为 重复 / 相似 / 冲突。"""

    target: str
    relation: str
    same: list[DimValue] = field(default_factory=list)
    diff: list[DimDelta] = field(default_factory=list)
    transferable: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "relation": self.relation,
            "same": [s.to_dict() for s in self.same],
            "diff": [d.to_dict() for d in self.diff],
            "transferable": self.transferable,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Link":
        return cls(
            target=raw["target"],
            relation=raw["relation"],
            same=[DimValue.from_dict(x) for x in raw.get("same", [])],
            diff=[DimDelta.from_dict(x) for x in raw.get("diff", [])],
            transferable=raw.get("transferable", ""),
        )


@dataclass
class EvidenceRef:
    """证据引用。必须同时给出档案编号与原文片段，否则不允许出现在输出里。"""

    record: str
    quote: str

    def to_dict(self) -> dict[str, Any]:
        return {"record": self.record, "quote": self.quote}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvidenceRef":
        return cls(record=raw["record"], quote=raw["quote"])


@dataclass
class Provenance:
    """来源信息。source 只允许 真实 / 模拟；导入冲突重编号时记录 remap_from。"""

    author: str
    date: str
    source: str
    remap_from: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"author": self.author, "date": self.date, "source": self.source}
        if self.remap_from:
            out["remap_from"] = self.remap_from
        return out

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Provenance":
        return cls(author=raw["author"], date=raw["date"], source=raw["source"],
                   remap_from=raw.get("remap_from"))


@dataclass
class Archive:
    """一条尝试记录。字段口径见 docs/record-format.md。"""

    id: str
    attempt: str
    expectation: str
    observation: str
    blocker: str
    attribution: Attribution
    boundary: str
    confidence: str
    status: str
    provenance: Provenance
    missing_info: list[str] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    dedup_key: str = ""
    version: int = 1
    conditions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out = {
            "id": self.id,
            "attempt": self.attempt,
            "expectation": self.expectation,
            "observation": self.observation,
            "blocker": self.blocker,
            "attribution": self.attribution.to_dict(),
            "missing_info": list(self.missing_info),
            "boundary": self.boundary,
            "confidence": self.confidence,
            "status": self.status,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "links": [x.to_dict() for x in self.links],
            "evidence_refs": [e.to_dict() for e in self.evidence_refs],
            "dedup_key": self.dedup_key,
            "version": self.version,
            "provenance": self.provenance.to_dict(),
        }
        if self.conditions:
            out["conditions"] = dict(self.conditions)
        return out

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Archive":
        return cls(
            id=raw["id"],
            attempt=raw["attempt"],
            expectation=raw["expectation"],
            observation=raw["observation"],
            blocker=raw["blocker"],
            attribution=Attribution.from_dict(raw["attribution"]),
            boundary=raw["boundary"],
            confidence=raw["confidence"],
            status=raw["status"],
            provenance=Provenance.from_dict(raw["provenance"]),
            missing_info=list(raw.get("missing_info", [])),
            artifacts=[Artifact.from_dict(x) for x in raw.get("artifacts", [])],
            links=[Link.from_dict(x) for x in raw.get("links", [])],
            evidence_refs=[EvidenceRef.from_dict(x) for x in raw.get("evidence_refs", [])],
            dedup_key=raw.get("dedup_key", ""),
            version=int(raw.get("version", 1)),
            conditions={_to_dim(key).value: value for key, value in raw.get("conditions", {}).items()},
        )

    def citation(self) -> str:
        """引用格式：R-013@v2（课题组，2026-08）。

        被关联次数是派生指标（由 links[].target 统计），不写进档案。
        """
        return "%s@v%d（%s，%s）" % (self.id, self.version, self.provenance.author,
                                    self.provenance.date)


@dataclass
class Library:
    """经验库：一批档案 + 版本与生成时间。"""

    version: str
    records: list[Archive] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "records": [r.to_dict() for r in self.records],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Library":
        return cls(
            version=raw["version"],
            generated_at=raw.get("generated_at", ""),
            records=[Archive.from_dict(x) for x in raw.get("records", [])],
        )

    def index(self) -> dict[str, Archive]:
        """按编号建索引，供引用解析使用。编号重复时直接报错，不静默覆盖。"""
        out: dict[str, Archive] = {}
        for r in self.records:
            if r.id in out:
                raise ValueError("档案编号重复：%s" % r.id)
            out[r.id] = r
        return out
