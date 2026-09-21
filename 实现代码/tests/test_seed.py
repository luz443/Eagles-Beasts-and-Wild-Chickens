"""种子数据生成器：伏笔必须埋够，来源必须标注，产出必须过契约校验。

种子库同时是**两个第一梯队创新点的演示材料**（附表 D.1）：
「可重试方向」（S2）需要至少一条带 `resurrection.unblocks` 的记录，
立项检查的主动质询（D5）需要至少一条带 `challenge.challenges` 的记录。
这两条在这里被断言，`SeedGenerator.check_plan` 也会自检——否则界面上只有空态。
"""

import unittest

from rra.contracts.validator import Validator
from rra.seed.generator import SeedGenerator, SeedPlan

TOTAL = 15


class TestSeedGenerator(unittest.TestCase):
    def test_generates_planned_count(self):
        gen = SeedGenerator(SeedPlan(total=TOTAL))
        records = gen.generate()
        self.assertEqual(TOTAL, len(records))

    def test_all_records_valid(self):
        """每条种子记录都必须能通过契约校验。"""
        gen = SeedGenerator(SeedPlan(total=TOTAL))
        v = Validator()
        for rec in gen.generate():
            vs = v.validate_archive(rec)
            self.assertEqual([], vs, [str(x) for x in vs])

    def test_library_level_valid(self):
        """整库校验（含解除依据的引用与引文可复核）也必须过——它比单档案校验严一层。"""
        gen = SeedGenerator(SeedPlan(total=TOTAL))
        vs = Validator().validate_library({"version": "1", "records": gen.generate()})
        self.assertEqual([], vs, [str(x) for x in vs])

    def test_foreshadowing_present(self):
        """死实验复活的伏笔：已放弃且阻塞点明确的记录必须 >= 2 条。"""
        gen = SeedGenerator(SeedPlan(total=TOTAL))
        recs = gen.generate()
        abandoned = [r for r in recs if r.get("status") == "已放弃" and r.get("blocker", "").strip()]
        self.assertGreaterEqual(len(abandoned), 2)

    def test_same_blocker_cluster_exists(self):
        """同一阻塞点至少 3 条，供失败地图与孵化清单使用。"""
        gen = SeedGenerator(SeedPlan(total=TOTAL))
        recs = gen.generate()
        blockers = {}
        for r in recs:
            blockers[r["blocker"]] = blockers.get(r["blocker"], 0) + 1
        self.assertTrue(any(v >= 3 for v in blockers.values()), blockers)

    def test_source_marked_simulation(self):
        gen = SeedGenerator(SeedPlan(total=TOTAL))
        for rec in gen.generate():
            self.assertEqual("模拟", rec["provenance"]["source"])

    def test_unblock_demo_data_exists(self):
        """S2：必须有一条记录声明解除了某条已放弃记录的阻塞点，且被解除的那条确实存在。"""
        recs = SeedGenerator(SeedPlan(total=TOTAL)).generate()
        by_id = {r["id"]: r for r in recs}
        unblocks = [(r["id"], u) for r in recs for u in (r.get("resurrection") or {}).get("unblocks", [])]
        self.assertTrue(unblocks, "没有任何记录带 resurrection.unblocks——可重试方向只有空态")
        for owner, u in unblocks:
            self.assertIn(u["record"], by_id, "被解除的档案不在种子库里")
            target = by_id[u["record"]]
            self.assertEqual("已放弃", target["status"], "被解除的那条应当是「已放弃」——否则不是复活")
            self.assertTrue(str(target["blocker"]).strip(), "被解除的那条必须有明确阻塞点")
            # 解除依据指向的档案也要在库里（引文可复核由整库校验负责）
            self.assertIn(u["basis"], by_id)

    def test_challenge_demo_data_exists(self):
        """D5：必须有一条记录带专家质询，且每条质询都有证据编号。"""
        recs = SeedGenerator(SeedPlan(total=TOTAL)).generate()
        challenges = [c for r in recs for c in (r.get("challenge") or {}).get("challenges", [])]
        self.assertTrue(challenges, "没有任何记录带 challenge.challenges——立项检查看不到质询")
        for c in challenges:
            self.assertTrue(c["evidence_ids"], "无证据编号的质询不得进库")
            for one in c["evidence_ids"]:
                self.assertRegex(one, r"^R-[0-9]{3,}$")

    def test_check_plan_reports_no_issues(self):
        gen = SeedGenerator(SeedPlan(total=TOTAL))
        recs = [r for r in gen.generate()]
        self.assertEqual([], gen.check_plan(recs))

    def test_check_plan_catches_missing_demo_data(self):
        """自检本身要能被证伪：把两个创新点的材料去掉，必须报出来。"""
        gen = SeedGenerator(SeedPlan(total=TOTAL))
        recs = gen.generate()
        for r in recs:
            r.pop("resurrection", None)
            r.pop("challenge", None)
        issues = gen.check_plan(recs)
        self.assertTrue(any("可重试方向" in i for i in issues), issues)
        self.assertTrue(any("主动质询" in i for i in issues), issues)


if __name__ == "__main__":
    unittest.main()
