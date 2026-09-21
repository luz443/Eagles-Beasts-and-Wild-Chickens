"""专家镜像一致性：仓库镜像 `expert/<name>/` 里的**生成物**必须与仓库逐字节相同。

为什么需要它：镜像里的 `bin/rra`、`bin/samples`、`skills/*/references/prompt.md` 都是
「由仓库生成、再复制进去」的副本。`tools/sync_expert.py --check` 只比对引擎摘要与 CLI，
**没有盯提示词与契约的副本**——于是最该被锁住的那部分（判断规则）可以静默漂移：
仓库里把 `prompts/induction.md` 的门槛从 3 改成 2，镜像里还是 3，
两边测试各自都是绿的，而专家实际用的是旧规则。

这套测试就是补这个缺口。改完仓库记得跑 `python tools/sync_expert.py --mirror-only`。
"""

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIRROR = ROOT / "expert" / "research-retro-assistant"

SKILL_OF_PROMPT = {
    "extract.md": "extract-record",
    "reverse_lookup.md": "reverse-lookup",
    "condition_compare.md": "condition-compare",
    "induction.md": "induction",
    "resurrection.md": "resurrection",
    "reviewer2.md": "reviewer2",
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class TestExpertMirror(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MIRROR.is_dir(), "仓库镜像不存在：%s" % MIRROR)

    def assert_same(self, src: Path, dst: Path):
        self.assertTrue(dst.is_file(), "镜像里缺文件：%s" % dst)
        self.assertEqual(sha256_of(src), sha256_of(dst),
                         "生成物与仓库不一致：%s → %s（跑一次 sync_expert.py --mirror-only）"
                         % (src.relative_to(ROOT), dst.relative_to(ROOT)))

    def test_prompts_are_mirrored_byte_for_byte(self):
        """六份提示词是判断规则的唯一真源，镜像必须逐字节一致。"""
        prompts = sorted(p.name for p in (ROOT / "prompts").glob("*.md"))
        self.assertEqual(sorted(SKILL_OF_PROMPT), prompts,
                         "提示词集合与映射表不一致（新增提示词要同时登记 SKILL_OF_PROMPT）")
        for prompt, skill in SKILL_OF_PROMPT.items():
            self.assert_same(ROOT / "prompts" / prompt,
                             MIRROR / "skills" / skill / "references" / "prompt.md")

    def test_prompt_version_is_frozen(self):
        """冻结版本号必须写在每一份提示词里，且不能还是 draft。"""
        for name in SKILL_OF_PROMPT:
            text = (ROOT / "prompts" / name).read_text(encoding="utf-8")
            self.assertNotIn("draft", text.lower(), "%s 仍是草稿版本" % name)
            self.assertIn("v1.0-frozen", text, "%s 缺少冻结版本号" % name)

    def test_engine_is_mirrored(self):
        """src/rra 下的每个 .py 都要在镜像 bin/rra 里有同内容副本（且镜像不得多出文件）。"""
        src_files = sorted(p for p in (ROOT / "src" / "rra").rglob("*.py")
                           if "__pycache__" not in p.parts)
        self.assertTrue(src_files)
        for src in src_files:
            self.assert_same(src, MIRROR / "bin" / src.relative_to(ROOT / "src"))
        mirror_files = {p.relative_to(MIRROR / "bin" / "rra")
                        for p in (MIRROR / "bin" / "rra").rglob("*")
                        if p.is_file() and p.suffix == ".py" and "__pycache__" not in p.parts}
        expected = {p.relative_to(ROOT / "src" / "rra") for p in src_files}
        self.assertEqual(expected, mirror_files, "镜像 bin/rra 里有仓库已删除的旧文件")

    def test_cli_and_samples_are_mirrored(self):
        self.assert_same(ROOT / "tools" / "rra_cli.py", MIRROR / "bin" / "rra_cli.py")
        self.assert_same(ROOT / "data" / "library.seed.json",
                         MIRROR / "bin" / "samples" / "library.seed.json")
        for f in sorted((ROOT / "contracts").glob("*.json")):
            self.assert_same(f, MIRROR / "bin" / "samples" / "contracts" / f.name)

    def test_contracts_are_mirrored_into_each_skill(self):
        """每个技能的 references 里都带一份契约，必须与仓库同步（否则技能按旧契约校验）。"""
        for skill in SKILL_OF_PROMPT.values():
            ref = MIRROR / "skills" / skill / "references"
            for name in ("record.schema.json", "dim.json"):
                self.assert_same(ROOT / "contracts" / name, ref / name)

    def test_record_format_doc_is_mirrored_where_used(self):
        doc = ROOT / "docs" / "record-format.md"
        for skill in ("extract-record", "reviewer2"):
            self.assert_same(doc, MIRROR / "skills" / skill / "references" / "record-format.md")

    def test_sync_manifest_matches(self):
        manifest = json.loads((MIRROR / "bin" / "SYNC.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["engine_digest"], manifest["repo_engine_digest"],
                         "SYNC.json 里的引擎摘要不一致")
        self.assertEqual(manifest["cli_digest"], manifest["repo_cli_digest"],
                         "SYNC.json 里的 CLI 摘要不一致")


if __name__ == "__main__":
    unittest.main()
