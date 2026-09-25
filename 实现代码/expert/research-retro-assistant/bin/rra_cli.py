#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rra_cli —— 研究复盘助手的确定性命令行入口（专家在会话中调用）。

定位：**只做确定性的事**——契约校验、编号、去重指纹、召回打分、澄清记账、合并、导出、用例清单。
语义判断（把日志读成档案、判断两条记录是否真的冲突、写归纳假设与质疑）由专家（模型）完成，
本 CLI 不碰语义，也不调用任何模型。

设计约束：
1. 输出一律 JSON（stdout），便于专家直接读取；错误也走 JSON，退出码非 0；
2. **拒绝即失败**：契约不合规时退出码 1 并给出「路径 + 原因 + 期望」，绝不返回半个结果；
3. 默认只读：只有 merge-library 在显式给 --out 时才写文件；
4. 不依赖任何网络与第三方包（只用标准库 + 本目录随包的 rra）。

用法：
  python3 bin/rra_cli.py <command> [参数]
  command 列表：contract-dims / validate-record / validate-library / next-id / recall /
                dedup-check / apply-clarification / condition-compare /
                induction-candidates / resurrection-candidates / merge-library /
                report / blocker-digest / eval-cases / selftest
"""

import argparse
import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _bootstrap_engine():
    """把确定性引擎放进 import 路径，并返回引擎根目录。

    两种运行位置都必须能直接跑（2026-09-19 外部代码审查报出的 P0：原先只支持"引擎与 CLI
    同目录"，仓库里的 tools/rra_cli.py 直接 ModuleNotFoundError，且即使设了 PYTHONPATH 也会
    因为样例路径写死在 HERE/samples 下而失败）：
      · 专家包内：<pkg>/bin/rra_cli.py     与 <pkg>/bin/rra/ 同级
      · 仓库内  ：<repo>/tools/rra_cli.py  引擎在 <repo>/src/rra/
    **不允许**要求外部 PYTHONPATH —— 找不到就明确报错，而不是抛 ModuleNotFoundError。
    """
    for engine_root in (HERE, HERE.parent / "src"):
        if (engine_root / "rra" / "__init__.py").is_file():
            if str(engine_root) not in sys.path:
                sys.path.insert(0, str(engine_root))
            return engine_root
    raise SystemExit(
        "找不到 rra 引擎：已在 %s 与 %s 下查找 rra/__init__.py。\n"
        "本 CLI 需与引擎同目录（专家包 bin/），或位于仓库 tools/ 下（引擎在 src/）。"
        % (HERE, HERE.parent / "src"))


def _first_existing(*paths):
    """返回第一个存在的路径；都不存在返回 None（调用方据此给出明确错误，而不是抛栈）。"""
    for p in paths:
        if Path(p).exists():
            return Path(p)
    return None


ENGINE_ROOT = _bootstrap_engine()

from rra.contracts.dims import Dim                                    # noqa: E402
from rra.contracts.models import Archive, Library                     # noqa: E402
from rra.contracts.validator import Validator                         # noqa: E402
from rra.eval.cases import CaseRegistry                               # noqa: E402
from rra.export.report import MarkdownExporter                        # noqa: E402
from rra.library.dedup import Deduplicator                            # noqa: E402
from rra.library.store import LibraryStore                            # noqa: E402
from rra.recall.scorer import RecallScorer                            # noqa: E402
from rra.skills.base import SkillInput, SkillOutput                   # noqa: E402
from rra.skills.condition_compare import ConditionCompareSkill        # noqa: E402
from rra.skills.induction import InductionSkill                       # noqa: E402
from rra.skills.resurrection import ResurrectionSkill                 # noqa: E402
from rra.skills.reverse_lookup import ReverseLookupSkill              # noqa: E402

# 样例与契约：包内（bin/samples/...）与仓库内（data/ + contracts/）都认
SAMPLE_LIBRARY = _first_existing(HERE / "samples" / "library.seed.json",
                                 HERE.parent / "data" / "library.seed.json")
SAMPLE_CONTRACTS = _first_existing(HERE / "samples" / "contracts",
                                   HERE.parent / "contracts")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def emit(obj, code=0):
    """把结果写到 stdout 并设置退出码。中文不转义，方便专家直接读。"""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    sys.exit(code)


def fail(message, **extra):
    payload = {"ok": False, "error": message}
    payload.update(extra)
    emit(payload, 1)


def violations_of(raw, kind, path):
    v = Validator()
    bad = v.validate_library(raw) if kind == "library" else v.validate_archive(raw)
    return [str(x) for x in bad]


def cmd_contract_dims(_args):
    dims = [d.value for d in Dim]
    emit({"ok": True, "count": len(dims), "dims": dims,
          "note": "维度只允许枚举值；自由文本会被契约拒绝（见 record.schema.json）"})


def cmd_validate_record(args):
    raw = read_json(args.file)
    bad = violations_of(raw, "record", args.file)
    if bad:
        fail("档案不符合契约，已拒绝（共 %d 处）" % len(bad), violations=bad)
    emit({"ok": True, "id": raw.get("id"), "violations": []})


def cmd_validate_library(args):
    raw = read_json(args.file)
    bad = violations_of(raw, "library", args.file)
    if bad:
        fail("整库不符合契约，已拒绝（共 %d 处）" % len(bad), violations=bad)
    emit({"ok": True, "records": len(raw.get("records", [])), "violations": []})


def cmd_next_id(args):
    lib = Library.from_dict(read_json(args.library))
    emit({"ok": True, "next_id": LibraryStore(Path(args.library)).next_id(lib)})


def cmd_recall(args):
    lib = Library.from_dict(read_json(args.library))
    scorer = RecallScorer()
    if args.weights:
        scorer.load_weights(args.weights)
    hits = scorer.recall(args.query, lib, limit=args.limit)
    emit({"ok": True, "query": args.query, "count": len(hits),
          "hits": [dataclasses.asdict(h) if dataclasses.is_dataclass(h) else str(h) for h in hits],
          "note": "宁少不凑：没有区分度的查询返回空列表，不要据此编造命中"})


def cmd_dedup_check(args):
    lib = Library.from_dict(read_json(args.library))
    raw = read_json(args.candidate)
    dedup = Deduplicator()
    key = dedup.key_of(Archive.from_dict(raw))
    hits = []
    for rec in lib.records:
        try:
            if dedup.key_of(rec) == key:
                hits.append(rec.id)
        except Exception:  # noqa: BLE001 —— 库里有畸形记录时跳过，不因此崩掉
            continue
    emit({"ok": True, "duplicate": bool(hits), "match_ids": hits, "dedup_key": key})


def cmd_apply_clarification(args):
    raw = read_json(args.record)
    skill = ReverseLookupSkill()
    answer = (getattr(args, "answer", "") or "").strip()
    out = skill.apply_clarification_facts(
        SkillOutput(payload=raw, narrative=""), args.keys, answer=answer)
    warnings = list(out.warnings)
    if not answer:
        # 不给答复原文就只记账、不留痕：必须说在明面上，不能让专家以为已经记进档案。
        warnings.append("未提供 --answer：只记账、不留痕（clarifications 不会写入档案）")
    emit({"ok": True, "payload": out.payload, "warnings": warnings})


def cmd_condition_compare(args):
    a = read_json(args.a)
    b = read_json(args.b)
    skill = ConditionCompareSkill()
    emit({"ok": True, "differing_dims": skill.differing_dims(a, b),
          "verdict": skill.verdict(a, b),
          "note": "verdict 是确定性结论（同因/异因/条件不全）；解释措辞由专家写"})


def cmd_induction_candidates(args):
    lib = read_json(args.library)
    groups = InductionSkill().eligible_groups(lib.get("records", []))
    emit({"ok": True, "group_count": len(groups),
          "groups": {k: [r.get("id") for r in v] for k, v in groups.items()},
          "note": "只给达到门槛（同一阻塞点 >= 3 条）的分组；写假设由专家完成"})


def cmd_resurrection_candidates(args):
    lib = read_json(args.library)
    rows = ResurrectionSkill().candidates(lib)
    emit({"ok": True, "count": len(rows),
          "candidates": [{"id": r.get("id"), "blocker": r.get("blocker"),
                          "observation": r.get("observation")} for r in rows],
          "note": "只列「已放弃且阻塞点明确」的候选；是否复活由专家判断并给理由"})


def cmd_merge_library(args):
    base = Library.from_dict(read_json(args.library))
    incoming = Library.from_dict(read_json(args.incoming))
    merged, report = LibraryStore(Path(args.library)).merge(base, incoming)
    result = {"ok": True, "total": len(merged.records),
              "report": dataclasses.asdict(report) if dataclasses.is_dataclass(report)
              else getattr(report, "__dict__", str(report))}
    if args.out:
        LibraryStore(Path(args.out)).save(merged)
        result["written"] = args.out
    else:
        result["written"] = None
        result["note"] = "未传 --out，只报告合并结果，不写任何文件"
    emit(result)


def cmd_report(args):
    emit({"ok": True, "markdown": MarkdownExporter().archive_report(read_json(args.file))})


def cmd_blocker_digest(args):
    records = read_json(args.library).get("records", [])
    emit({"ok": True, "markdown": MarkdownExporter().blocker_digest(records)})


def cmd_eval_cases(args):
    reg = CaseRegistry.default()
    def dump(c):
        row = dataclasses.asdict(c) if dataclasses.is_dataclass(c) else dict(getattr(c, "__dict__", {}))
        row["kind"] = "开放" if c.is_open else "盲测"
        return row
    rows = [dump(c) for c in (reg.blind_cases() + reg.open_cases())]
    emit({"ok": True, "blind": len(reg.blind_cases()), "open": len(reg.open_cases()),
          "cases": rows})


def cmd_selftest(_args):
    """自检：用样例数据跑通「整库校验 → 编号 → 召回 → 归纳候选 → 复活候选」五步。"""
    steps = []
    if SAMPLE_LIBRARY is None or not SAMPLE_LIBRARY.is_file():
        fail("找不到样例库：既不在 %s/samples/，也不在 %s/data/。"
             % (HERE, HERE.parent))
    raw = read_json(SAMPLE_LIBRARY)
    bad = violations_of(raw, "library", str(SAMPLE_LIBRARY))
    steps.append({"step": "validate-library", "ok": not bad, "violations": len(bad)})
    if bad:
        fail("自检失败：样例库未过契约", steps=steps)
    lib = Library.from_dict(raw)
    nid = LibraryStore(SAMPLE_LIBRARY).next_id(lib)
    steps.append({"step": "next-id", "ok": bool(nid), "next_id": nid})
    hits = RecallScorer().recall("长序列训练显存不足", lib, limit=3)
    steps.append({"step": "recall", "ok": len(hits) >= 1,
                  "hits": [dataclasses.asdict(h) if dataclasses.is_dataclass(h) else str(h)
                           for h in hits]})
    groups = InductionSkill().eligible_groups(raw.get("records", []))
    steps.append({"step": "induction-candidates", "ok": len(groups) >= 1,
                  "groups": len(groups)})
    rows = ResurrectionSkill().candidates(raw)
    steps.append({"step": "resurrection-candidates", "ok": True, "count": len(rows)})
    ok = all(s.get("ok") for s in steps)
    emit({"ok": ok, "records": len(raw.get("records", [])), "steps": steps,
          "engine_root": str(ENGINE_ROOT),
          "sample_library": str(SAMPLE_LIBRARY),
          "contracts_dir": str(SAMPLE_CONTRACTS) if SAMPLE_CONTRACTS else "(未找到)"},
         0 if ok else 1)


class _JsonArgumentParser(argparse.ArgumentParser):
    """用法错误也走 JSON（2026-09-22 后端审查 P2-9）。

    argparse 默认只把用法打到 stderr、stdout 一个字节都没有，退出码 2 ——
    这与本文件开头的承诺「输出一律 JSON（stdout）；错误也走 JSON，退出码非 0」相反：
    专家按 JSON 解析 stdout 会直接炸，而不是拿到一条可读的失败原因。
    覆写 error() 即可（argparse 的所有参数错误都经过它）；`emit()` 内部 sys.exit，
    退出码仍是非 0（沿用 argparse 惯例的 2）。
    """

    def error(self, message: str):  # type: ignore[override]
        emit({"ok": False, "error": "参数用法错误：%s" % message,
              "usage": self.format_usage().strip()}, 2)


def build_parser():
    p = _JsonArgumentParser(prog="rra_cli", description="研究复盘助手 · 确定性命令行入口")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("contract-dims", help="列出九维枚举").set_defaults(func=cmd_contract_dims)
    sub.add_parser("selftest", help="用随包样例自检（校验/编号/召回/归纳/复活）").set_defaults(func=cmd_selftest)

    for name, fn, help_text in (
        ("validate-record", cmd_validate_record, "校验单条档案是否符合契约"),
        ("validate-library", cmd_validate_library, "校验整库是否符合契约"),
    ):
        s = sub.add_parser(name, help=help_text)
        s.add_argument("file")
        s.set_defaults(func=fn)

    s = sub.add_parser("next-id", help="给出下一个可用档案编号")
    s.add_argument("library")
    s.set_defaults(func=cmd_next_id)

    s = sub.add_parser("recall", help="按关键词召回候选（宁少不凑）")
    s.add_argument("library")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=5)
    s.add_argument("--weights", default="")
    s.set_defaults(func=cmd_recall)

    s = sub.add_parser("dedup-check", help="判断候选记录是否与库内某条重复")
    s.add_argument("library")
    s.add_argument("candidate")
    s.set_defaults(func=cmd_dedup_check)

    s = sub.add_parser("apply-clarification", help="澄清记账：移除已澄清项并递增版本")
    s.add_argument("record")
    s.add_argument("keys", nargs="+")
    s.add_argument("--answer", default="", help="澄清答复原文；给了才写入 clarifications")
    s.set_defaults(func=cmd_apply_clarification)

    s = sub.add_parser("condition-compare", help="两条记录的条件对比（确定性部分）")
    s.add_argument("a")
    s.add_argument("b")
    s.set_defaults(func=cmd_condition_compare)

    s = sub.add_parser("induction-candidates", help="同一阻塞点 >= 3 条的分组")
    s.add_argument("library")
    s.set_defaults(func=cmd_induction_candidates)

    s = sub.add_parser("resurrection-candidates", help="已放弃且阻塞点明确的候选")
    s.add_argument("library")
    s.set_defaults(func=cmd_resurrection_candidates)

    s = sub.add_parser("merge-library", help="合并导入（去重 + 重编号）")
    s.add_argument("library")
    s.add_argument("incoming")
    s.add_argument("--out", default="")
    s.set_defaults(func=cmd_merge_library)

    s = sub.add_parser("report", help="生成单条档案的 Markdown 报告")
    s.add_argument("file")
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("blocker-digest", help="生成避坑清单（按阻塞点分组）")
    s.add_argument("library")
    s.set_defaults(func=cmd_blocker_digest)

    sub.add_parser("eval-cases", help="列出评测用例（开放 / 盲测）").set_defaults(func=cmd_eval_cases)
    return p


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except FileNotFoundError as e:
        fail("文件不存在：%s" % e)
    except json.JSONDecodeError as e:
        fail("JSON 解析失败：%s" % e)
    except Exception as e:  # noqa: BLE001 —— 统一转成 JSON 错误，别把栈甩给用户
        fail("%s: %s" % (type(e).__name__, e))


if __name__ == "__main__":
    main()
