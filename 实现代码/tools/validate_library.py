"""校验库文件并同步给网页：python tools/validate_library.py"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rra.contracts.validator import Validator

ROOT = Path(__file__).resolve().parents[1]


class ValidateLibraryCli:
    """命令行入口：先校验 data/ 的真源，再同步到 web/data/。"""

    def __init__(self, source: str = "data/library.seed.json",
                 target: str = "web/data/library.sample.json") -> None:
        self.source = ROOT / source
        self.target = ROOT / target

    def run(self) -> int:
        raw = json.loads(self.source.read_text(encoding="utf-8"))
        violations = Validator().validate_library(raw)
        if violations:
            print("校验未通过（%d 处）：" % len(violations))
            for v in violations:
                print("  -", v)
            return 1
        n = len(raw["records"])
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(self.source.read_text(encoding="utf-8"), encoding="utf-8")
        self.target.with_suffix('.js').write_text(
            'export const SAMPLE_LIBRARY = ' + json.dumps(raw, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
        (self.target.parent / 'scoring.json').write_text(
            (ROOT / 'contracts/scoring.json').read_text(encoding='utf-8'), encoding='utf-8')
        synced = len(json.loads(self.target.read_text(encoding="utf-8"))["records"])
        if synced != n:
            print("同步前后条数不一致：%d -> %d" % (n, synced))
            return 1
        print("校验通过（%d 条），已同步 -> %s" % (n, self.target))
        return 0


if __name__ == "__main__":
    raise SystemExit(ValidateLibraryCli().run())
