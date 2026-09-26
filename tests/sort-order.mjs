/**
 * 排序纯函数测试：三种模式 + 稳定性 + 非破坏性。python run_tests.py 会自动跑到它。
 * 用法：node web/tests/sort-order.mjs
 */
import { normalizeSort, sortRecords } from "../js/util/sort.js";

let passed = 0;
let failed = 0;
function check(name, ok, extra = "") {
  if (ok) { passed++; console.log("OK    " + name); }
  else { failed++; console.log("FAIL  " + name + (extra ? "  → " + extra : "")); }
}

const recs = [
  { id: "R-001", confidence: "high" },
  { id: "R-002", confidence: "low" },
  { id: "R-003", confidence: "medium" },
  { id: "R-004", confidence: "low" },
  { id: "R-005", confidence: "unknown" },   // 未知置信度：排最后
];
const LINKS = { "R-001": 3, "R-002": 0, "R-003": 5, "R-004": 1, "R-005": 2 };
const linkedOf = (r) => LINKS[r.id] || 0;
const ids = (list) => list.map(r => r.id).join(",");

// ---- 库内顺序：原样 ----
check("order 保持库内顺序", ids(sortRecords(recs, "order")) === "R-001,R-002,R-003,R-004,R-005",
  ids(sortRecords(recs, "order")));

// ---- 置信度低在前；同值（两条 low）保持库内相对顺序 ----
check("confidence 低在前且同值稳定",
  ids(sortRecords(recs, "confidence")) === "R-002,R-004,R-003,R-001,R-005",
  ids(sortRecords(recs, "confidence")));

// ---- 被关联多在前 ----
check("linked 多在前",
  ids(sortRecords(recs, "linked", linkedOf)) === "R-003,R-001,R-005,R-004,R-002",
  ids(sortRecords(recs, "linked", linkedOf)));

// ---- 非破坏性：不得改动入参，且返回新数组 ----
const before = ids(recs);
const out = sortRecords(recs, "confidence");
check("不改动入参", ids(recs) === before);
check("返回新数组", out !== recs);

// ---- 退化输入：非法模式回落库内顺序；空/非数组不抛错 ----
check("非法模式 → 库内顺序", ids(sortRecords(recs, "nonsense")) === before);
check("normalizeSort 非法值回落 order", normalizeSort("nonsense") === "order");
check("空数组安全", sortRecords([], "confidence").length === 0);
check("非数组安全", sortRecords(null, "linked").length === 0);
check("linked 缺回调时按全 0 处理（仍稳定）",
  ids(sortRecords(recs, "linked")) === before, ids(sortRecords(recs, "linked")));

console.log("\n通过 " + passed + " 项，失败 " + failed + " 项");
process.exit(failed ? 1 : 0);
