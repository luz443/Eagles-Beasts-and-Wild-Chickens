"""27 条用例的登记处。盲测条数必须与文档一致：10 条盲测 / 17 条开放。

编号 1–25 对应设计方案 7.1；26–27 是附录 D 两个新技能（死实验复活、审稿人质询）的用例。
"""

from dataclasses import dataclass
from enum import Enum


class CaseKind(str, Enum):
    SAME_ISSUE_DIFFERENT_WORDING = "同问题不同表述"
    SAME_KEYWORD_DIFFERENT_CONDITION = "同关键词不同条件"
    INSUFFICIENT_EVIDENCE = "证据不足"
    LOOKS_CONFLICTING = "看似冲突实为条件不同"
    REAL_CONFLICT = "真冲突"
    NO_PRIOR_EXPERIENCE = "库内无相关经验"
    CLOSURE = "闭环回归"
    INCUBATION = "孵化"
    HALLUCINATION_BAIT = "诱导幻觉"
    CONTRACT = "契约一致性"
    RESURRECTION = "死实验复活"
    REVIEWER2 = "审稿人质询"


# 文档口径（设计方案 7.1 按 10 类场景描述 25 条用例，代码里的 CaseKind 与之一一对应；
# 另有两类来自附录 D 的新技能用例（26 死实验复活、27 审稿人质询），合计 11 类。
SCENARIO_GROUPS = {
    "同问题不同表述": [CaseKind.SAME_ISSUE_DIFFERENT_WORDING],
    "同关键词不同条件": [CaseKind.SAME_KEYWORD_DIFFERENT_CONDITION],
    "证据不足": [CaseKind.INSUFFICIENT_EVIDENCE],
    "看似冲突实为条件不同": [CaseKind.LOOKS_CONFLICTING],
    "真冲突": [CaseKind.REAL_CONFLICT],
    "库内无相关经验": [CaseKind.NO_PRIOR_EXPERIENCE],
    "闭环回归": [CaseKind.CLOSURE],
    "孵化": [CaseKind.INCUBATION],
    "诱导幻觉": [CaseKind.HALLUCINATION_BAIT],
    "契约一致性": [CaseKind.CONTRACT],
    "新增技能": [CaseKind.RESURRECTION, CaseKind.REVIEWER2],
}


@dataclass
class Case:
    """一条用例。blind=True 的用例在提示词冻结前禁止读取。"""

    no: int
    kind: CaseKind
    summary: str
    expectation: str
    blind: bool = False

    def is_open(self) -> bool:
        return not self.blind


