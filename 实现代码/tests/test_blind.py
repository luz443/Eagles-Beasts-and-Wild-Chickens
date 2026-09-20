"""盲测守门：未冻结读盲测用例必须抛错；冻结后可读；**冻结后改提示词必须立刻失效**。

2026-09-19 外部代码审查 P1：原实现 seal() 可传空路径（哈希为空）、读取前不复核哈希，
于是"先跑盲测、再回头调提示词"这条最典型的自欺路径完全没有被挡住。
"""

import pathlib
import tempfile
import unittest

from rra.eval.blind import BlindGuard, FreezeRecord
from rra.eval.cases import Case, CaseKind

BLIND = Case(no=3, kind=CaseKind.INSUFFICIENT_EVIDENCE, summary="盲测", expectation="拒绝", blind=True)
OPEN = Case(no=1, kind=CaseKind.INSUFFICIENT_EVIDENCE, summary="开放", expectation="拒绝", blind=False)


def seal_with(guard, content="提示词内容", **kw):
    """在临时目录里造一个真实的提示词文件再冻结（seal 现在必须给路径）。"""
    tmp = tempfile.TemporaryDirectory()
    path = pathlib.Path(tmp.name) / "prompt.md"
    path.write_text(content, encoding="utf-8")
    record = guard.seal(kw.pop("version", "v0.1"), kw.pop("by", "甲"), prompt_path=str(path), **kw)
    return tmp, path, record


class TestBlindGuard(unittest.TestCase):
    def test_read_before_freeze_raises(self):
        with self.assertRaises(PermissionError):
            BlindGuard().assert_can_read(BLIND)

    def test_open_case_always_readable(self):
        BlindGuard().assert_can_read(OPEN)

    def test_after_freeze_blind_readable(self):
        guard = BlindGuard()
        tmp, _path, _rec = seal_with(guard)
        try:
            guard.assert_can_read(BLIND)
        finally:
            tmp.cleanup()

    def test_duplicate_freeze_raises(self):
        guard = BlindGuard()
        tmp, path, _rec = seal_with(guard)
        try:
            with self.assertRaises(RuntimeError):
                guard.seal("v0.2", "乙", prompt_path=str(path))
        finally:
            tmp.cleanup()

    def test_seal_requires_prompt_path(self):
        """核心回归：没有提示词路径不许冻结（旧实现允许空哈希）。"""
        with self.assertRaises(ValueError) as ctx:
            BlindGuard().seal("v0.1", "甲")
        self.assertIn("提示词路径", str(ctx.exception))

    def test_seal_rejects_missing_file(self):
        with self.assertRaises(ValueError):
            BlindGuard().seal("v0.1", "甲", prompt_path="/no/such/prompt.md")

    def test_tampering_after_freeze_blocks_reading(self):
        """核心回归：冻结后改提示词 → 再读盲测用例必须被拦下。"""
        guard = BlindGuard()
        tmp, path, _rec = seal_with(guard)
        try:
            guard.assert_can_read(BLIND)                 # 冻结后、未改动：放行
            path.write_text("提示词内容（被改过了）", encoding="utf-8")
            with self.assertRaises(PermissionError) as ctx:
                guard.assert_can_read(BLIND)
            self.assertIn("冻结后被改动", str(ctx.exception))
        finally:
            tmp.cleanup()

    def test_freeze_without_hash_is_refused(self):
        """手工塞一条没有哈希的冻结记录：也不许读取盲测用例。"""
        guard = BlindGuard(FreezeRecord(prompt_version="v1", frozen_at="t", frozen_by="甲",
                                        prompt_hash="", prompt_path=""))
        with self.assertRaises(PermissionError):
            guard.assert_can_read(BLIND)

    def test_hash_prompt_is_stable_hex(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "p.md"
            p.write_text("固定内容", encoding="utf-8")
            h1 = FreezeRecord.hash_prompt(str(p))
            self.assertEqual(h1, FreezeRecord.hash_prompt(str(p)))
            self.assertEqual(64, len(h1))
            int(h1, 16)

    def test_seal_records_hash_and_path(self):
        guard = BlindGuard()
        tmp, path, rec = seal_with(guard, content="提示词内容")
        try:
            self.assertEqual(64, len(rec.prompt_hash))
            self.assertEqual(str(path), rec.prompt_path)
            self.assertTrue(rec.frozen_at)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
