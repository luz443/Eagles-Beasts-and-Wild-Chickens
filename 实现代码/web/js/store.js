import { PersistenceAdapter } from "./persist.js";
import { ContractValidator } from "./contracts.js";
import { SAMPLE_LIBRARY } from "../data/library.sample.js";

const SEP = "\u001f";

/** 「人工纠错」标记与目标编号正则：必须与 src/rra/library/refutation.py、src/rra/library/dedup.py 逐字一致。 */
const REF_MARKER = "人工纠错";
const REF_ID = /R-\d+/;

function isRefutation(rec) {
  return !!(rec && typeof rec.attempt === "string" && rec.attempt.includes(REF_MARKER));
}

/** 纠错记录专用键 = 标记 + 目标编号 + 归一化理由；取不到目标编号时返回 null（退回通用键）。 */
function refutationKey(rec, norm) {
  if (!isRefutation(rec)) return null;
  let target = "";
  for (const lk of (rec.links || [])) {
    if (lk && lk.relation === "冲突") { target = lk.target || ""; break; }
  }
  if (!target) { const m = REF_ID.exec(rec.attempt || ""); if (m) target = m[0]; }
  if (!target) return null;
  const reason = rec.observation || ((rec.attribution && rec.attribution.text) || "");
  return [norm(REF_MARKER), norm(target), norm(reason)].join(SEP);
}

/** 与 Python 侧 Deduplicator.key_of 逐字对齐：尝试 / 阻塞点 / 关键条件 / 关联产物，后两段排序。
 *  纠错记录走专用键（同目标不同理由不再撞键），普通记录语义一个字不改。 */
