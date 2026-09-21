"""技能 6（附录 D.1 的 D5）：审稿人 2 号。

立项检查从「给你看历史」升级为「主动质询」；每条质疑必须带证据编号。

分工（见 base.py 模块文档）：**质询的措辞是语义判断，由专家完成**；
本文件只做一件事，但这件事故意做得很硬：**没有证据编号的质询整条丢弃**。
丢掉的条目会记在 warnings 里——不静默吞掉，否则使用者会以为「专家没提意见」。
"""

import re

from ..contracts.validator import Violation
from .base import SkillBase, SkillInput, SkillOutput, SkillRefusal, expert_output

_ID_RE = re.compile(r"^R-[0-9]{3,}$")


class Reviewer2Skill(SkillBase):
    name = "reviewer2"
    prompt_path = "prompts/reviewer2.md"

    def build(self, payload: SkillInput) -> SkillOutput:
        """把关质询清单：无编号的整条丢弃，编号不存在的按违规报出。"""
        known = {str(r.get("id", "")) for r in (payload.library or {}).get("records", [])
                 if isinstance(r, dict) and r.get("id")}

        raw = expert_output(payload)
        if not isinstance(raw, dict) or not isinstance(raw.get("challenges"), list):
            raise ValueError("质询结果必须是含 challenges 列表的对象")

        kept, dropped = [], []
        for i, item in enumerate(raw["challenges"]):
            if not isinstance(item, dict):
                dropped.append("challenges[%d]：不是对象" % i)
                continue
            text = str(item.get("text", "")).strip()
            if not text:
                dropped.append("challenges[%d]：内容为空" % i)
                continue
            if not self.is_grounded(item):
                dropped.append("challenges[%d]：无证据编号（无出处的质询不得进库）" % i)
                continue
            ids = [str(x) for x in item["evidence_ids"]]
            if known:
                stray = [x for x in ids if x not in known]
                if stray:
                    raise ValueError("challenges[%d].evidence_ids 指向库内不存在的档案：%s"
                                     % (i, "、".join(stray)))
            kept.append({"text": text, "evidence_ids": ids})

        if not kept:
            raise SkillRefusal(
                "没有任何带证据编号的质询可产出（共丢弃 %d 条）" % len(dropped),
                missing=["带 R-### 编号的质询"])

        warnings = []
        if dropped:
            warnings.append("已丢弃无证据编号的质询：%s" % "；".join(dropped))
        warnings.append("质询的次数陈述只是引子，不构成对探索方向的判决。")

        return SkillOutput(
            payload={"challenges": kept, "dropped": dropped},
            narrative=str((payload.context or {}).get("narrative", "")),
            warnings=warnings,
        )

    def validate(self, output: SkillOutput) -> list[Violation]:
        """payload 是质询清单而非档案：只查每条质询都有非空的 R-### 编号。"""
        payload = output.payload
        out: list[Violation] = []
        if not isinstance(payload, dict):
            return [Violation("$", "不是对象", "dict")]
        items = payload.get("challenges")
        if not isinstance(items, list):
            return [Violation("challenges", "不是列表", "list")]
        for i, item in enumerate(items):
            base = "challenges[%d]" % i
            if not isinstance(item, dict):
                out.append(Violation(base, "元素不是对象", "object"))
                continue
            if not str(item.get("text", "")).strip():
                out.append(Violation(base + ".text", "质询内容为空", "非空字符串"))
            ids = item.get("evidence_ids")
            if not isinstance(ids, list) or not ids:
                out.append(Violation(base + ".evidence_ids", "缺少证据编号", "至少一个 R-###"))
                continue
            for j, one in enumerate(ids):
                if not isinstance(one, str) or not _ID_RE.match(one):
                    out.append(Violation("%s.evidence_ids[%d]" % (base, j),
                                         "证据编号格式不合法", "R-###"))
        return out

    def is_grounded(self, challenge: dict) -> bool:
        """没有证据编号的质疑一律视为不合格，必须丢弃。

        规则写死：列表非空且每一项都必须匹配 R-###；缺编号的质询不进输出。
        """
        ids = (challenge or {}).get("evidence_ids") or []
        return bool(ids) and all(isinstance(i, str) and _ID_RE.match(i) for i in ids)
