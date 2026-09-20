"""畸形嵌套结构必须报违规，而不是抛异常（2026-09-19 外部审查 P1）。

审查给出的最小输入是 `{"id": "R-001", "links": [null]}`：原实现在 `link.get()` 上抛
AttributeError，网页端则抛 TypeError。校验器的契约是「给出 路径 + 原因 + 期望」，
不是「把调用方打崩」——畸形输入恰恰是最需要它稳定的时候。

补充：审查只点了 `validate_archive`，实测 `validate_library` 里同样有这条路径（它也会
遍历 links / evidence_refs），所以两层都要覆盖。
"""

import unittest

from rra.contracts.validator import Validator


def base_record(**over):
    rec = {
        "id": "R-001", "attempt": "a", "expectation": "e", "observation": "o",
        "blocker": "b", "attribution": {"text": "t", "type": "assumption"},
        "boundary": "bd", "confidence": "low", "status": "进行中",
        "provenance": {"author": "u", "date": "2026-09-19", "source": "模拟"},
    }
    rec.update(over)
    return rec


LINK = {"target": "R-002", "relation": "相似", "same": [], "diff": [], "transferable": ""}


class TestNestedShapeRobustness(unittest.TestCase):
    def setUp(self):
        self.v = Validator()

    CASES = [
        ("links 元素为 null", {"links": [None]}, "links[0]"),
        ("links 不是列表", {"links": "bad"}, "links"),
        ("same 元素为 null", {"links": [dict(LINK, same=[None])]}, "links[0].same[0]"),
        ("same 不是列表", {"links": [dict(LINK, same="bad")]}, "links[0].same"),
        ("diff 元素为 null", {"links": [dict(LINK, diff=[None])]}, "links[0].diff[0]"),
        ("evidence_refs 元素为 null", {"evidence_refs": [None]}, "evidence_refs[0]"),
        ("evidence_refs 不是列表", {"evidence_refs": {"record": "R-001"}}, "evidence_refs"),
        ("artifacts 不是列表", {"artifacts": "runs/x.log"}, "artifacts"),
        ("missing_info 不是列表", {"missing_info": 3}, "missing_info"),
    ]

    def test_archive_reports_paths_instead_of_raising(self):
        for name, patch, expected_path in self.CASES:
            with self.subTest(name):
                vs = self.v.validate_archive(base_record(**patch))
                self.assertIn(expected_path, [x.path for x in vs],
                              "%s 未报出路径 %s" % (name, expected_path))

    def test_library_layer_also_survives(self):
        """整库层也不能崩（审查未点到，但同一段逻辑在这里也有）。"""
        lib = {"version": "0.1.0", "generated_at": "2026-09-19",
               "records": [base_record(links=[None]), base_record(id="R-002")]}
        vs = self.v.validate_library(lib)
        self.assertIn("records[0].links[0]", [x.path for x in vs])

    def test_violations_carry_all_three_parts(self):
        vs = self.v.validate_archive(base_record(links=[None]))
        for v in vs:
            text = str(v)
            self.assertTrue(v.path and v.reason and v.expected, text)
            self.assertIn("期望", text)

    def test_well_formed_input_still_clean(self):
        self.assertEqual(self.v.validate_archive(base_record()), [])


if __name__ == "__main__":
    unittest.main()
