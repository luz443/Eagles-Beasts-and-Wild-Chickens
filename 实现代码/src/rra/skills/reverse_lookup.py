"""技能 2：入库即反查。输出候选证据 + 缺失信息；澄清后更新结论强度。

分工（见 base.py 模块文档）：**「这两条是不是同一个问题」是语义判断，由专家完成**；
本文件只做确定性把关——反查结果里出现的每个编号都必须真实存在于库中，
引文必须够长可复核，无命中时**一个编号都不许出现**。
"""

from datetime import datetime

from .base import (
    SkillBase, SkillInput, SkillOutput, SkillRefusal, expert_output, normalize_archive,
)

_QUOTE_MIN = 4


def _library_ids(library: dict) -> set[str]:
    return {str(r.get("id", "")) for r in (library or {}).get("records", [])
            if isinstance(r, dict) and r.get("id")}


class ReverseLookupSkill(SkillBase):
    name = "reverse_lookup"
    prompt_path = "prompts/reverse_lookup.md"

    def build(self, payload: SkillInput) -> SkillOutput:
        """把关反查结果：编号必须真实存在、引文必须够长、无命中不得有编号。"""
        if not (payload.library or {}).get("records"):
            raise SkillRefusal("没有库文件就无法反查", missing=["library"])

        raw = expert_output(payload)
        archive = normalize_archive(raw)
        known = _library_ids(payload.library)
        context = payload.context or {}
        warnings = [str(w) for w in (context.get("warnings") or [])]

        refs = archive.get("evidence_refs") or []
        links = archive.get("links") or []

        # 编号必须真实存在 —— 编造编号是本作品最致命的失效（用例 24 的诱导幻觉）。
        for i, ref in enumerate(refs):
            rid = str(ref.get("record", ""))
            if rid and rid not in known:
                raise ValueError("evidence_refs[%d].record 指向库内不存在的档案：%s" % (i, rid))
        for i, link in enumerate(links):
            target = str(link.get("target", ""))
            if target and target not in known:
                raise ValueError("links[%d].target 指向库内不存在的档案：%s" % (i, target))

        # 引文要够长；内容是否逐字可复核由整库校验负责（这里没有别的档案可查）。
        for i, ref in enumerate(refs):
            quote = ref.get("quote")
            if not isinstance(quote, str) or len(quote) < _QUOTE_MIN:
                raise ValueError("evidence_refs[%d].quote 过短，无法复核（至少 %d 个字符）"
                                 % (i, _QUOTE_MIN))

        # 无命中就如实说无：此时不得留下任何编号。
        if not refs and not links:
            warnings.append("库内没有相关记录：本次未产出任何候选编号（不得硬凑相似档案）。")

        violations = self.validator.validate_archive(archive)
        if violations:
            raise ValueError("反查结果未通过契约校验：" + "；".join(str(v) for v in violations))

        return SkillOutput(
            payload=archive,
            narrative=str(context.get("narrative", "")),
            warnings=warnings,
        )

    def update_after_clarification(self, output: SkillOutput, answer: str) -> SkillOutput:
        """澄清往返的**确定性**部分：记账 + 版本推进 + 答复留痕。

        语义重判（结论强度、证据引用是否更新）仍由专家在下一轮完成；
        这里只保证「补充过什么」被如实记录（含答复原文）、且入库版本与澄清前那一版可区分。
        """
        answer = str(answer or "").strip()
        if not answer:
            raise SkillRefusal("澄清答复为空", missing=["answer"])

        resolved = self.resolved_keys(output.payload, answer)
        if not resolved:
            return SkillOutput(
                payload=dict(output.payload),
                narrative=output.narrative,
                warnings=list(output.warnings) + [
                    "澄清答复未匹配到任何缺失字段（%s），档案未变更" % answer],
            )

        updated = self.apply_clarification_facts(output, resolved, answer=answer)
        return SkillOutput(
            payload=updated.payload,
            narrative=output.narrative,
            warnings=list(updated.warnings) + ["澄清答复已记录：%s" % answer],
        )

    def resolved_keys(self, archive: dict, answer: str) -> list[str]:
        """从答复文本里认出被澄清的缺失字段（确定性：按字段名是否出现在答复里）。

        认不出来就返回空列表——**不猜**。猜错的代价是「档案说补过了，其实没补」，
        比多留一条 missing_info 严重得多。
        """
        text = answer.lower()
        return [str(m) for m in (archive.get("missing_info") or [])
                if str(m) and str(m).lower() in text]

    def apply_clarification_facts(self, output: SkillOutput, resolved_keys: list[str],
                                  answer: str = "") -> SkillOutput:
        """确定性记账：移除已澄清的 missing_info、档案版本 +1、答复原文进 `clarifications`。

        版本递增是刻意的：入库版本与澄清前那一版必须可区分
        （对应设计方案 3.2 的「最终确认的那一版才是入库版本」）。

        `answer` 是答复原文，按 `{"key", "answer", "at"}` 逐项追加进 `clarifications`——
        只把答复放在 warnings 里等于没留痕，日后无法复核「补了什么」（P2-10）。
        取不到答复原文（answer 为空）时不编造：宁可不留痕，也不写一条查不到出处的记录。
        """
        payload = dict(output.payload)
        resolved = {str(k) for k in resolved_keys}
        missing = [m for m in payload.get("missing_info", []) if str(m) not in resolved]
        payload["missing_info"] = missing
        payload["version"] = int(payload.get("version", 1)) + 1

        text = str(answer or "").strip()
        if text:
            log = [dict(item) for item in (payload.get("clarifications") or [])]
            at = datetime.now().isoformat(timespec="seconds")
            for key in resolved_keys:
                log.append({"key": str(key), "answer": text, "at": at})
            payload["clarifications"] = log

        warnings = list(output.warnings) + [
            "已澄清字段：%s；文档版本递增至 v%d" % ("、".join(resolved_keys), payload["version"])]
        return SkillOutput(payload=payload, narrative=output.narrative, warnings=warnings)
