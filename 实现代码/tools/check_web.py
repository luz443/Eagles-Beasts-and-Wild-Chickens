"""前端静态检查：JS 语法（ESM）+ CSS 卫生 + index.html 引用完整性。

用法：python tools/check_web.py
退出码非 0 即有问题。

为什么不用 node --check 直接查 *.js：这些文件是 ESM 但扩展名是 .js，
node --check 会按 CommonJS 解析而误报 import。做法是复制成 .mjs 再检查。
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

problems = []
lines = []


def walk(base: Path, suffix: str):
    out = []
    for cur, dirs, files in os.walk(base):
        for name in sorted(files):
            if name.endswith(suffix):
                out.append(Path(cur) / name)
    return sorted(out)


def main() -> int:
    # Windows 控制台默认 GBK：输出里有中文与全角符号，统一按 UTF-8 走
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    node = os.environ.get("RRA_NODE", "node")

    # ---- 1. JS 语法 ----
    js_files = walk(WEB / "js", ".js")
    tmp_dir = tempfile.mkdtemp(prefix="rra-syntax-")
    try:
        for f in js_files:
            tmp = Path(tmp_dir) / (f.stem + "-" + str(abs(hash(str(f))) % 100000) + ".mjs")
            shutil.copyfile(f, tmp)
            r = subprocess.run([node, "--check", str(tmp)], capture_output=True, text=True)
            rel = f.relative_to(WEB).as_posix()
            if r.returncode == 0:
                lines.append("OK    JS   " + rel)
            else:
                first = (r.stderr or "").strip().splitlines()[0] if (r.stderr or "").strip() else "未知错误"
                lines.append("FAIL  JS   " + rel + "\n      " + first)
                problems.append(rel)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # ---- 2. CSS：括号配平 + 组件层禁裸色值 ----
    css_files = walk(WEB / "css", ".css")
    for f in css_files:
        text = f.read_text(encoding="utf-8")
        rel = f.relative_to(WEB).as_posix()
        opens, closes = text.count("{"), text.count("}")
        import re
        hexes = re.findall(r"#[0-9a-fA-F]{3,8}\b", text)
        local = []
        if opens != closes:
            local.append("花括号不配平 { =%d } =%d" % (opens, closes))
        if rel != "css/tokens.css" and hexes:
            local.append("出现裸色值 %d 处：%s" % (len(hexes), " ".join(sorted(set(hexes)))))
        if local:
            lines.append("FAIL  CSS  " + rel + "\n      " + "\n      ".join(local))
            problems.append(rel)
        else:
            note = ("含 %d 个令牌色值" % len(set(hexes))) if rel == "css/tokens.css" else "无裸色值"
            lines.append("OK    CSS  %s（{} 配平 %d 对；%s）" % (rel, opens, note))

    # ---- 3. index.html 必须引入全部 CSS；旧 app.css 不允许复活 ----
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for f in css_files:
        rel = f.relative_to(WEB).as_posix()
        if rel not in html:
            lines.append("FAIL  HTML index.html 未引入 " + rel)
            problems.append("index.html<-" + rel)
    if (WEB / "css" / "app.css").exists():
        lines.append("FAIL  CSS  css/app.css 仍存在（已拆分为三层，这是死文件）")
        problems.append("css/app.css")

    lines.append("")
    lines.append("文件数：JS %d 个，CSS %d 个" % (len(js_files), len(css_files)))
    lines.append(("未通过 %d 项：" % len(problems)) + "、".join(problems) if problems else "全部通过（0 项问题）")
    print("\n".join(lines))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
