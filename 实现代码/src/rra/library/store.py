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
    renumbered: dict[str, str] = field(default_factory=dict)
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
        # newline="\n" 必须显式给：Windows 上 write_text 会把 \n 翻译成 os.linesep，
        # 于是跑一次 make_seed.py 就把 data/library.seed.json 从纯 LF 变成 CRLF，
        # 镜像逐字节比对测试（test_cli_and_samples_are_mirrored）立刻变红，
        # 且"同一输入 → 同一字节"不再成立（2026-09-22 后端审查 P1-4 实测）。
        #
        # 原子写（同轮审查 P2-11）：先写同目录临时文件，再原子换名。此前直接覆盖目标文件，
        # 写入中断/断电会留下**被截断的库文件**——"不产生半成品"当时只覆盖"校验失败"这一种情况。
        # 网页侧同类问题有 web/tests/store-commit-safety.mjs 守着，Python 侧现在也有对应实现。
        text = json.dumps(raw, ensure_ascii=False, indent=2) + "\n"
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8", newline="\n")
        tmp.replace(self.path)      # Path.replace == os.replace：同目录内原子换名

    def next_id(self, library: Library) -> str:
        """按 R-### 规则分配下一个编号：现有最大序号 + 1。"""
        return "R-%03d" % (self._max_seq(r.id for r in library.records) + 1)

    @staticmethod
    def _max_seq(ids) -> int:
        """取一批编号里最大的序号；解析不出的编号跳过（不因个别脏编号整体失败）。"""
        best = 0
        for rid in ids:
            try:
                best = max(best, int(str(rid).split("-")[1]))
            except (IndexError, ValueError):
                continue
        return best

    @staticmethod
    def _bump_version(version: str) -> str:
        """库级版本递增：把最后一个数字段 +1（"0.1.0" → "0.1.1"）。

        逐段找最后一个能解析成数字的段，是为了兼容 "0.1" / "0.1.0" / "2026-09-22" 这类写法；
        一段数字都没有时退化为追加 `.1`，绝不返回原值（否则「合并过了」与「没合并」不可区分）。
        """
        parts = str(version or "").split(".")
        for i in range(len(parts) - 1, -1, -1):
            if parts[i].isdigit():
                parts[i] = str(int(parts[i]) + 1)
                return ".".join(parts)
        return (str(version) + ".1") if version else "0.1.0"

    @staticmethod
    def _rewrite_refs(data: dict, remap: dict[str, str]) -> dict:
        """按 old→new 统一改写档案内的引用。

        重编号只改 `id` 是不够的：`links[].target` / `evidence_refs[].record` /
        `resurrection[].basis` 都指向别的档案，不改写就会「指向另一条记录」——
        而整库校验查不出这种错（引用的编号确实存在，只是指错了人）。
        """
        if not remap:
            return data
        for link in data.get("links") or []:
            if isinstance(link, dict) and link.get("target") in remap:
                link["target"] = remap[link["target"]]
        for ref in data.get("evidence_refs") or []:
            if isinstance(ref, dict) and ref.get("record") in remap:
                ref["record"] = remap[ref["record"]]
        resurrection = data.get("resurrection")
        if isinstance(resurrection, dict):
            for item in resurrection.get("unblocks") or []:
                if isinstance(item, dict) and item.get("basis") in remap:
                    item["basis"] = remap[item["basis"]]
        return data

    def merge(self, base: Library, incoming: Library) -> tuple[Library, MergeReport]:
        """合并：按指纹去重；编号冲突且指纹不同则重编号并记录 remap_from。

        重编号必须是**一次性**的：先只对「会真正入库的 incoming 记录」找出与 base 撞号的编号，
        从 `max(base ∪ incoming) + 1` 起依次分配新号并留下 old→new 映射，
        再统一改写引用。原实现边加边用 merged 求下一个号，会把本来没撞号的 incoming
        记录也卷进重命名（2026-09-22 后端审查 P1-3 的最小复现）。
        """
        report = MergeReport()
        merged = Library(version=self._bump_version(base.version),
                         records=list(base.records), generated_at=base.generated_at)
        known_keys = {self.dedup.key_of(r) for r in merged.records}
        known_ids = {r.id for r in merged.records}

        # 第一遍：去重，并找出所有撞号（只看真正会入库的记录）。
        pending: list[Archive] = []
        for rec in incoming.records:
            key = self.dedup.key_of(rec)
            if key in known_keys:
                report.duplicated.append(rec.id)
                continue
            known_keys.add(key)
            pending.append(rec)

        remap: dict[str, str] = {}
        conflicts = [r.id for r in pending if r.id in known_ids]
        seq = self._max_seq(list(known_ids) + [r.id for r in incoming.records]) + 1
        for old in conflicts:
            if old not in remap:
                remap[old] = "R-%03d" % seq
                seq += 1

        # 第二遍：套用重编号 + 改写引用，再入库。
        for rec in pending:
            data = self._rewrite_refs(rec.to_dict(), remap)
            new_id = remap.get(rec.id)
            if new_id:
                report.renumbered[rec.id] = new_id
                data["id"] = new_id
                # 不覆盖既有 remap_from：它记的是更早的一跳（档案可能被重编号过多次）。
                if not data["provenance"].get("remap_from"):
                    data["provenance"]["remap_from"] = rec.id
            rec = Archive.from_dict(data)
            known_ids.add(rec.id)
            merged.records.append(rec)
            report.added.append(rec.id)

        violations = self.validator.validate_library(merged.to_dict())
        if violations:
            report.violations = [str(v) for v in violations]
            raise ValueError("合并结果未通过契约校验：" + "；".join(report.violations))
        return merged, report

    def find_abandoned_with_blocker(self) -> list[Archive]:
        """列出「已放弃且阻塞点明确」的档案——死实验复活的输入。

        阻塞点明确 = blocker 非空且有 missing_info 之外的明确描述；
        这里以非空为最低门槛，具体筛法由 ResurrectionSkill 补充。
        """
        lib = self.load()
        return [r for r in lib.records if r.status == "已放弃" and r.blocker.strip()]
