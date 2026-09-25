"""召回打分。输出必须带命中解释：命中了哪些字段与词、各占多少权重。

定位：只做召回不做判定（判定由 LearnBuddy 专家完成）。
"""

import json
from dataclasses import dataclass

from ..contracts.models import Archive, Library

# 权重的唯一来源是 contracts/scoring.json；这个字典只是缺省镜像。
DEFAULT_WEIGHTS = {
    "blocker": 3.0,
    "attempt": 2.0,
    "observation": 1.0,
    "boundary": 1.0,
}

# 召回下限：低于此分数不返回（宁可少召回，也不硬凑——「库内无相关经验」
# 必须能被如实报告，这是用例 15-17 的判据）。
MIN_SCORE = 1.0


@dataclass
class Hit:
    """一条召回结果。explain 用于网页上的「为什么命中」，不允许为空。"""

    record_id: str
    score: float
    explain: list[str]


def _tokens(query: str) -> list[str]:  # noqa: D401
    """简易中文分词：CJK 按**重叠** 2-gram 切（无外部依赖），英文按整词。

    2026-09-22 后端审查 P1-5：原实现按「非重叠 2-gram」切（i += 2），
    `查显存` 被切成 ['查显','存']，丢单字后真关键词「显存」直接消失——
    种子库上 `recall 查显存` 命中 0 条并打印「没有区分度」，会把
    用例 15-17（"库内无相关经验须如实报告"）反向带偏：库里明明有经验却被报成没有。
    改成重叠 bigram（i += 1）后，任何 >=2 字的关键词都能被切出来。

    长度 >=3 的 CJK 串同时保留**原串**：命中解释里就能写出完整查询词，
    而不是「查显」这类碎片。单字仍被丢掉——宁少不凑的门限不动。
    """
    import re
    words = re.findall(r"[A-Za-z0-9_.\-]+|[\u4e00-\u9fff]", query)
    out: list[str] = []
    run: list[str] = []

    def flush() -> None:
        """把一段连续 CJK 收成 token：>=3 字留原串，再补全部重叠 bigram。"""
        if len(run) >= 2:
            joined = "".join(run)
            if len(run) >= 3:
                out.append(joined)
            out.extend(joined[i:i + 2] for i in range(len(joined) - 1))
        run.clear()

    for w in words:
        if re.fullmatch(r"[\u4e00-\u9fff]", w):
            run.append(w)
        else:
            flush()
            out.append(w)
    flush()
    # 丢掉单字 token：单字（如"不""跑"）在中文里几乎没有区分度，
    # 留着会让"库内无相关记录"被误报成有命中（召回宁少不凑）。
    return [t for t in out if len(t) > 1]


class RecallScorer:
    """字段加权召回。权重存在实例上，避免改类属性污染其它实例。"""

    def __init__(self) -> None:
        self.weights: dict[str, float] = dict(DEFAULT_WEIGHTS)

    def load_weights(self, path: str) -> None:
        """从 contracts/scoring.json 读取权重写入 self.weights。两端共用这一份。"""
        raw = json.loads(open(path, encoding="utf-8").read())
        self.weights = {k: float(v) for k, v in raw["weights"].items()}

    def score(self, query: str, archive: Archive) -> Hit:
        """对单条档案打分并给出命中解释。"""
        fields = {
            "blocker": archive.blocker,
            "attempt": archive.attempt,
            "observation": archive.observation,
            "boundary": archive.boundary,
        }
        tokens = _tokens(query)
        total = 0.0
        explain: list[str] = []
        for name, text in fields.items():
            if not text:
                continue
            hit_words = [t for t in tokens if t and t in text]
            if not hit_words:
                continue
            w = self.weights.get(name, 1.0)
            contrib = w * len(hit_words)
            total += contrib
            # 解释里必须给出**真正命中的词原文**：只报"命中 1 词"时，
            # 网页与专家都无从判断命中的是「显存」还是切出来的碎片「查显」。
            explain.append("%s 命中 %d 词（权重 %.1f）：%s"
                           % (name, len(hit_words), w, "、".join(hit_words)))
        return Hit(record_id=archive.id, score=total, explain=explain)

    def recall(self, query: str, library: Library, limit: int = 5) -> list[Hit]:
        """按分数降序返回候选；无相关记录时必须返回空列表，不得硬凑。"""
        hits = [self.score(query, r) for r in library.records]
        hits = [h for h in hits if h.score >= MIN_SCORE and h.explain]
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]
