"""确定性契约校验。用例 25 依赖它；技能产出的入口处调用，杜绝半成品进库。

设计约束：
- 纯函数、无副作用、不依赖运行时模型判断；
- 每条违规必须给出「路径 + 原因 + 期望」，不允许只说「有问题」；
- 校验规则与 contracts/record.schema.json 保持同一口径（枚举值写死在此处，
  由 test_dims 与 schema 双向核对，见 tests/test_dims.py）。
"""

import re
from dataclasses import dataclass

from .dims import Dim
from .models import Archive, Library

_ID_PATTERN = re.compile(r"^R-[0-9]{3,}$")
_ATTRIBUTION_TYPES = {"assumption", "observed"}
_CONFIDENCE = {"high", "medium", "low"}
_STATUSES = {"进行中", "已放弃", "已绕过", "已解决"}
_RELATIONS = {"重复", "相似", "冲突"}
_QUOTE_MIN = 4

_REQUIRED_TOP = [
    "id", "attempt", "expectation", "observation", "blocker",
    "attribution", "boundary", "confidence", "status", "provenance",
]
_ALLOWED_TOP = {
    "id", "attempt", "expectation", "observation", "blocker", "attribution",
    "missing_info", "boundary", "confidence", "status", "artifacts", "links",
    "evidence_refs", "dedup_key", "version", "provenance", "conditions",
}
# 与 record.schema.json 的 minLength: 1 对齐，按**原串**长度判（不 trim），
# 避免「schema 按原串、校验器按 trim」造成的两端漂移。
_STRING_REQUIRED = [
    "id", "attempt", "expectation", "observation", "blocker", "boundary",
]
_REQUIRED_PROVENANCE = ["author", "date", "source"]
_SOURCES = {"真实", "模拟"}


@dataclass
class Violation:
    """一条违规：定位 + 原因 + 期望。三要素缺一不可。"""

    path: str
    reason: str
    expected: str

    def __str__(self) -> str:
        return "%s：%s（期望：%s）" % (self.path, self.reason, self.expected)


