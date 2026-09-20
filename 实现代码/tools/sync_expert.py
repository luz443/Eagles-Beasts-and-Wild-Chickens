"""把仓库同步进专家包，并把专家包镜像回仓库（双向，但单一真源是仓库）。

用法：python tools/sync_expert.py [--check]

单一真源（仓库） → 生成物（专家包）：
    src/rra/**                    → <pkg>/bin/rra/**
    tools/rra_cli.py              → <pkg>/bin/rra_cli.py
    prompts/*.md                  → <pkg>/skills/<skill>/references/prompt.md
    contracts/*.json              → <pkg>/bin/samples/contracts/ 与各技能 references/
    data/library.seed.json        → <pkg>/bin/samples/library.seed.json
    docs/record-format.md         → extract-record / reviewer2 的 references/

专家包（作者手写的部分） → 仓库镜像 expert/<name>/**：
    .codebuddy-plugin/plugin.json、agents/*.md、skills/*/SKILL.md、bin/rra_cli.py、
    README.md、avatars/.gitkeep —— 让开源仓库里也有一份可直接安装的专家包。

--check 只校验「包内引擎摘要 == 仓库引擎摘要」，不写任何文件（用于 CI / 交付前自检）。
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NAME = "research-retro-assistant"

# 专家目录：由 WORKBUDDY_CONFIG_DIR 决定（未设置时回落 ~/.workbuddy）
CFG = Path(os.environ.get("WORKBUDDY_CONFIG_DIR", "").strip() or (Path.home() / ".workbuddy"))
PKG = CFG / "plugins" / "marketplaces" / "my-experts" / "plugins" / NAME
MIRROR = REPO / "expert" / NAME

SKILL_OF_PROMPT = {
    "extract.md": "extract-record",
    "reverse_lookup.md": "reverse-lookup",
    "condition_compare.md": "condition-compare",
    "induction.md": "induction",
    "resurrection.md": "resurrection",
    "reviewer2.md": "reviewer2",
}

# 镜像策略（2026-09-19 外部审查后调整）：
#   expert/<name>/ 现在是**整份专家包的复制**（含 bin/rra、bin/samples 等生成物），
#   保证克隆仓库的人拿到即可安装；一致性由本脚本的 sha256 摘要 + `--check` 守着。
#   因此不再维护"只镜像手写文件"的白名单。


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def py_digest(root: Path) -> str:
    """目录摘要：只统计 .py 源码、跳过 __pycache__（否则仓库侧的 .pyc 会造成假警报）。"""
    h = hashlib.sha256()
    files = sorted(p for p in root.rglob("*.py")
                   if p.is_file() and "__pycache__" not in p.parts)
    for p in files:
        h.update(str(p.relative_to(root)).replace(os.sep, "/").encode("utf-8"))
        h.update(sha256_of(p).encode("ascii"))
    return h.hexdigest()


def sync_generated(log):
    """仓库 → 包：引擎、CLI、提示词、契约、样例。"""
    if (PKG / "bin" / "rra").exists():
        shutil.rmtree(PKG / "bin" / "rra")
    shutil.copytree(REPO / "src" / "rra", PKG / "bin" / "rra",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    log.append("bin/rra/  ← src/rra/（%d 个文件）"
               % sum(1 for p in (PKG / "bin" / "rra").rglob("*") if p.is_file()))

    shutil.copyfile(REPO / "tools" / "rra_cli.py", PKG / "bin" / "rra_cli.py")
    log.append("bin/rra_cli.py ← tools/rra_cli.py")

    samples = PKG / "bin" / "samples"
    (samples / "contracts").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO / "data" / "library.seed.json", samples / "library.seed.json")
    for f in sorted((REPO / "contracts").glob("*.json")):
        shutil.copyfile(f, samples / "contracts" / f.name)
    log.append("bin/samples/ ← data/ + contracts/")

    for prompt, skill in SKILL_OF_PROMPT.items():
        ref = PKG / "skills" / skill / "references"
        ref.mkdir(parents=True, exist_ok=True)
        src = REPO / "prompts" / prompt
        if not src.exists():
            log.append("!! 缺提示词 %s（跳过）" % src)
            continue
        shutil.copyfile(src, ref / "prompt.md")
        for extra in ("record.schema.json", "dim.json"):
            p = REPO / "contracts" / extra
            if p.exists():
                shutil.copyfile(p, ref / extra)
        if skill in ("extract-record", "reviewer2"):
            rf = REPO / "docs" / "record-format.md"
            if rf.exists():
                shutil.copyfile(rf, ref / "record-format.md")
        log.append("skills/%s/references/ ← prompts/%s + contracts/" % (skill, prompt))

    manifest = {
        "source_repo": str(REPO),
        "note": "bin/rra、bin/samples、skills/*/references、bin/rra_cli.py 为生成物；改仓库后重跑本脚本。",
        "engine_digest": py_digest(PKG / "bin" / "rra"),
        "repo_engine_digest": py_digest(REPO / "src" / "rra"),
        "cli_digest": sha256_of(PKG / "bin" / "rra_cli.py"),
        "repo_cli_digest": sha256_of(REPO / "tools" / "rra_cli.py"),
    }
    (PKG / "bin" / "SYNC.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def sync_mirror(log):
    """包 → 仓库镜像：**整份复制（含生成物）**，让克隆仓库的人直接可安装。

    2026-09-19 外部审查指出：原镜像只放"手写文件"，缺 bin/rra 与 bin/samples，
    克隆下来根本跑不起来。生成物进仓库确实有重复，但它们由本脚本产出、
    并由 sha256 摘要守着（`--check`）不会静默漂移 —— 这比"缺文件导致跑不起来"划算。
    """
    if MIRROR.exists():
        shutil.rmtree(MIRROR)
    shutil.copytree(PKG, MIRROR, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    log.append("expert/%s/  ← 完整专家包（含生成物，共 %d 个文件）"
               % (NAME, sum(1 for p in MIRROR.rglob("*") if p.is_file())))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只比对摘要，不写文件")
    ap.add_argument("--platform", action="store_true",
                    help="与 --check 连用：比对本机已安装的平台包（默认比对仓库镜像）")
    args = ap.parse_args()

    log = []
    if args.check:
        target = PKG if args.platform else MIRROR
        label = "本机已安装的平台包" if args.platform else "仓库镜像 expert/%s" % NAME
        if not (target / ".codebuddy-plugin" / "plugin.json").exists():
            if args.platform:
                log.append("本机未安装该平台包：%s\n"
                           "  → 这不影响仓库交付。安装方式：把 expert/%s/ 复制到 %s 后，\n"
                           "    跑官方 register_expert.py（记得先设 PYTHONIOENCODING=utf-8）。"
                           % (target, NAME, PKG.parent))
            else:
                log.append("仓库镜像不存在：%s\n  → 先跑不带 --check 的同步生成镜像。" % target)
            print("\n".join(log))
            return 1
        pkg_d, repo_d = py_digest(target / "bin" / "rra"), py_digest(REPO / "src" / "rra")
        cli_same = (sha256_of(target / "bin" / "rra_cli.py")
                    == sha256_of(REPO / "tools" / "rra_cli.py"))
        log.append("%s · 引擎摘要一致：%s" % (label, pkg_d == repo_d))
        log.append("%s · CLI 摘要一致：%s" % (label, cli_same))
        if pkg_d != repo_d:
            log.append("  → 不一致意味着「专家包里的确定性引擎」与仓库 src/rra 已分叉，"
                       "跑一次同步（不带 --check）即可对齐。")
        print("\n".join(log))
        return 0 if (pkg_d == repo_d and cli_same) else 1

    if not (PKG / ".codebuddy-plugin" / "plugin.json").exists():
        log.append("专家包不存在或未初始化：%s" % PKG)
        print("\n".join(log))
        return 1

    manifest = sync_generated(log)
    sync_mirror(log)
    log.append("引擎摘要一致（包内 == 仓库）：%s"
               % (manifest["engine_digest"] == manifest["repo_engine_digest"]))
    print("\n".join(log))
    return 0 if manifest["engine_digest"] == manifest["repo_engine_digest"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
