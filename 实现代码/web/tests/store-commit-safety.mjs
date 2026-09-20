/**
 * 网页侧的「先落盘、后改内存」原子性测试（2026-09-19 外部审查 P1）。
 *
 * 原缺陷：importLibrary 里先 `this.library = next` 再 `save()`。save 因配额/隐私模式抛错时，
 * 内存已经是新库、存储还是旧库 —— 调用方以为"失败没变"，实际内存被污染。
 *
 * 用法：node web/tests/store-commit-safety.mjs（退出码非 0 即回归）
 */
import { LibraryStore } from "../js/store.js";
import { RefutationController } from "../js/refute.js";

let passed = 0;
let failed = 0;
function check(name, ok, extra = "") {
  if (ok) { passed++; console.log("OK    " + name); }
  else { failed++; console.log("FAIL  " + name + (extra ? "  → " + extra : "")); }
}

function rec(id) {
  return {
    id, attempt: "尝试 " + id, expectation: "e", observation: "o", blocker: "b",
    attribution: { text: "t", type: "assumption" }, boundary: "bd",
    confidence: "low", status: "进行中",
    provenance: { author: "测试", date: "2026-09-19", source: "模拟" },
  };
}
const lib = (ids) => ({ version: "0.1.0", generated_at: "2026-09-19", records: ids.map(rec) });

/** 可注入失败的存储适配器（形状与 PersistenceAdapter 一致）。 */
class FakeAdapter {
  constructor({ failOnWrite = false, seed = null } = {}) {
    this.failOnWrite = failOnWrite;
    this.map = new Map();
    this.writes = 0;
    if (seed) this.map.set("rra:library", JSON.stringify(seed));
  }
  key(k) { return "rra:" + k; }
  read(k) { const raw = this.map.get(this.key(k)); return raw === undefined ? null : JSON.parse(raw); }
  write(k, v) {
    this.writes += 1;
    if (this.failOnWrite) throw new Error("QuotaExceededError: 模拟写入失败");
    this.map.set(this.key(k), JSON.stringify(v));
  }
  remove(k) { this.map.delete(this.key(k)); }
  isAvailable() { return true; }
  onChanged() {}
}

const ids = (store) => store.library.records.map(r => r.id).join(",");

// ---- 1. 正常路径：写入成功后才替换内存 ----
{
  const adapter = new FakeAdapter({ seed: lib(["R-001"]) });
  const store = new LibraryStore(adapter);
  store.library = lib(["R-001"]);
  const report = store.importLibrary(lib(["R-999"]));
  check("正常导入：内存含新档案", ids(store) === "R-001,R-999", ids(store));
  check("正常导入：已落盘", adapter.read("library").records.length === 2);
  check("正常导入：报告列出新增", report.added.join() === "R-999", JSON.stringify(report));
}

// ---- 2. 写入失败：必须抛错，且内存保持旧库（核心回归点）----
{
  const adapter = new FakeAdapter({ failOnWrite: true, seed: lib(["R-001"]) });
  const store = new LibraryStore(adapter);
  store.library = lib(["R-001"]);
  let threw = false;
  try { store.importLibrary(lib(["R-999"])); } catch { threw = true; }
  check("写失败：导入抛错", threw);
  check("写失败：内存未被污染", ids(store) === "R-001", ids(store));
  const stored = adapter.read("library");
  check("写失败：存储仍是旧库（R-999 没写进去）",
    !!stored && stored.records.map(r => r.id).join() === "R-001",
    JSON.stringify(stored && stored.records.map(r => r.id)));
}

// ---- 3. save() 写失败同样不得改内存 ----
{
  const adapter = new FakeAdapter({ failOnWrite: true });
  const store = new LibraryStore(adapter);
  store.library = lib(["R-001"]);
  let threw = false;
  try { store.save(); } catch { threw = true; }
  check("save 失败：抛错且内存不变", threw && ids(store) === "R-001", ids(store));
}

// ---- 4. 契约不合规：在碰存储之前就该拒绝 ----
{
  const adapter = new FakeAdapter();
  const store = new LibraryStore(adapter);
  store.library = lib(["R-001"]);
  const broken = library_broken();
  let threw = false;
  try { store.commit(broken); } catch { threw = true; }
  check("commit 拒绝不合规库", threw);
  check("拒绝时未写存储", adapter.writes === 0, "writes=" + adapter.writes);
}

function library_broken() {
  const bad = rec("R-001");
  bad.confidence = "very-high";                 // 不在枚举内
  return { version: "0.1.0", generated_at: "2026-09-19", records: [bad] };
}

// ---- 5. 反驳入口同样走原子提交 ----
{
  const adapter = new FakeAdapter({ failOnWrite: true, seed: lib(["R-001"]) });
  const store = new LibraryStore(adapter);
  store.library = lib(["R-001"]);
  const refute = new RefutationController(store);
  let threw = false;
  try { refute.submit("R-001", "这条观察的条件写得过宽"); } catch { threw = true; }
  check("反驳在写失败时抛错", threw);
  check("反驳写失败后内存未污染", ids(store) === "R-001", ids(store));
}

console.log("\n通过 " + passed + " 项，失败 " + failed + " 项");
process.exit(failed ? 1 : 0);