class Validator:
    """纯函数式校验器。"""

    def validate_archive(self, raw: dict) -> list[Violation]:
        """校验单条档案：必填字段、枚举取值、编号与引用格式、dim 是否取自枚举。"""
        out: list[Violation] = []
        if not isinstance(raw, dict):
            return [Violation("$", "不是对象", "dict")]

        for key in _REQUIRED_TOP:
            v = raw.get(key)
            if v is None or (isinstance(v, str) and not v.strip()):
                out.append(Violation(key, "必填字段缺失或为空", "非空 %s" % key))

        # 声明了 additionalProperties: false，就必须真的执行——否则契约形同虚设
        for key in raw:
            if key not in _ALLOWED_TOP:
                out.append(Violation(key, "出现契约未声明的字段", "只允许契约内的字段"))

        if "conditions" in raw:
            conditions = raw["conditions"]
            if not isinstance(conditions, dict):
                out.append(Violation("conditions", "不是对象", "object"))
            else:
                for dim, value in conditions.items():
                    path = "conditions.%s" % dim
                    if not self.dim_is_enum(dim):
                        out.append(Violation(path, "条件维度不是枚举值", "九维枚举之一"))
                    if not isinstance(value, str) or len(value) == 0:
                        out.append(Violation(path, "条件值不是非空字符串", "string，至少 1 个字符"))

        # 字符串字段必须真的是字符串：否则下游 .slice / 拼接会崩
        for key in _STRING_REQUIRED:
            v = raw.get(key)
            if v is not None and not isinstance(v, str):
                out.append(Violation(key, "字段类型不是字符串", "string"))

        rid = raw.get("id", "")
        if rid and not _ID_PATTERN.match(str(rid)):
            out.append(Violation("id", "编号格式不合法", "R-###（R-加三位以上数字）"))

        attr = raw.get("attribution")
        if attr is not None and not isinstance(attr, dict):
            out.append(Violation("attribution", "不是对象", "object"))
        if isinstance(attr, dict):
            atype = attr.get("type")
            if atype not in _ATTRIBUTION_TYPES:
                out.append(Violation(
                    "attribution.type", "归因类型不在枚举内",
                    "assumption / observed（日志未给出原因时必须是 assumption）"))
            if not isinstance(attr.get("text", ""), str) or not attr.get("text", "").strip():
                out.append(Violation("attribution.text", "归因文本为空", "非空字符串"))

        if raw.get("confidence") not in _CONFIDENCE:
            out.append(Violation("confidence", "置信度不在枚举内", "high / medium / low"))
        if raw.get("status") not in _STATUSES:
            out.append(Violation("status", "状态不在枚举内", " / ".join(sorted(_STATUSES))))

        prov = raw.get("provenance")
        if prov is not None and not isinstance(prov, dict):
            out.append(Violation("provenance", "不是对象", "object"))
        if isinstance(prov, dict):
            for key in _REQUIRED_PROVENANCE:
                val = prov.get(key, "")
                if not isinstance(val, str) or not val.strip():
                    out.append(Violation("provenance.%s" % key, "来源信息缺失", "非空字符串"))
            if prov.get("source") not in _SOURCES:
                out.append(Violation("provenance.source", "数据来源不在枚举内", "真实 / 模拟"))

        # 列表型字段的结构检查必须放在最前：否则 `links: "bad"` 会被逐字符迭代，
        # `links: [null]` 会在下面一行 `.get()` 直接抛 AttributeError（外部审查 P1）。
        for field in _LIST_FIELDS:
            if raw.get(field) is not None and not isinstance(raw.get(field), list):
                out.append(Violation(field, "不是列表", "list"))

        for i, link in enumerate(_as_list(raw.get("links"))):
            base = "links[%d]" % i
            if not isinstance(link, dict):
                out.append(Violation(base, "元素不是对象", "object"))
                continue
            if link.get("relation") not in _RELATIONS:
                out.append(Violation(base + ".relation", "关系不在枚举内", "重复 / 相似 / 冲突"))
            target = str(link.get("target", ""))
            if target and not _ID_PATTERN.match(target):
                out.append(Violation(base + ".target", "目标编号格式不合法", "R-###"))
            for key, label in (("same", "相同点"), ("diff", "不同点")):
                if link.get(key) is not None and not isinstance(link.get(key), list):
                    out.append(Violation(base + "." + key, "不是列表", "list"))
                for j, dim_value in enumerate(_as_list(link.get(key))):
                    if not isinstance(dim_value, dict):
                        out.append(Violation("%s.%s[%d]" % (base, key, j), "元素不是对象", "object"))
                        continue
                    if not self.dim_is_enum(str(dim_value.get("dim", ""))):
                        out.append(Violation(
                            "%s.%s[%d].dim" % (base, key, j), "条件维度不是枚举值",
                            "九维枚举之一（model/seq_len/...，禁止自由文本）"))

        for i, ref in enumerate(_as_list(raw.get("evidence_refs"))):
            base = "evidence_refs[%d]" % i
            if not isinstance(ref, dict):
                out.append(Violation(base, "元素不是对象", "object"))
                continue
            record = str(ref.get("record", ""))
            if not _ID_PATTERN.match(record):
                out.append(Violation(base + ".record", "证据编号格式不合法", "R-###"))
            if not isinstance(ref.get("quote", ""), str):
                out.append(Violation(base + ".quote", "原文片段不是字符串", "string"))
                continue
            quote = ref.get("quote", "")
            if len(quote) < _QUOTE_MIN:
                out.append(Violation(
                    base + ".quote", "原文片段过短，无法复核",
                    "至少 %d 个字符的原文摘录" % _QUOTE_MIN))

        return out

    def validate_library(self, raw: dict) -> list[Violation]:
        """校验整库：编号唯一、links / evidence_refs 指向的档案存在、**引文可复核**。

        「引文可复核」是跨档案检查，只能在整库层做：拿被引用档案的可核验字段
        （见 QUOTABLE_FIELDS）去比对引文，找不到即报违规。
        单档案校验（validate_archive）没有别的档案可查，不做这一层 —— 边界写在这里，免得被误读。
        """
        out: list[Violation] = []
        if not isinstance(raw, dict):
            return [Violation("$", "不是对象", "dict")]
        records = raw.get("records")
        if not isinstance(records, list):
            return [Violation("records", "缺少档案列表", "list")]

        seen: dict[str, int] = {}
        for i, rec in enumerate(records):
            if not isinstance(rec, dict):
                out.append(Violation("records[%d]" % i, "元素不是对象", "object"))
                continue
            out.extend(
                Violation("records[%d].%s" % (i, v.path), v.reason, v.expected)
                for v in self.validate_archive(rec))
            rid = str(rec.get("id", ""))
            if rid:
                if rid in seen:
                    out.append(Violation(
                        "records[%d].id" % i, "档案编号重复（首次出现在 records[%d]）" % seen[rid],
                        "编号唯一"))
                else:
                    seen[rid] = i

        known = set(seen)
        by_id = {str(r.get("id", "")): r for r in records if isinstance(r, dict)}
        for i, rec in enumerate(records):
            if not isinstance(rec, dict):
                continue
            for j, link in enumerate(_as_list(rec.get("links"))):
                if not isinstance(link, dict):
                    continue                      # 元素类型问题由 validate_archive 报出
                target = str(link.get("target", ""))
                if target and target not in known:
                    out.append(Violation(
                        "records[%d].links[%d].target" % (i, j),
                        "指向的档案不存在", "指向库内编号之一"))
            for j, ref in enumerate(_as_list(rec.get("evidence_refs"))):
                if not isinstance(ref, dict):
                    continue
                rid = str(ref.get("record", ""))
                if not rid:
                    continue
                if rid not in known:
                    out.append(Violation(
                        "records[%d].evidence_refs[%d].record" % (i, j),
                        "引用的档案不存在", "指向库内编号之一"))
                    continue
                quote = ref.get("quote")
                target = by_id.get(rid)
                if target is None or not isinstance(quote, str) or not quote.strip():
                    continue                      # 缺引文/类型问题由 validate_archive 负责
                if not _quote_matches(quote, target):
                    out.append(Violation(
                        "records[%d].evidence_refs[%d].quote" % (i, j),
                        "引文在被引用档案里找不到（不可复核）",
                        "该档案的 %s 中真实存在的原文片段" % " / ".join(QUOTABLE_FIELDS)))

        return out

    def assert_valid(self, archive: Archive) -> None:
        """不合法即抛错，错误信息带全部违规。"""
        vs = self.validate_archive(archive.to_dict())
        if vs:
            raise ValueError("档案未通过契约校验：" + "；".join(str(v) for v in vs))

    def dim_is_enum(self, value: str) -> bool:
        """dim 是否属于九个维度之一。自由文本一律拒绝。"""
        return value in {d.value for d in Dim}


