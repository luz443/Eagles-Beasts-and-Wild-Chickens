"""库的读写与导入合并。编号冲突时重编号并记录 remap_from，不静默覆盖。"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..contracts.models import Archive, Library
from ..contracts.validator import Validator
from .dedup import Deduplicator


@dataclass
class MergeReport:
    """导入结果：新增、重复、重编号各自的条数与明细。"""

    added: list[str] = field(default_factory=list)
    duplicated: list[str] = field(default_factory=list)
    renumbered: dict[str, field_factory := dict] = field(default_factory=dict) if False else field(default_factory=dict)
    violations: list[str] = field(default_factory=list)


class LibraryStore:
    """经验库的存取。路径由调用方给出，不硬编码。"""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.dedup = Deduplicator()
        self.validator = Validator()

    def load(self) -> Library:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        vs = self.validator.validate_library(raw)
        if vs:
            raise ValueError("库文件未通过契约校验：" + "；".join(str(v) for v in vs))
        return Library.from_dict(raw)

    def save(self, library: Library) -> None:
        raw = library.to_dict()
        vs = self.validator.validate_library(raw)
        if vs:
            raise ValueError("拒绝写入未通过校验的库：" + "；".join(str(v) for v in vs))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def next_id(self, library: Library) -> str:
        """按 R-### 规则分配下一个编号：现有最大序号 + 1。"""
        best = 0
        for r in library.records:
            try:
                best = max(best, int(r.id.split("-")[1]))
            except (IndexError, ValueError):
                continue
        return "R-%03d" % (best + 1)

    def merge(self, base: Library, incoming: Library) -> tuple[Library, MergeReport]:
        """合并：按指纹去重；编号冲突且指纹不同则重编号并记录 remap_from。"""
        report = MergeReport()
        merged = Library(version=base.version, records=list(base.records),
                         generated_at=base.generated_at)
        known_keys = {self.dedup.key_of(r) for r in merged.records}
        known_ids = {r.id for r in merged.records}

        for rec in incoming.records:
            key = self.dedup.key_of(rec)
            if key in known_keys:
                report.duplicated.append(rec.id)
                continue
            known_keys.add(key)
            if rec.id in known_ids:
                new_id = self.next_id(merged)
                report.renumbered[rec.id] = new_id
                data = rec.to_dict()
                data["id"] = new_id
                data["provenance"]["remap_from"] = rec.id
                rec = Archive.from_dict(data)
            known_ids.add(rec.id)
            merged.records.append(rec)
            report.added.append(rec.id)

        return merged, report

    def find_abandoned_with_blocker(self) -> list[Archive]:
        """列出「已放弃且阻塞点明确」的档案——死实验复活的输入。

        阻塞点明确 = blocker 非空且有 missing_info 之外的明确描述；
        这里以非空为最低门槛，具体筛法由 ResurrectionSkill 补充。
        """
        lib = self.load()
        return [r for r in lib.records if r.status == "已放弃" and r.blocker.strip()]
