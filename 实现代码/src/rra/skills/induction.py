"""技能 4：归纳孵化。同一阻塞点多条记录 → 待验证假设清单（H 编号）。

分工（见 base.py 模块文档）：**假设的措辞是语义判断，由专家完成**；
本文件不让「证据不足却产出假设」发生——门槛（≥3 条独立尝试、纠错记录不计）、
支撑编号必须真实存在、每条假设必须带最小验证动作，三条都在这里把住。
"""

from ..contracts.validator import Violation
from ..library.refutation import exclude_refutations
from .base import SkillBase, SkillInput, SkillOutput, SkillRefusal, expert_output

# 每条假设必须齐备的四项（缺一项就不是假设，而是方向性评论）。
REQUIRED_FIELDS = ("blocker", "supporting", "consensus", "unverified", "unlocks", "min_action")


class InductionSkill(SkillBase):
    name = "induction"
    prompt_path = "prompts/induction.md"

    MIN_SUPPORTING = 3

    def build(self, payload: SkillInput) -> SkillOutput:
        """支撑记录不足 MIN_SUPPORTING 时必须拒绝，不得硬产出假设。"""
        records = (payload.library or {}).get("records") or []
        eligible = self.eligible_groups(records)
        if not eligible:
            raise SkillRefusal(
                "没有任何阻塞点积累到 %d 条独立尝试（人工纠错不计入）" % self.MIN_SUPPORTING,
                missing=["同一阻塞点至少 %d 条尝试记录" % self.MIN_SUPPORTING])

        raw = expert_output(payload)
        if not isinstance(raw, dict) or not isinstance(raw.get("hypotheses"), list):
            raise ValueError("归纳结果必须是含 hypotheses 列表的对象")

        hypotheses = []
        for i, item in enumerate(raw["hypotheses"]):
            hypotheses.append(self.check_hypothesis(i, item, eligible))

        produced = {h["blocker"] for h in hypotheses}
        # 够门槛却没产出假设：不是错误，但要如实说出来（可能确实无从归纳）。
        unproduced = [b for b in eligible if b not in produced]

        warnings = []
        if unproduced:
            warnings.append("已达门槛但未产出假设的阻塞点：%s（需说明还缺什么）"
                            % "、".join(unproduced))
        return SkillOutput(
            payload={"hypotheses": hypotheses},
            narrative=str((payload.context or {}).get("narrative", "")),
            warnings=warnings,
        )

    def check_hypothesis(self, index: int, item: dict, eligible: dict[str, list[dict]]) -> dict:
        """把单条假设按规则过一遍；任一条不过就报违规并说明缺什么。"""
        base = "hypotheses[%d]" % index
        if not isinstance(item, dict):
            raise ValueError("%s 不是对象" % base)

        blocker = str(item.get("blocker", "")).strip()
        if not blocker:
            raise ValueError("%s.blocker 为空：假设必须挂在某个阻塞点上" % base)
        if blocker not in eligible:
            raise ValueError(
                "%s.blocker（%s）未达到 %d 条独立尝试的门槛，不得产出假设"
                % (base, blocker, self.MIN_SUPPORTING))

        group_ids = [str(r.get("id")) for r in eligible[blocker]]
        supporting = [str(s) for s in (item.get("supporting") or [])]
        if not supporting:
            raise ValueError("%s.supporting 为空：无支撑记录的假设不得产出" % base)
        stray = [s for s in supporting if s not in group_ids]
        if stray:
            raise ValueError("%s.supporting 含不属于该分组或不存在于库中的编号：%s"
                             % (base, "、".join(stray)))

        missing = [f for f in REQUIRED_FIELDS
                   if f != "supporting" and not str(item.get(f, "")).strip()]
        if missing:
            raise ValueError("%s 缺少必填项：%s（缺最小验证动作的只是评论，不是假设）"
                             % (base, "、".join(missing)))

        return {
            "blocker": blocker,
            "supporting": supporting,
            "consensus": str(item["consensus"]).strip(),
            "unverified": str(item["unverified"]).strip(),
            "unlocks": str(item["unlocks"]).strip(),
            "min_action": str(item["min_action"]).strip(),
            "status": str(item.get("status") or "未验证").strip(),
        }

    def validate(self, output: SkillOutput) -> list[Violation]:
        """payload 是假设清单而非档案，所以只查结构与编号形状。"""
        payload = output.payload
        out: list[Violation] = []
        if not isinstance(payload, dict):
            return [Violation("$", "不是对象", "dict")]
        items = payload.get("hypotheses")
        if not isinstance(items, list):
            return [Violation("hypotheses", "不是列表", "list")]
        for i, item in enumerate(items):
            base = "hypotheses[%d]" % i
            if not isinstance(item, dict):
                out.append(Violation(base, "元素不是对象", "object"))
                continue
            for key in ("blocker", "consensus", "unverified", "unlocks", "min_action"):
                if not str(item.get(key, "")).strip():
                    out.append(Violation(base + "." + key, "内容为空", "非空字符串"))
            if not item.get("supporting"):
                out.append(Violation(base + ".supporting", "无支撑记录", "至少一个 R-###"))
        return out

    def eligible_groups(self, records: list[dict]) -> dict[str, list[dict]]:
        """按阻塞点分组，只保留达到 MIN_SUPPORTING 条的分组。

        未达门槛的分组不出现——「证据不足就不产出假设」这条规则在这里落地。

        **先剔除人工纠错记录**（与网页端 `web/js/views/incubation.js` 同一口径）：
        纠错不是一次尝试，否则 2 条真实记录 + 1 条纠错就能凑满 3 条、凭空产出假设。
        """
        groups: dict[str, list[dict]] = {}
        for r in exclude_refutations(records):
            groups.setdefault(r.get("blocker", ""), []).append(r)
        return {k: v for k, v in groups.items()
                if k and len(v) >= self.MIN_SUPPORTING}
