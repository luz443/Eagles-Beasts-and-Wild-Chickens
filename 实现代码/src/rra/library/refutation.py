"""人工纠错记录（网页端「反驳」按钮写入）的识别规则——两端唯一真源。

背景：网页端的反驳会把一条 `attempt = "对 R-00X 的人工纠错"` 的记录写进库里
（`web/js/refute.js`）。这类记录**不是一次尝试**，因此不能用来凑归纳门槛。

为什么必须收口到一个函数：2026-09-19 实测发现两端口径不一致——
网页 `web/js/views/incubation.js` 会先 `filter(r => !attempt.includes("人工纠错"))`
再按阻塞点分组，而专家侧（Python）原本没有这个过滤。后果很具体：
**同一个库，网页说「还没积累到 3 条」，专家侧却认为够 3 条并产出假设**。

规则（与 JS 端逐字一致）：`attempt` 字段包含「人工纠错」即为纠错记录。
之所以用「包含」而不是「等于」，是为了兼容历史数据与人工手写的带前缀写法。

改动本规则时必须同时改 JS 端（`refute.js` / `incubation.js`）并跑
`tests/test_refutation_filter.py`，否则一致性会被静默破坏。
"""

MARKER = "人工纠错"


def is_refutation(record: object) -> bool:
    """该记录是否为「人工纠错」记录。非字典 / 缺字段一律按「不是」处理，不抛错。"""
    if not isinstance(record, dict):
        return False
    attempt = record.get("attempt")
    if not isinstance(attempt, str):
        return False
    return MARKER in attempt


def exclude_refutations(records: list) -> list:
    """过滤掉纠错记录，保持原顺序（返回新列表，不改入参）。"""
    if not isinstance(records, list):
        return []
    return [r for r in records if not is_refutation(r)]
