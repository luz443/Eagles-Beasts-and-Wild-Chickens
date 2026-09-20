"""技能基座：证据不足即拒绝；输出未过校验即拒绝；不留半成品。"""

import unittest

from rra.skills.base import SkillBase, SkillInput, SkillOutput, SkillRefusal
from rra.contracts.validator import Validator


class FakeSkill(SkillBase):
    name = "fake"

    def build(self, payload):
        if payload.raw_text.strip() == "一句话":
            raise SkillRefusal("证据不足", missing=["参数", "日志"])
        return SkillOutput(payload={"ok": True}, narrative="完成")


class TestSkillBase(unittest.TestCase):
    def test_refuses_without_evidence(self):
        with self.assertRaises(SkillRefusal) as ctx:
            FakeSkill().run(SkillInput(raw_text="一句话"))
        self.assertIn("参数", ctx.exception.missing)

    def test_run_returns_output_when_valid(self):
        out = FakeSkill().run(SkillInput(raw_text="充足的输入"))
        self.assertTrue(out.payload["ok"])

    def test_validate_delegates_to_validator(self):
        skill = FakeSkill()
        self.assertIsInstance(skill.validator, Validator)


if __name__ == "__main__":
    unittest.main()