function dedupKey(rec) {
  const norm = (s) => String(s === undefined || s === null ? "" : s)
    .normalize("NFKC")
    .replace(/[，。！？、；：,.!?;:"'“”‘’（）()\[\]【】]+/g, "")
    .replace(/\s+/g, "")
    .toLowerCase();
  const ref = refutationKey(rec, norm);
  if (ref !== null) return ref;
  const conditions = [];
  for (const lk of (rec.links || [])) {
    for (const s of (lk.same || [])) conditions.push(s.dim + "=" + norm(s.value));
    for (const d of (lk.diff || [])) conditions.push(d.dim + ":" + norm(d.from) + "->" + norm(d.to));
  }
  const artifacts = (rec.artifacts || [])
    .filter(a => a && typeof a === "object")
    .map(a => norm(a.ref));
  const parts = [norm(rec.attempt), norm(rec.blocker),
    conditions.slice().sort().join(","),
    artifacts.slice().sort().join(",")].join(SEP);
  const own = Object.entries(rec.conditions || {}).map(([k,v])=>[k,String(v).normalize('NFKC').trim().replace(/\s+/g,' ').toLowerCase()]).sort(([a],[b])=>a<b?-1:a>b?1:0);
  return parts + (own.length ? SEP + JSON.stringify(own) : '');
}

/** 库状态与导入导出。合并规则与 Python 侧一致（同一契约、同一套去重键）。 */
export class LibraryStore {
  constructor(adapter = new PersistenceAdapter(), validator = new ContractValidator()) {
    this.adapter = adapter;
    this.validator = validator;
    this.library = { version: "0.1.0", generated_at: "", records: [] };
    this.listeners = [];
  }

  async load() {
    const local = this.adapter.read("library");
    if (local) {
      const issues=this.validator.validateLibrary(local);
      if(issues.length) throw new Error('本地库校验失败；请先导出备份并检查档案。');
      // Only upgrade untouched demonstration records; never infer conditions for user records.
      let changed=false;
      for(const r of local.records){
        const seed=SAMPLE_LIBRARY.records.find(s=>s.id===r.id);
        if(!r.conditions&&seed?.conditions&&r.provenance?.source==='模拟'){
          const withoutConditions=s=>JSON.stringify(Object.fromEntries(Object.entries(s).filter(([k])=>k!=='conditions').sort(([a],[b])=>a.localeCompare(b))));
          if(withoutConditions(r)===withoutConditions(seed)){r.conditions={...seed.conditions};changed=true;}
        }
      }
      if(changed)this.adapter.write('library',local);
      this.library = local;
      return this.library;
    }
    try {
      const res = await fetch("./data/library.sample.json");
      if (!res.ok) throw new Error('样例读取失败');
      this.library = await res.json();
    } catch {
      // fetch 不可用（file:// 打开 / 服务器未起）时回退到内联样例，
      // 保证「双击 index.html 也能看到库」，而不是白屏。
      this.library = SAMPLE_LIBRARY;
    }
    return this.library;
  }

  /**
   * 提交一个新库：**先落盘成功，才替换内存**。
   *
   * 为什么要这样（2026-09-19 外部审查 P1）：原实现在 importLibrary 里先 `this.library = next`
   * 再 `save()`。一旦 save 因配额/隐私模式抛错，内存已经是新库、存储还是旧库 ——
   * 调用方以为"失败了什么都没变"，实际内存被污染，之后任何一次保存都会把半截状态写出去。
   */
  commit(next) {
    const vs = this.validator.validateLibrary(next);
    if (vs.length) throw new Error("库未通过契约校验：" + vs.map(v => v.path).join("；"));
    this.adapter.write("library", next);      // 写失败会抛错，此时内存保持旧值
    this.library = next;
    this.lastWrite = JSON.stringify(next);
    this.emit();
    return next;
  }

  /** 保存当前内存态（等价于提交自己）。 */
  save() {
    return this.commit(this.library);
  }

  /** 其它标签页改动了库：整库替换后通知视图（跳过自己刚写的那次，避免回环）。 */
  adoptExternal(raw) {
    if (!raw || !Array.isArray(raw.records)) return false;
    const text = JSON.stringify(raw);
    if (text === this.lastWrite) return false;
    this.library = raw;
    this.emit();
    return true;
  }

  onChange(fn) { this.listeners.push(fn); }
  emit() { this.listeners.forEach(fn => fn(this.library)); }

  /** 导入：合并、去重、冲突重编号并记录 remap_from，返回前后对比提示。 */
  importLibrary(rawJson) {
    let incoming;
    try { incoming = typeof rawJson === "string" ? JSON.parse(rawJson) : rawJson; }
    catch (e) { throw new Error("不是合法 JSON：" + e.message); }
    const vs = this.validator.validateLibrary(incoming);
    if (vs.length) throw new Error("导入文件未通过契约校验：" + vs.map(v => v.path).join("；"));

    // 先算出合并结果，全部成功后再整体替换。
    // 原实现边 push 边 save：save 校验失败时内存已被改脏，而调用方以为"内存未受影响"。
    const report = { added: [], duplicated: [], renumbered: {} };
    const next = JSON.parse(JSON.stringify(this.library));
    const knownKeys = new Set(next.records.map(dedupKey));
    const knownIds = new Set(next.records.map(r => r.id));
    const maxNo = () => Math.max(0, ...[...knownIds].map(id => parseInt(id.slice(2), 10) || 0));

    for (const rec of incoming.records) {
      const key = dedupKey(rec);
      if (knownKeys.has(key)) { report.duplicated.push(rec.id); continue; }
      knownKeys.add(key);
      const clone = JSON.parse(JSON.stringify(rec));
      if (knownIds.has(clone.id)) {
        const newId = "R-" + String(maxNo() + 1).padStart(3, "0");
        report.renumbered[clone.id] = newId;
        clone.id = newId;
        clone.provenance = clone.provenance || {};
        clone.provenance.remap_from = rec.id;
      }
      knownIds.add(clone.id);
      next.records.push(clone);
      report.added.push(clone.id);
    }

    const postVs = this.validator.validateLibrary(next);
    if (postVs.length) {
      throw new Error("导入后库未通过契约校验（已回滚，内存未改动）："
        + postVs.map(v => v.path).join("；"));
    }
    this.commit(next);        // 先落盘、成功才替换内存；写失败时内存保持旧库
    return report;
  }

  exportLibrary() {
    return JSON.stringify(this.library, null, 2);
  }

  findById(id) {
    return this.library.records.find(r => r.id === id) || null;
  }

  /** 被关联次数：派生指标，从 links[].target 统计，不写入档案。 */
  linkedCount(id) {
    return this.library.records.reduce(
      (n, r) => n + (r.links || []).filter(l => l.target === id).length, 0);
  }
}
