"""缓存：键必须稳定；关闭时不得写盘；命中不消耗调用。"""

import tempfile, unittest
from pathlib import Path

from rra.skills.cache import CacheEntry, SkillCache


class TestSkillCache(unittest.TestCase):
    def test_key_is_stable(self):
        c = SkillCache(path=None)
        self.assertEqual(c.key_of("a", "b"), c.key_of("a", "b"))

    def test_key_differs_on_input(self):
        c = SkillCache(path=None)
        self.assertNotEqual(c.key_of("a", "b"), c.key_of("a", "c"))

    def test_disabled_cache_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "cache.json"
            c = SkillCache(path=p, enabled=False)
            c.put(CacheEntry(key="k", output={"x": 1}))
            self.assertFalse(p.exists())

    def test_enabled_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "cache.json"
            c = SkillCache(path=p, enabled=True)
            c.put(CacheEntry(key="k", output={"x": 1}, prompt_version="v0.1"))
            got = SkillCache(path=p, enabled=True).get("k")
            self.assertIsNotNone(got)
            self.assertEqual({"x": 1}, got.output)
            self.assertEqual(1, c.stats()["entries"])

    def test_miss_returns_none(self):
        self.assertIsNone(SkillCache(path=None).get("nope"))


if __name__ == "__main__":
    unittest.main()