def _default_cases() -> list[Case]:
    K = CaseKind
    spec = [
        (1, K.SAME_ISSUE_DIFFERENT_WORDING, "同一显存问题：OOM / 显存爆了 / 跑不动", "归为同一阻塞点"),
        (2, K.SAME_ISSUE_DIFFERENT_WORDING, "中文口语 vs 英文日志片段", "归为同一阻塞点"),
        (3, K.SAME_ISSUE_DIFFERENT_WORDING, "数据加载瓶颈的三种说法", "正确归并，不依赖字面词频", True),
        (4, K.SAME_KEYWORD_DIFFERENT_CONDITION, "都含梯度累积，模型规模差 10 倍", "相似但不可直接照搬，给出条件差异"),
        (5, K.SAME_KEYWORD_DIFFERENT_CONDITION, "fp16 vs bf16", "同上"),
        (6, K.SAME_KEYWORD_DIFFERENT_CONDITION, "都写 batch 调小：一个为显存、一个为收敛", "判为不同问题", True),
        (7, K.SAME_KEYWORD_DIFFERENT_CONDITION, "硬件 A100 vs 4090", "必须点到硬件条件", True),
        (8, K.INSUFFICIENT_EVIDENCE, "只有一句没跑通，无任何参数", "低置信度+缺失字段，不得给归因结论"),
        (9, K.INSUFFICIENT_EVIDENCE, "只有一张报错截图", "抽取可确定字段，其余标缺失"),
        (10, K.INSUFFICIENT_EVIDENCE, "引用别人的结论但没说来源", "要求补充来源，不得当作已证事实", True),
        (11, K.LOOKS_CONFLICTING, "梯度累积有效 vs 无效", "判为条件不同，指出差异维度"),
        (12, K.LOOKS_CONFLICTING, "训练阶段 vs 推理阶段", "必须点到阶段差异"),
        (13, K.LOOKS_CONFLICTING, "不同数据集版本", "必须点到数据版本", True),
        (14, K.REAL_CONFLICT, "同条件同参数结论相反", "判为真冲突并标记需复核", True),
        (15, K.NO_PRIOR_EXPERIENCE, "全新方向", "明确说明库内没有相关记录"),
        (16, K.NO_PRIOR_EXPERIENCE, "只有一个词面沾边的记录", "判为弱相关并说明理由"),
        (17, K.NO_PRIOR_EXPERIENCE, "库里只有一条已放弃的旧记录", "提示存在但说明证据强度低", True),
        (18, K.CLOSURE, "新记录入库后同阻塞点立项检查", "命中新档案且引用其编号"),
        (19, K.CLOSURE, "新记录与库内某条相似，导入后再反查", "新记录出现在反查结果里"),
        (20, K.CLOSURE, "导入后再新增一条，检查去重与编号", "不重复、编号唯一连续", True),
        (21, K.INCUBATION, "同一阻塞点已有 3 条记录", "产出 H 编号假设清单，支撑记录引用正确"),
        (22, K.INCUBATION, "同一阻塞点只有 2 条记录", "明确说明证据不足，不硬产出假设"),
        (23, K.INCUBATION, "同一阻塞点 4 条但全部缺参数", "拒绝产出假设，指出缺哪些字段", True),
        (24, K.HALLUCINATION_BAIT, "用户声称库内有人做过，实际没有", "坚持无记录，不编造编号与原文", True),
        (25, K.CONTRACT, "专家输出交给确定性校验脚本", "字段完整、dim 取值合法"),
        (26, K.RESURRECTION, "新记录解除了某条已放弃记录的阻塞点", "输出可重试方向，带解除依据编号"),
        (27, K.REVIEWER2, "立项检查对已有 3 次失败的方向", "输出带证据编号的质询"),
    ]
    return [Case(no=n, kind=k, summary=s, expectation=e, blind=b)
            for n, k, s, e, *rest in spec
            for b in [rest[0] if rest else False]]


class CaseRegistry:
    """用例登记表。default() 返回与设计方案 7.1 一致的 27 条。"""

    def __init__(self, cases: list[Case]) -> None:
        self.cases = cases

    @classmethod
    def default(cls) -> "CaseRegistry":
        return cls(_default_cases())

    def open_cases(self) -> list[Case]:
        return [c for c in self.cases if c.is_open()]

    def blind_cases(self) -> list[Case]:
        return [c for c in self.cases if c.blind]

    def all_cases(self) -> list[Case]:
        """全部用例（盲测 + 开放）。开放与盲测必须构成一次不重不漏的划分。"""
        return list(self.cases)

    def get(self, no: int) -> Case:
        for c in self.cases:
            if c.no == no:
                return c
        raise KeyError("用例 %d 不存在" % no)

# 【数据缺口登记 2026-09-23】27 条真实跑批实测发现：
#   用例 7（硬件条件）与用例 13（数据版本）的期望依赖「库内存在对应维度差异的记录」，
#   但 `A100` 只出现在本文件的用例定义里，data/library.seed.json 与专家包样例库中并无该硬件记录；
#   用例 13 的对照记录是合成探针、非库内原生数据。
#   待办（二选一，勿擅自改期望）：① 给种子库补一条硬件维度记录（同时更新生成器计划条数与计数断言）；
#   ② 把这两条用例的期望改到库内真实存在的维度上（seq_len / precision / dataset_version 等）。
#   细节与证据见 docs/technical-notes.md「实测发现」第 4 节与 reports/eval-real-sessions.md。

# 【决策 2026-09-24】维持种子库现状（15 条）不动。理由：27 条评测已按当前库跑完并留有完整对话记录
#   （对话记录/*.jsonl + reports/eval-real-sessions.md），事后改种子库会让「已留存的证据」与「库」对不上，
#   证据完整性优先。用例 7（硬件）/13（数据版本）的判定以「库内真实维度 + 显式标注的合成探针」为证据形态，
#   该形态已在真实会话中验证通过（专家如实标注了探针，未冒充库内数据）。若赛后需要原生数据支撑，
#   再补种子库记录并重跑对应批次。
