"""评测与提示词的**交付完整性**：冻结的东西必须真的冻住了，跑出来的东西必须真的跑过。

这套测试盯的是「过程证据」而不是功能：
- 六份技能提示词是否都已定稿（不是 `draft`）、是否都进了冻结记录；
- 冻结记录里的哈希是否与当前文件**逐份**一致（只对一份等于放行另外五份）；
- 用这份冻结记录，盲测用例**确实**可以读取（守门不是摆设）；
- 没有冻结记录时，盲测用例**确实**读不了（纪律反向也成立）。

为什么值得单独一个文件：`reports/eval-log.md` 是 PPT 第 8 页的唯一数据来源，
而它只能由「冻结之后跑出来的真实结果」生成。提示词冻不住，这条链就是假的。
提示词确实要改时，正确的做法是：改完重跑
`python tools/run_eval.py --create-freeze reports/prompt-freeze.json --prompts-dir prompts ...`，
并明确知道**此前的盲测结果作废**。
"""

import json
import re
import unittest
from pathlib import Path

from rra.eval.blind import BlindGuard, FreezeRecord
from rra.eval.cases import CaseRegistry, CaseKind

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts"
FREEZE = ROOT / "reports" / "prompt-freeze.json"
VERSION = "v1.0-frozen"

PROMPT_NAMES = ("extract.md", "reverse_lookup.md", "condition_compare.md",
                "induction.md", "resurrection.md", "reviewer2.md")

# 四条全局禁令：无论哪个技能，这四条都不能在改写提示词时被删掉。
GLOBAL_BANS = ("编号", "assumption", "失败次数", "证据不足")


def load_freeze() -> FreezeRecord:
    data = json.loads(FREEZE.read_text(encoding="utf-8"))
    return FreezeRecord(
        prompt_version=data.get("prompt_version", ""),
        frozen_at=data.get("frozen_at", ""),
        frozen_by=data.get("frozen_by", ""),
        prompt_hash=data.get("prompt_hash", ""),
        prompt_path=data.get("prompt_path", ""),
        prompt_hashes=dict(data.get("prompt_hashes") or {}),
    )


class TestPromptsAreFinal(unittest.TestCase):
    def test_all_six_prompts_exist(self):
        for name in PROMPT_NAMES:
            self.assertTrue((PROMPTS / name).is_file(), "缺提示词：%s" % name)

    def test_version_anchor_is_frozen(self):
        """版本行是唯一的哈希锚点，必须在每一份里显式写明，且不能还是 draft。"""
        for name in PROMPT_NAMES:
            text = (PROMPTS / name).read_text(encoding="utf-8")
            self.assertNotIn("draft", text.lower(), "%s 仍是草稿" % name)
            self.assertIn("**版本：%s**" % VERSION, text, "%s 缺冻结版本行" % name)

    def test_global_bans_survive_in_every_prompt(self):
        """四条全局禁令不得在改写中丢失——它们是本作品判断力的底线。"""
        for name in PROMPT_NAMES:
            text = (PROMPTS / name).read_text(encoding="utf-8")
            missing = [b for b in GLOBAL_BANS if b not in text]
            self.assertEqual([], missing, "%s 丢了禁令：%s" % (name, missing))

    def test_every_prompt_has_refusal_and_selfcheck(self):
        """六节结构里最容易被省掉的两节：拒绝条件与自检清单。"""
        for name in PROMPT_NAMES:
            text = (PROMPTS / name).read_text(encoding="utf-8")
            self.assertIn("拒绝", text, "%s 没有拒绝条件" % name)
            self.assertIn("自检", text, "%s 没有自检清单" % name)

    def test_prompts_do_not_carry_cli_commands(self):
        """提示词只写判定规则；命令属于 SKILL.md（提示词参与哈希，命令会频繁变）。"""
        for name in PROMPT_NAMES:
            text = (PROMPTS / name).read_text(encoding="utf-8")
            self.assertNotIn("rra_cli.py", text, "%s 把 CLI 命令写进了提示词" % name)


