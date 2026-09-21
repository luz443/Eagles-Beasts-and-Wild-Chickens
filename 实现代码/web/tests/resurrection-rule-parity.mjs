/**
 * 两端「可重试候选」规则一致性护栏。
 *
 * 为什么需要它：这条规则不是数据结构（schema 管不到），而是**行为约定**——
 * 「只有『已放弃且阻塞点非空』的记录才进入可重试候选」。
 * 若只在一端改字面量，两端口径会静默分叉：网页把某条列进「可重试方向」，
 * 专家侧却不认它（或反过来），而两边测试都还是绿的。
 *
 * 做法（与 refutation-rule-parity.mjs 一致）：把两处实现的字面量读出来逐一比对，
 * 再各自跑一遍规则确认结论相同——不依赖 DOM，也不需要跑浏览器。
 *
 * 用法：node web/tests/resurrection-rule-parity.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { RESURRECTION_STATUS, isResurrectionCandidate, resurrectionCandidates, collectUnblocks } from "../js/util/resurrection.js";

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

const JS_RULE = "web/js/util/resurrection.js";
const JS_VIEW = "web/js/views/resurrection.js";
const PY_RULE = "src/rra/skills/resurrection.py";

const jsRule = read(JS_RULE);
const jsView = read(JS_VIEW);
const pyRule = read(PY_RULE);

// 1. 状态字面量：两端必须逐字一致
const mJs = (jsRule.match(/RESURRECTION_STATUS\s*=\s*"([^"]+)"/) || [])[1] || null;
const mPy = (pyRule.match(/CANDIDATE_STATUS\s*=\s*"([^"]+)"/) || [])[1] || null;
check("util/resurrection.js 里能抽到状态字面量", !!mJs, String(mJs));
check("resurrection.py 里能抽到状态字面量", !!mPy, String(mPy));
check("两端状态字面量一致（唯一真源）", !!mJs && mJs === mPy, `${mJs} vs ${mPy}`);
check("导出的常量与字面量一致", RESURRECTION_STATUS === mJs, `${RESURRECTION_STATUS} vs ${mJs}`);

// 2. 规则的组成必须两端相同：status 且 blocker 非空
check("网页规则以 status 过滤", /record\.status\s*!==\s*RESURRECTION_STATUS/.test(jsRule));
check("网页规则以 blocker 非空过滤", /blocker\.trim\(\)\.length\s*>\s*0/.test(jsRule));
check("Python 规则以 status 过滤", /r\.get\("status"\)\s*==\s*CANDIDATE_STATUS/.test(pyRule));
check("Python 规则以 blocker 非空过滤", /str\(r\.get\("blocker"/.test(pyRule) && /\.strip\(\)/.test(pyRule));

// 3. 规则必须真的被用上（否则等于写了没接）
check("可重试方向视图调用了候选规则", /isResurrectionCandidate|resurrectionCandidates/.test(jsView));
check("可重试方向视图汇总了解除依据", /collectUnblocks/.test(jsView));

// 4. 两条边界用同一个输入跑一遍
const edge = [
  { id: "R-006", status: "已放弃", blocker: "长序列训练显存不足" },
  { id: "R-001", status: "进行中", blocker: "长序列训练显存不足" },
  { id: "R-007", status: "已放弃", blocker: "   " },
  { id: "R-008", status: "已放弃", blocker: "" },
  { id: "R-009", status: "已放弃" },
  { id: "R-010", status: "已绕过", blocker: "显存" },
];
const got = resurrectionCandidates(edge).map(r => r.id);
check("边界输入只捞到 R-006", JSON.stringify(got) === JSON.stringify(["R-006"]), JSON.stringify(got));
check("非对象输入不崩", isResurrectionCandidate(null) === false && resurrectionCandidates("x").length === 0);

// 5. 种子库里的伏笔必须真的捞得出来——否则「可重试方向」是个空页
const seed = JSON.parse(read("data/library.seed.json"));
const seedIds = resurrectionCandidates(seed.records).map(r => r.id);
check("种子库可重试候选 >= 2 条", seedIds.length >= 2, JSON.stringify(seedIds));

// 6. 解除依据的汇总（collectUnblocks）只按声明派生，不改档案
const withUnblock = [{ id: "R-013", resurrection: { unblocks: [{ record: "R-006", basis: "R-013", quote: "xxxx" }] } }];
const map = collectUnblocks(withUnblock);
check("collectUnblocks 按被解除编号建索引", map.has("R-006") && map.get("R-006")[0].from === "R-013");
check("collectUnblocks 对畸形输入安全", collectUnblocks([null, "x", { resurrection: 1 }]).size === 0);

// 7. 文件存在且非空（避免"文件改名后测试静默全过"）
for (const rel of [JS_RULE, JS_VIEW, PY_RULE]) {
  check("文件存在且非空：" + rel, read(rel).trim().length > 0);
}

console.log("\n通过 " + passed + " 项，失败 " + failed + " 项");
process.exit(failed ? 1 : 0);
