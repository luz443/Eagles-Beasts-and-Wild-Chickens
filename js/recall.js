import { DIMS } from "./contracts.js";

/** 召回：只做候选筛选与命中解释，不做语义判定（判定由 LearnBuddy 专家完成）。 */

function tokens(query) {
  const parts = String(query).match(/[A-Za-z0-9_.\-]+|[\u4e00-\u9fff]/g) || [];
  const out = [];
  for (let i = 0; i < parts.length; i++) {
    if (/^[\u4e00-\u9fff]$/.test(parts[i]) && i + 1 < parts.length && /^[\u4e00-\u9fff]$/.test(parts[i + 1])) {
      out.push(parts[i] + parts[i + 1]); i++;
    } else { out.push(parts[i]); }
  }
  // 丢单字 token：中文单字几乎没有区分度，留着会把"库内无相关记录"误报成有命中
  return out.filter((t) => t.length > 1);
}

export class RecallScorer {
  constructor() {
    // 缺省镜像，必须由 loadWeights() 从 contracts/scoring.json 覆盖，禁止两端各自硬编码。
    this.weights = { blocker: 3.0, attempt: 2.0, observation: 1.0, boundary: 1.0 };
  }

  loadWeights(scoring) {
    this.weights = Object.fromEntries(
      Object.entries(scoring.weights).map(([k, v]) => [k, Number(v)]));
  }

  score(query, record) {
    const fields = { blocker: record.blocker, attempt: record.attempt,
                     observation: record.observation, boundary: record.boundary };
    const qs = tokens(query);
    let total = 0; const explain = [];
    for (const [name, text] of Object.entries(fields)) {
      if (!text) continue;
      const hits = qs.filter(t => t && text.includes(t));
      if (!hits.length) continue;
      const w = this.weights[name] || 1.0;
      total += w * hits.length;
      explain.push(name + " 命中 " + hits.length + " 词（权重 " + w + "）");
    }
    return { recordId: record.id, score: total, explain };
  }

  recall(query, records, limit = 5) {
    const MIN = 1.0;
    return records.map(r => this.score(query, r))
      .filter(h => h.score >= MIN && h.explain.length)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
  }
}
