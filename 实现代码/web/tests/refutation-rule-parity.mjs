/**
 * 两端「人工纠错」规则一致性护栏。
 *
 * 为什么需要它：这条规则不是数据结构（schema 管不到），而是**行为约定**——
 * 「纠错记录不算一次尝试，不能用来凑归纳门槛」。
 * 若只在一端改字面量，两端口径会静默分叉：网页说不足 3 条，专家侧却产出假设。
 *
 * 做法：把三处实现里的字面量读出来逐一比对（不依赖 DOM，也不需要跑浏览器）。
 * 用法：node web/tests/refutation-rule-parity.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");

let passed = 0;
let failed = 0;
function check(name, ok, extra = "") {
  if (ok) { passed++; console.log("OK    " + name); }
  else { failed++; console.log("FAIL  " + name + (extra ? "  → " + extra : "")); }
}

function read(rel) {
  return fs.readFileSync(path.join(ROOT, rel), "utf8");
}

/** 从文本里抽出被引号包住的标记字面量。 */
function extractMarker(text, pattern) {
  const m = text.match(pattern);
  return m ? m[1] : null;
}

const JS_REFUTE = "web/js/refute.js";
const JS_INCUBATION = "web/js/views/incubation.js";
const PY_RULE = "src/rra/library/refutation.py";

const jsRefute = read(JS_REFUTE);
const jsIncubation = read(JS_INCUBATION);
const pyRule = read(PY_RULE);

const mRefute = extractMarker(jsRefute, /includes\(\s*"([^"]+)"\s*\)/);
const mIncubation = extractMarker(jsIncubation, /includes\(\s*"([^"]+)"\s*\)/);
const mPython = extractMarker(pyRule, /MARKER\s*=\s*"([^"]+)"/);

check("refute.js 里能抽到标记字面量", !!mRefute, String(mRefute));
check("incubation.js 里能抽到标记字面量", !!mIncubation, String(mIncubation));
check("refutation.py 里能抽到标记字面量", !!mPython, String(mPython));

check("网页两处字面量一致", !!mRefute && mRefute === mIncubation,
  `${mRefute} vs ${mIncubation}`);
check("Python 与网页字面量一致（两端唯一真源）", !!mPython && mPython === mRefute,
  `${mPython} vs ${mRefute}`);

// 归纳门槛这条规则必须真的接上了过滤器：Python 侧要调用 exclude_refutations
check("Python 归纳技能确实调用了 exclude_refutations",
  /exclude_refutations\(/.test(read("src/rra/skills/induction.py")));

// 网页端分组前也必须先过滤
check("网页孵化清单在分组前过滤纠错记录",
  /filter\(r => !\(r\.attempt \|\| ""\)\.includes\(/.test(jsIncubation));

// 覆盖检查：三处文件都存在且非空（避免"文件改名后测试静默全过"）
for (const rel of [JS_REFUTE, JS_INCUBATION, PY_RULE]) {
  check("文件存在且非空：" + rel, read(rel).trim().length > 0);
}

console.log("\n通过 " + passed + " 项，失败 " + failed + " 项");
process.exit(failed ? 1 : 0);
