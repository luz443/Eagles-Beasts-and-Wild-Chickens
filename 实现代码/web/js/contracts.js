/** 契约层（浏览器侧）：与 contracts/record.schema.json 和 Python 侧保持一致。 */

export const DIMS = [
  "model", "seq_len", "batch", "micro_batch", "precision",
  "hardware", "dataset_version", "stage", "framework",
];

export const DIM_LABELS = {
  model: "模型", seq_len: "序列长度", batch: "批大小", micro_batch: "微批大小",
  precision: "精度", hardware: "硬件", dataset_version: "数据版本",
  stage: "阶段", framework: "框架",
};

export const RELATIONS = ["重复", "相似", "冲突"];
export const ATTRIBUTION_TYPES = ["assumption", "observed"];
export const CONFIDENCE = ["high", "medium", "low"];
export const STATUSES = ["进行中", "已放弃", "已绕过", "已解决"];

const ID_RE = /^R-[0-9]{3,}$/;
const QUOTE_MIN = 4;

// 列表型字段：既要是数组，元素也要是对象。缺一个就会把校验器打崩（外部审查 P1）。
const LIST_FIELDS = ["links", "evidence_refs", "artifacts", "missing_info"];

// 引文允许取自被引用档案的哪些字段——必须与 Python 侧 QUOTABLE_FIELDS 逐项一致，
// 也必须与 refute.js 取引文的位置一致，否则会制造新的跨端分叉。
const QUOTABLE_FIELDS = ["attribution.text", "observation", "blocker"];

