"""死实验复活的候选规则（两端一致性护栏）。

规则真源：`src/rra/skills/resurrection.py::CANDIDATE_STATUS` 与 `candidates()`；
网页端对应实现：`web/js/util/resurrection.js`（`RESURRECTION_STATUS` 与
`isResurrectionCandidate`），由「可重试方向」视图 `web/js/views/resurrection.js` 使用。

要防的是一类**静默不一致**：同一个库，网页把某条列为"可重试候选"，
专家侧却不认（或反过来）。改任何一端都会在这里或
`web/tests/resurrection-rule-parity.mjs` 失败。
"""

import re
import unittest
from pathlib import Path

from rra.skills.resurrection import CANDIDATE_STATUS, ResurrectionSkill

ROOT = Path(__file__).resolve().parents[1]
WEB_RULE = "web/js/util/resurrection.js"


def rec(rid, blocker, status="进行中"):
    return {"id": rid, "attempt": "尝试 " + rid, "blocker": blocker, "status": status,
            "confidence": "low", "attribution": {"text": "x", "type": "assumption"}}


def abandoned(rid, blocker):
    return rec(rid, blocker, status="已放弃")


class TestCandidateRule(unittest.TestCase):
    def setUp(self):
        self.skill = ResurrectionSkill()

    def lib(self, *records):
        return {"version": "1", "records": list(records)}

    def test_only_abandoned_with_blocker(self):
        lib = self.lib(
            abandoned("R-006", "长序列训练显存不足"),
            rec("R-001", "长序列训练显存不足"),            # 进行中 → 不算
            abandoned("R-007", "   "),                      # 空白阻塞点 → 不算
            abandoned("R-008", ""),                         # 空阻塞点 → 不算
        )
        self.assertEqual([r["id"] for r in self.skill.candidates(lib)], ["R-006"])

    def test_missing_blocker_key_is_not_a_candidate(self):
        self.assertEqual(self.skill.candidates(self.lib({"id": "R-009", "status": "已放弃"})), [])

    def test_non_abandoned_statuses_excluded(self):
        for status in ("进行中", "已绕过", "已解决"):
            self.assertEqual(self.skill.candidates(self.lib(rec("R-001", "显存不足", status))), [])

    def test_order_preserved_and_input_not_mutated(self):
        records = [abandoned("R-006", "b1"), rec("R-001", "b2"), abandoned("R-007", "b3")]
        lib = self.lib(*records)
        before = [dict(r) for r in records]
        self.assertEqual([r["id"] for r in self.skill.candidates(lib)], ["R-006", "R-007"])
        self.assertEqual(records, before)

    def test_tolerates_bad_shapes(self):
        self.assertEqual(self.skill.candidates(None), [])
        self.assertEqual(self.skill.candidates({}), [])

    def test_status_literal_matches_web(self):
        """字面量必须与网页端逐字一致——这是两端规则的连接点。"""
        source = (ROOT / WEB_RULE).read_text(encoding="utf-8")
        match = re.search(r'RESURRECTION_STATUS\s*=\s*"([^"]+)"', source)
        self.assertIsNotNone(match, "网页端未声明 RESURRECTION_STATUS 常量")
        self.assertEqual(CANDIDATE_STATUS, match.group(1))

    def test_web_rule_gates_on_status_and_blocker(self):
        """网页端必须同时以 status 与 blocker 双重过滤，缺一条就会与专家侧分叉。"""
        source = (ROOT / WEB_RULE).read_text(encoding="utf-8")
        self.assertIn("record.status !== RESURRECTION_STATUS", source)
        self.assertIn("blocker.trim().length > 0", source)


class TestSeedForeshadowingStillUsable(unittest.TestCase):
    """种子数据里预留的伏笔必须真的能被这条规则捞出来（否则「可重试方向」是空页）。"""

    def test_seed_has_candidates(self):
        import json
        lib = json.loads((ROOT / "data" / "library.seed.json").read_text(encoding="utf-8"))
        got = ResurrectionSkill().candidates(lib)
        self.assertGreaterEqual(len(got), 2, "种子数据必须预留至少 2 条「已放弃且阻塞点明确」的记录")
        for r in got:
            self.assertEqual(r["status"], CANDIDATE_STATUS)
            self.assertTrue(str(r["blocker"]).strip())


if __name__ == "__main__":
    unittest.main()