# ---------------------------------------------------------------------------
# 结构容错与「引文可复核」检查
#
# 2026-09-19 外部代码审查报出两处：① `links: [null]` 之类畸形嵌套会让 `.get()` 抛
# AttributeError（校验器应该报违规，而不是把调用方打崩）；② 引用片段只查长度不查内容，
# 编造 4 个字就能过 —— 「证据必须可复核」这条铁律在代码层等于空的。
# ---------------------------------------------------------------------------

# 列表型字段：既要是列表，元素也要是对象。缺一个就会在校验里炸。
_LIST_FIELDS = ("links", "evidence_refs", "artifacts", "missing_info")

# 引文允许取自被引用档案的哪些字段。
# 必须与网页端取引文的位置一致（`web/js/refute.js` 从 attribution.text → observation → blocker
# 逐级回退），否则会制造新的跨端分叉：网页能取到的引文、专家侧却判为不可复核。
QUOTABLE_FIELDS = ("attribution.text", "observation", "blocker")

_NORMALIZER = None


def _normalize(text: str) -> str:
    """与去重指纹同一套规范化（NFKC + 去标点 + 去空白 + 小写），避免两处口径不同。

    延迟导入：`library.dedup` 会 import contracts.models，模块级导入会形成 contracts ↔ library 环。
    """
    global _NORMALIZER
    if _NORMALIZER is None:
        from ..library.dedup import Deduplicator
        _NORMALIZER = Deduplicator().normalize
    return _NORMALIZER(text)


def _as_list(value) -> list:
    """宽容取列表：None / 非列表一律当空列表（类型问题由 _check_list_fields 负责报出）。"""
    return value if isinstance(value, list) else []


def _quoted_text_of(archive: dict) -> list[str]:
    """被引用档案里可用于复核的原文（三个字段各自独立比对，不跨字段拼接）。"""
    attribution = archive.get("attribution")
    text = attribution.get("text", "") if isinstance(attribution, dict) else ""
    return [str(text), str(archive.get("observation", "")), str(archive.get("blocker", ""))]


def _quote_matches(quote: str, target: dict) -> bool:
    """引文是否真的出现在目标档案的可核验字段里。

    空引文（例如只有标点，规范化后为空串）一律判为不匹配 ——
    否则 `"" in 任意字符串` 会恒真，等于把检查关掉。
    """
    q = _normalize(quote)
    if not q:
        return False
    return any(q in _normalize(field) for field in _quoted_text_of(target))
