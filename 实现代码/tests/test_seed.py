"""种子数据生成器：伏笔必须埋够，来源必须标注，产出必须过契约校验。"""

import unittest

from rra.contracts.validator import Validator
from rra.seed.generator import SeedGenerator, SeedPlan


class TestSeedGenerator(unittest.TestCase):
    def test_generates_planned_count(self):
        gen = SeedGenerator(SeedPlan(total=14))
        records = gen.generate()
        self.assertEqual(14, len(records))

    def test_all_records_valid(self):
        """每条种子记录都必须能通过契约校验。"""
        gen = SeedGenerator(SeedPlan(total=14))
        v = Validator()
        for rec in gen.generate():
            vs = v.validate_archive(rec)
            self.assertEqual([], vs, [str(x) for x in vs])

    def test_foreshadowing_present(self):
        """死实验复活的伏笔：已放弃且阻塞点明确的记录必须 >= 2 条。"""
        gen = SeedGenerator(SeedPlan(total=14))
        recs = gen.generate()
        abandoned = [r for r in recs if r.get("status") == "已放弃" and r.get("blocker", "").strip()]
        self.assertGreaterEqual(len(abandoned), 2)

    def test_same_blocker_cluster_exists(self):
        """同一阻塞点至少 3 条，供失败地图与孵化清单使用。"""
        gen = SeedGenerator(SeedPlan(total=14))
        recs = gen.generate()
        blockers = {}
        for r in recs:
            blockers[r["blocker"]] = blockers.get(r["blocker"], 0) + 1
        self.assertTrue(any(v >= 3 for v in blockers.values()), blockers)

    def test_source_marked_simulation(self):
        gen = SeedGenerator(SeedPlan(total=14))
        for rec in gen.generate():
            self.assertEqual("模拟", rec["provenance"]["source"])

    def test_check_plan_reports_no_issues(self):
        gen = SeedGenerator(SeedPlan(total=14))
        recs = [r for r in gen.generate()]
        self.assertEqual([], gen.check_plan(recs))


if __name__ == "__main__":
    unittest.main()
