/**
 * 路由纯函数测试：往返一致性 + 边界。python run_tests.py 会自动跑到它。
 * 用法：node web/tests/route-roundtrip.mjs
 */
import { parseHash, routeToHash, sameParams } from "../js/route.js";

const VIEWS = ["library", "detail", "map", "projectCheck", "compareMatrix", "incubation"];

let passed = 0;
let failed = 0;
function check(name, ok, extra = "") {
  if (ok) { passed++; console.log("OK    " + name); }
  else { failed++; console.log("FAIL  " + name + (extra ? "  → " + extra : "")); }
}

// ---- 往返：状态 → hash → 状态，必须一模一样 ----
const cases = [
  ["library", {}],
  ["library", { query: "显存" }],
  ["library", { query: "显存", status: "进行中", sort: "confidence" }],
  ["library", { sort: "linked" }],
  ["projectCheck", {}],
  ["map", {}],
  ["compareMatrix", {}],
  ["incubation", {}],
  ["detail", { id: "R-003" }],
];
for (const [name, params] of cases) {
  const h = routeToHash(name, params);
  const back = parseHash(h, VIEWS);
  check("往返 " + name + " " + JSON.stringify(params) + " → " + h,
    !!back && back.name === name && sameParams(back.params, params),
    JSON.stringify(back));
}

// ---- 默认值折叠：sort=order 是默认值，不该出现在 URL 里 ----
check("默认排序不写进 URL", routeToHash("library", { sort: "order" }) === "#/library",
  routeToHash("library", { sort: "order" }));

// ---- 边界：坏链接一律返回 null（调用方据此"不动作"） ----
check("空 hash → null", parseHash("", VIEWS) === null);
check("未知视图 → null", parseHash("#/nope", VIEWS) === null);
check("detail 缺编号 → null", parseHash("#/detail", VIEWS) === null);
check("只有 # 号 → null", parseHash("#", VIEWS) === null);

// ---- 宽容：缺前导斜杠也要认（人手工敲的链接） ----
check("缺前导斜杠可解析", (parseHash("#library", VIEWS) || {}).name === "library");
check("#/ 带尾斜杠可解析", (parseHash("#/library/", VIEWS) || {}).name === "library");

// ---- 转义：检索词里的 & = 中文 空格必须原样还原 ----
check("特殊字符往返", (() => {
  const q = "batch=32 & 显存 不足";
  const b = parseHash(routeToHash("library", { query: q }), VIEWS);
  return !!b && b.params.query === q;
})(), "检索词未原样还原");

check("档案编号转义往返", (() => {
  const b = parseHash(routeToHash("detail", { id: "R-003" }), VIEWS);
  return !!b && b.params.id === "R-003";
})());

// ---- sameParams：缺省值等价、真实差异必须报 false ----
check("缺省与空串等价", sameParams({ query: "", status: undefined }, {}));
check("真实差异报 false", sameParams({ query: "a" }, { query: "b" }) === false);
check("多一个键报 false", sameParams({}, { sort: "linked" }) === false);

console.log("\n通过 " + passed + " 项，失败 " + failed + " 项");
process.exit(failed ? 1 : 0);