/** 与去重指纹同一套规范化（NFKC + 去标点 + 去空白 + 小写）：三处实现必须同口径。 */
function normText(value) {
  return String(value === undefined || value === null ? "" : value)
    .normalize("NFKC")
    .replace(/[，。！？、；：,.!?;:"'“”‘’（）()\[\]【】]+/g, "")
    .replace(/\s+/g, "")
    .toLowerCase();
}

/** 宽容取数组：非数组一律当空数组（类型问题由 validateArchive 负责报出）。 */
function asList(value) {
  return Array.isArray(value) ? value : [];
}

function isPlainObject(value) {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

/** 被引用档案里可用于复核的原文（三个字段各自独立比对，不跨字段拼接）。 */
function quotableTextOf(archive) {
  const attr = archive.attribution;
  const text = isPlainObject(attr) ? attr.text : "";
  return [text, archive.observation, archive.blocker].map(v => (v === undefined || v === null ? "" : String(v)));
}

/** 引文是否真的出现在目标档案的可核验字段里；空引文一律不匹配（否则 "" 恒真）。 */
function quoteMatches(quote, target) {
  const q = normText(quote);
  if (!q) return false;
  return quotableTextOf(target).some(field => normText(field).includes(q));
}

const REQUIRED_TOP = ["id", "attempt", "expectation", "observation", "blocker",
  "attribution", "boundary", "confidence", "status", "provenance"];
const ALLOWED_TOP = new Set(["id", "attempt", "expectation", "observation", "blocker",
  "attribution", "missing_info", "boundary", "confidence", "status", "artifacts",
  "links", "evidence_refs", "dedup_key", "version", "provenance", "conditions",
  "resurrection", "challenge"]);
const STRING_REQUIRED = ["id", "attempt", "expectation", "observation", "blocker", "boundary"];
const SOURCES = ["真实", "模拟"];

export class ContractValidator {
  /** 只做确定性校验：必填、枚举、格式。任何一条违规都要给出字段路径。 */
  validateArchive(raw) {
    const out = [];
    if (!raw || typeof raw !== "object") return [{ path: "$", reason: "不是对象", expected: "object" }];
    for (const key of REQUIRED_TOP) {
      const v = raw[key];
      if (v === undefined || v === null || (typeof v === "string" && !v.trim())) {
        out.push({ path: key, reason: "必填字段缺失或为空", expected: "非空 " + key });
      }
    }
    // 声明了 additionalProperties: false 就必须执行，否则契约形同虚设
    for (const key of Object.keys(raw)) {
      if (!ALLOWED_TOP.has(key)) {
        out.push({ path: key, reason: "出现契约未声明的字段", expected: "只允许契约内的字段" });
      }
    }
    if (raw.conditions !== undefined) {
      if (!isPlainObject(raw.conditions)) out.push({path:'conditions',reason:'不是对象',expected:'object'});
      else for (const [dim,value] of Object.entries(raw.conditions)) {
        if (!DIMS.includes(dim))out.push({path:'conditions.'+dim,reason:'条件维度不合法',expected:'九维枚举'});
        if (typeof value !== 'string' || !value.length)out.push({path:'conditions.'+dim,reason:'条件取值不合法',expected:'非空字符串'});
      }
    }
    // 死实验复活（S2）与审稿人 2 号（D5）：档案侧各带一个可选对象。
    // 形状检查在这里，跨档案检查放在 validateLibrary —— 与 Python 侧一一对应。
    if (raw.resurrection !== undefined && raw.resurrection !== null) {
      out.push(...this.checkResurrection(raw.resurrection));
    }
    if (raw.challenge !== undefined && raw.challenge !== null) {
      out.push(...this.checkChallenge(raw.challenge));
    }
    for (const key of STRING_REQUIRED) {
      const v = raw[key];
      if (v !== undefined && v !== null && typeof v !== "string") {
        out.push({ path: key, reason: "字段类型不是字符串", expected: "string" });
      }
    }
    if (raw.id && !ID_RE.test(raw.id)) {
      out.push({ path: "id", reason: "编号格式不合法", expected: "R-###" });
    }
    const rawAttr = raw.attribution;
    // 与 Python 侧一致：父对象缺失或类型不对时**不下探**子字段，
    // 否则缺一个 attribution 会级联报出 attribution.type / attribution.text，两端结论不同。
    if (rawAttr !== undefined && rawAttr !== null
        && (typeof rawAttr !== "object" || Array.isArray(rawAttr))) {
      out.push({ path: "attribution", reason: "不是对象", expected: "object" });
    } else if (rawAttr && typeof rawAttr === "object") {
      if (!ATTRIBUTION_TYPES.includes(rawAttr.type)) {
        out.push({ path: "attribution.type", reason: "归因类型不在枚举内", expected: "assumption / observed" });
      }
      if (typeof rawAttr.text !== "string" || !rawAttr.text.trim()) {
        out.push({ path: "attribution.text", reason: "归因文本为空", expected: "非空字符串" });
      }
    }
    if (!CONFIDENCE.includes(raw.confidence)) {
      out.push({ path: "confidence", reason: "置信度不在枚举内", expected: "high/medium/low" });
    }
    if (!STATUSES.includes(raw.status)) {
      out.push({ path: "status", reason: "状态不在枚举内", expected: STATUSES.join(" / ") });
    }
    const rawProv = raw.provenance;
    if (rawProv !== undefined && rawProv !== null
      && (typeof rawProv !== "object" || Array.isArray(rawProv))) {
      out.push({ path: "provenance", reason: "不是对象", expected: "object" });
    } else if (rawProv && typeof rawProv === "object") {
      for (const key of ["author", "date"]) {
        if (typeof rawProv[key] !== "string" || !rawProv[key].trim()) {
          out.push({ path: "provenance." + key, reason: "来源信息缺失", expected: "非空字符串" });
        }
      }
      if (!SOURCES.includes(rawProv.source)) {
        out.push({ path: "provenance.source", reason: "数据来源不在枚举内", expected: "真实 / 模拟" });
      }
    }
    // 列表型字段的结构检查必须在前：否则 `links: "bad"` 会被当成字符串处理、
    // `links: [null]` 会在下面 lk.relation 上抛 TypeError（外部审查 P1 的最小复现）。
    for (const field of LIST_FIELDS) {
      const value = raw[field];
      if (value !== undefined && value !== null && !Array.isArray(value)) {
        out.push({ path: field, reason: "不是列表", expected: "list" });
      }
    }
    asList(raw.links).forEach((lk, i) => {
      if (!isPlainObject(lk)) {
        out.push({ path: `links[${i}]`, reason: "元素不是对象", expected: "object" });
        return;
      }
      if (!RELATIONS.includes(lk.relation)) {
        out.push({ path: `links[${i}].relation`, reason: "关系不在枚举内", expected: RELATIONS.join(" / ") });
      }
      if (lk.target && !ID_RE.test(lk.target)) {
        out.push({ path: `links[${i}].target`, reason: "目标编号格式不合法", expected: "R-###" });
      }
      for (const key of ["same", "diff"]) {
        const value = lk[key];
        if (value !== undefined && value !== null && !Array.isArray(value)) {
          out.push({ path: `links[${i}].${key}`, reason: "不是列表", expected: "list" });
        }
        asList(value).forEach((d, j) => {
          if (!isPlainObject(d)) {
            out.push({ path: `links[${i}].${key}[${j}]`, reason: "元素不是对象", expected: "object" });
            return;
          }
          if (!this.dimIsEnum(d.dim)) {
            out.push({ path: `links[${i}].${key}[${j}].dim`, reason: "条件维度不是枚举值", expected: "九维枚举之一" });
          }
        });
      }
    });
    asList(raw.evidence_refs).forEach((ref, i) => {
      if (!isPlainObject(ref)) {
        out.push({ path: `evidence_refs[${i}]`, reason: "元素不是对象", expected: "object" });
        return;
      }
      if (!ID_RE.test(ref.record || "")) {
        out.push({ path: `evidence_refs[${i}].record`, reason: "证据编号格式不合法", expected: "R-###" });
      }
      // 与 Python 侧一致：按**原串**长度判（不 trim），避免两端漂移
      if (typeof ref.quote !== "string") {
        out.push({ path: `evidence_refs[${i}].quote`, reason: "原文片段不是字符串", expected: "string" });
      } else if (ref.quote.length < QUOTE_MIN) {
        out.push({ path: `evidence_refs[${i}].quote`, reason: "原文片段过短", expected: "至少 " + QUOTE_MIN + " 字符" });
      }
    });
    return out;
  }

  /** resurrection：unblocks[] 的 record/basis 必须是 R-###，quote 必须够长可复核。 */
  checkResurrection(raw) {
    const out = [];
    if (!isPlainObject(raw)) return [{ path: "resurrection", reason: "不是对象", expected: "object" }];
    if (raw.unblocks === undefined || raw.unblocks === null) return out;
    if (!Array.isArray(raw.unblocks)) {
      return [{ path: "resurrection.unblocks", reason: "不是列表", expected: "list" }];
    }
    raw.unblocks.forEach((item, i) => {
      const base = `resurrection.unblocks[${i}]`;
      if (!isPlainObject(item)) {
        out.push({ path: base, reason: "元素不是对象", expected: "object" });
        return;
      }
      for (const [key, label] of [["record", "被解除的档案编号"], ["basis", "解除依据的档案编号"]]) {
        if (!ID_RE.test(item[key] === undefined || item[key] === null ? "" : String(item[key]))) {
          out.push({ path: base + "." + key, reason: label + "格式不合法", expected: "R-###" });
        }
      }
      if (typeof item.quote !== "string") {
        out.push({ path: base + ".quote", reason: "原文片段不是字符串", expected: "string" });
      } else if (item.quote.length < QUOTE_MIN) {
        out.push({
          path: base + ".quote", reason: "原文片段过短，无法复核",
          expected: `至少 ${QUOTE_MIN} 个字符的原文摘录`,
        });
      }
    });
    return out;
  }

  /** challenge：每条质询必须有非空的 evidence_ids，且每项都是 R-###（见 reviewer2.is_grounded）。 */
  checkChallenge(raw) {
    const out = [];
    if (!isPlainObject(raw)) return [{ path: "challenge", reason: "不是对象", expected: "object" }];
    if (raw.challenges === undefined || raw.challenges === null) return out;
    if (!Array.isArray(raw.challenges)) {
      return [{ path: "challenge.challenges", reason: "不是列表", expected: "list" }];
    }
    raw.challenges.forEach((item, i) => {
      const base = `challenge.challenges[${i}]`;
      if (!isPlainObject(item)) {
        out.push({ path: base, reason: "元素不是对象", expected: "object" });
        return;
      }
      if (typeof item.text !== "string" || !item.text.trim()) {
        out.push({ path: base + ".text", reason: "质询内容为空", expected: "非空字符串" });
      }
      if (!Array.isArray(item.evidence_ids) || item.evidence_ids.length === 0) {
        out.push({
          path: base + ".evidence_ids", reason: "缺少证据编号（无出处的质询不得进库）",
          expected: "至少一个 R-### 编号",
        });
        return;
      }
      item.evidence_ids.forEach((one, j) => {
        if (typeof one !== "string" || !ID_RE.test(one)) {
          out.push({
            path: `${base}.evidence_ids[${j}]`, reason: "证据编号格式不合法", expected: "R-###",
          });
        }
      });
    });
    return out;
  }

  validateLibrary(raw) {
    if (!raw || !Array.isArray(raw.records)) {
      return [{ path: "records", reason: "缺少档案列表", expected: "array" }];
    }
    const out = [];
    const seen = new Set();
    raw.records.forEach((rec, i) => {
      // 畸形元素必须报违规，而不是把校验器打崩
      if (!rec || typeof rec !== "object" || Array.isArray(rec)) {
        out.push({ path: `records[${i}]`, reason: "元素不是对象", expected: "object" });
        return;
      }
      this.validateArchive(rec).forEach(v => out.push({ ...v, path: `records[${i}].` + v.path }));
      if (seen.has(rec.id)) out.push({ path: `records[${i}].id`, reason: "编号重复", expected: "唯一" });
      seen.add(rec.id);
    });
    const ids = new Set(raw.records.filter(r => r && typeof r === "object").map(r => r.id));
    const byId = new Map(raw.records.filter(r => isPlainObject(r)).map(r => [r.id, r]));
    raw.records.forEach((rec, i) => {
      if (!isPlainObject(rec)) return;
      asList(rec.links).forEach((lk, j) => {
        if (isPlainObject(lk) && lk.target && !ids.has(lk.target)) {
          out.push({ path: `records[${i}].links[${j}].target`, reason: "指向的档案不存在", expected: "库内编号" });
        }
      });
      // Python 侧校验了「引用指向的档案存在」；这里还要同步「引文可复核」（外部审查 P0）：
      // 引文必须真的出现在被引用档案的可核验字段里 —— 否则编造 4 个字也能通过，
      // 「证据必须带原文片段」这条铁律在代码层就是空的。
      asList(rec.evidence_refs).forEach((ref, j) => {
        if (!isPlainObject(ref) || !ref.record) return;
        if (!ids.has(ref.record)) {
          out.push({ path: `records[${i}].evidence_refs[${j}].record`, reason: "引用的档案不存在", expected: "库内编号" });
          return;
        }
        const target = byId.get(ref.record);
        if (!target || typeof ref.quote !== "string" || !ref.quote.trim()) return;
        if (!quoteMatches(ref.quote, target)) {
          out.push({
            path: `records[${i}].evidence_refs[${j}].quote`,
            reason: "引文在被引用档案里找不到（不可复核）",
            expected: `该档案的 ${QUOTABLE_FIELDS.join(" / ")} 中真实存在的原文片段`,
          });
        }
      });
      // 死实验复活的解除依据同样必须可复核：依据指向的档案要存在，
      // 且 quote 必须能在**依据档案**里找到（与 evidence_refs 同一铁律）。
      const unblocks = isPlainObject(rec.resurrection) ? asList(rec.resurrection.unblocks) : [];
      unblocks.forEach((item, j) => {
        if (!isPlainObject(item)) return;   // 元素类型问题由 validateArchive 报出
        const unblocked = item.record === undefined || item.record === null ? "" : String(item.record);
        const basis = item.basis === undefined || item.basis === null ? "" : String(item.basis);
        if (unblocked && !ids.has(unblocked)) {
          out.push({
            path: `records[${i}].resurrection.unblocks[${j}].record`,
            reason: "被解除的档案不存在", expected: "指向库内编号之一",
          });
        }
        if (basis && !ids.has(basis)) {
          out.push({
            path: `records[${i}].resurrection.unblocks[${j}].basis`,
            reason: "解除依据的档案不存在", expected: "指向库内编号之一",
          });
          return;
        }
        const basisRec = byId.get(basis);
        if (!basisRec || typeof item.quote !== "string" || !item.quote.trim()) return;
        if (!quoteMatches(item.quote, basisRec)) {
          out.push({
            path: `records[${i}].resurrection.unblocks[${j}].quote`,
            reason: "解除依据的引文在依据档案里找不到（不可复核）",
            expected: `依据档案的 ${QUOTABLE_FIELDS.join(" / ")} 中真实存在的原文片段`,
          });
        }
      });
    });
    return out;
  }

  dimIsEnum(value) {
    return DIMS.includes(value);
  }

  /** 去重指纹（与 store.js / Python Deduplicator 三方必须同口径；供一致性测试调用）。 */
  dedupKeyForParity(rec) {
    const SEP = "\u001f";
    const norm = normText;      // 与引文核验共用同一套规范化，避免"两处各写一遍"再度分叉
    const conditions = [];
    for (const lk of (rec.links || [])) {
      for (const s of (lk.same || [])) conditions.push(s.dim + "=" + norm(s.value));
      for (const d of (lk.diff || [])) conditions.push(d.dim + ":" + norm(d.from) + "->" + norm(d.to));
    }
    const artifacts = (rec.artifacts || []).filter(a => a && typeof a === "object").map(a => norm(a.ref));
    const parts = [norm(rec.attempt), norm(rec.blocker),
      conditions.slice().sort().join(","), artifacts.slice().sort().join(",")].join(SEP);
    const own = Object.entries(rec.conditions || {}).map(([k,v])=>[k,String(v).normalize('NFKC').trim().replace(/\s+/g,' ').toLowerCase()]).sort(([a],[b])=>a<b?-1:a>b?1:0);
    return parts + (own.length ? SEP + JSON.stringify(own) : '');
  }
}
