"""导出：档案报告带编号与证据引用；避坑清单按阻塞点聚合。"""

import unittest

from rra.export.report import MarkdownExporter


REC = {
    "id": "R-005", "attempt": "沿用 R-004 配置跑 4096", "expectation": "跑通",
    "observation": "OOM", "blocker": "长序列训练显存不足",
    "attribution": {"text": "累积不省激活", "type": "observed"},
    "boundary": "4096 时成立", "confidence": "medium", "status": "进行中",
    "evidence_refs": [{"record": "R-004", "quote": "显存稳定在 21G"}],
    "provenance": {"author": "模拟·王同学", "date": "2026-08-02", "source": "模拟"},
}


class TestExport(unittest.TestCase):
    def test_archive_report_has_id_and_quote(self):
        md = MarkdownExporter().archive_report(REC)
        self.assertIn("R-005", md)
        self.assertIn("显存稳定在 21G", md)
        self.assertIn("假设" if REC["attribution"]["type"] == "assumption" else "已观察", md)

    def test_blocker_digest_groups_by_blocker(self):
        recs = [dict(REC), dict(REC, id="R-001")]
        md = MarkdownExporter().blocker_digest(recs)
        self.assertIn("长序列训练显存不足", md)
        self.assertIn("R-001", md)
        self.assertIn("R-005", md)


if __name__ == "__main__":
    unittest.main()
