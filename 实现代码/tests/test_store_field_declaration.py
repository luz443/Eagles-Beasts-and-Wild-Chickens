"""P2-12：MergeReport.renumbered 的字段声明必须干净。

原写法是 `renumbered: dict[str, field_factory := dict] = field(...) if False else field(...)`：
- 注解被求值成 `dict[str, dict]`（多出来的 `field_factory := dict` 只是顺手泄漏了一个类属性），
- 值那边挂着一条永远不会走到的 `if False else`。

它今天不炸，但既误导读者（看起来像是条件默认值），也让类型注解说的不是真话。
red 点：注解不等于 `dict[str, str]`；green 点：注解干净、源码里不再有残留写法。
"""

import unittest
from pathlib import Path

from rra.library.store import MergeReport

ROOT = Path(__file__).resolve().parents[1]


class TestMergeReportDeclaration(unittest.TestCase):
    def test_renumbered_annotation_is_plain_str_mapping(self):
        self.assertEqual(dict[str, str], MergeReport.__annotations__["renumbered"])

    def test_source_has_no_leftover_expression(self):
        src = (ROOT / "src" / "rra" / "library" / "store.py").read_text(encoding="utf-8")
        self.assertNotIn("field_factory", src)
        self.assertNotIn("if False else", src)

    def test_renumbered_still_defaults_to_empty_dict(self):
        self.assertEqual({}, MergeReport().renumbered)


if __name__ == "__main__":
    unittest.main()