class TestFreezeRecordIsHonest(unittest.TestCase):
    def test_freeze_file_exists_and_is_labeled(self):
        self.assertTrue(FREEZE.is_file(),
                        "缺少 %s：盲测无法进行。先跑 tools/run_eval.py --create-freeze" % FREEZE)
        rec = load_freeze()
        self.assertEqual(VERSION, rec.prompt_version)
        self.assertTrue(rec.frozen_by.strip(), "冻结记录必须写明冻结人")
        self.assertTrue(re.match(r"^\d{4}-\d{2}-\d{2}T", rec.frozen_at),
                        "冻结时间格式异常：%r" % rec.frozen_at)

    def test_freeze_covers_all_six_prompts(self):
        """只冻结一份 = 放行另外五份。这里要求六份都在。"""
        rec = load_freeze()
        self.assertEqual(6, len(rec.prompt_hashes), "冻结记录应覆盖六份提示词：%s"
                         % sorted(rec.prompt_hashes))
        for name in PROMPT_NAMES:
            hit = [k for k in rec.prompt_hashes if k.endswith("/" + name) or k == name]
            self.assertTrue(hit, "冻结记录里没有 %s" % name)

    def test_each_stored_hash_matches_current_file(self):
        """逐份复核：任何一份被改动，都必须在这里先失败，而不是等盲测跑到一半。"""
        rec = load_freeze()
        for path, stored in sorted(rec.prompt_hashes.items()):
            self.assertTrue((ROOT / path).is_file(), "冻结记录指向的文件不存在：%s" % path)
            self.assertEqual(stored, FreezeRecord.hash_prompt(str(ROOT / path)),
                             "%s 在冻结后被改动——盲测结果作废。"
                             "要么改回去，要么重新冻结并重跑盲测。" % path)

    def test_combined_hash_matches_parts(self):
        rec = load_freeze()
        self.assertEqual(rec.prompt_hash, FreezeRecord.combine(rec.prompt_hashes))

    def test_paths_are_posix_style(self):
        """冻结记录要能被别的机器复核，路径里不能出现 Windows 反斜杠。"""
        for path in load_freeze().prompt_hashes:
            self.assertNotIn("\\", path, "冻结记录里的路径含反斜杠：%s" % path)


class TestBlindGateIsReal(unittest.TestCase):
    def test_real_freeze_unlocks_blind_suite(self):
        """用仓库里的真实冻结记录，盲测用例必须读得到（守门不是摆设）。"""
        guard = BlindGuard(load_freeze())
        blind = [c for c in CaseRegistry.default().all_cases() if c.blind]
        self.assertTrue(blind, "用例集中没有盲测用例")
        for case in blind:
            guard.assert_can_read(case)

    def test_without_freeze_blind_suite_is_locked(self):
        """反向也成立：没有冻结记录时，一条盲测用例都不许读。"""
        blind = [c for c in CaseRegistry.default().all_cases() if c.blind]
        for case in blind:
            with self.assertRaises(PermissionError):
                BlindGuard().assert_can_read(case)


class TestCaseRegistryIntegrity(unittest.TestCase):
    def test_blind_and_open_partition_the_suite(self):
        reg = CaseRegistry.default()
        blind = reg.blind_cases()
        open_ = reg.open_cases()
        self.assertEqual(len(reg.all_cases()), len(blind) + len(open_))
        self.assertFalse({c.no for c in blind} & {c.no for c in open_}, "盲测与开放用例有重叠")

    def test_every_case_kind_is_exercised_somewhere(self):
        """每种用例类型至少要有一条用例，否则规则表里会有「从来没被跑过」的分支。"""
        reg = CaseRegistry.default()
        used = {c.kind for c in reg.all_cases()}
        self.assertEqual(set(CaseKind) - used, set(), "没有用例覆盖的类型：%s"
                         % sorted(k.name for k in set(CaseKind) - used))

    def test_every_case_has_readable_fields(self):
        for case in CaseRegistry.default().all_cases():
            self.assertTrue(str(case.summary).strip(), "用例 %d 缺摘要" % case.no)
            self.assertTrue(str(case.expectation).strip(), "用例 %d 缺期望行为" % case.no)


if __name__ == "__main__":
    unittest.main()
