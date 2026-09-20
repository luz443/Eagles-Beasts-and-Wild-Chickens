"""生成种子数据：python tools/make_seed.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rra.contracts.models import Archive, Library
from rra.library.store import LibraryStore
from rra.seed.generator import SeedGenerator


class MakeSeedCli:
    """命令行入口。生成逻辑在 rra.seed.generator 里。"""

    def __init__(self, out_path: str = "data/library.seed.json") -> None:
        self.out_path = Path(__file__).resolve().parents[1] / out_path

    def run(self) -> int:
        gen = SeedGenerator()
        records = gen.generate()
        issues = gen.check_plan(records)
        if issues:
            print("种子数据自检未通过：")
            for i in issues:
                print("  -", i)
            return 1
        archives = [Archive.from_dict(r) for r in records]
        store = LibraryStore(self.out_path)
        store.save(Library(version="0.1.0", generated_at="2026-09-19", records=archives))
        print("已生成 %d 条种子档案 -> %s" % (len(records), self.out_path))
        return 0


if __name__ == "__main__":
    raise SystemExit(MakeSeedCli().run())
