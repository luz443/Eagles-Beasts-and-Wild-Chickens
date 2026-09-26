/**
 * 死实验复活的候选规则（网页侧）。
 *
 * 规则的唯一真源在 Python：`src/rra/skills/resurrection.py::ResurrectionSkill.candidates`
 * ——「已放弃」且「阻塞点非空」的记录才进入可重试候选。
 *
 * 为什么单独抽一个文件：这条规则不是数据结构（schema 管不到），而是**行为约定**。
 * 若只在一端改字面量，两端口径会静默分叉：网页把某条列为可重试，专家侧却不认。
 * 所以两端各放一个测试盯着同一份字面量（见 web/tests/resurrection-rule-parity.mjs）。
 */

export const RESURRECTION_STATUS = "已放弃";

/** 单条记录是否为「可重试」候选。只做确定性筛选，不做任何语义推断。 */
export function isResurrectionCandidate(record) {
  if (!record || typeof record !== "object") return false;
  if (record.status !== RESURRECTION_STATUS) return false;
  const blocker = record.blocker === undefined || record.blocker === null ? "" : String(record.blocker);
  return blocker.trim().length > 0;
}

/** 从库里筛出全部可重试候选（保持库内原有顺序）。 */
export function resurrectionCandidates(records) {
  return (Array.isArray(records) ? records : []).filter(isResurrectionCandidate);
}

/**
 * 从全库汇总「解除记录」：某条档案的 `resurrection.unblocks[]` 声明它解除了谁。
 *
 * 返回 `Map<被解除的编号, 解除项[]>`。纯派生，不改动档案本身——
 * 与「被关联次数」同一约定：派生指标不写回档案，避免两份真源。
 */
export function collectUnblocks(records) {
  const out = new Map();
  for (const rec of Array.isArray(records) ? records : []) {
    if (!rec || typeof rec !== "object") continue;
    const block = rec.resurrection;
    if (!block || typeof block !== "object" || Array.isArray(block)) continue;
    for (const item of Array.isArray(block.unblocks) ? block.unblocks : []) {
      if (!item || typeof item !== "object" || Array.isArray(item)) continue;
      const target = item.record;
      if (typeof target !== "string" || !target) continue;
      if (!out.has(target)) out.set(target, []);
      out.get(target).push({ ...item, from: rec.id });
    }
  }
  return out;
}

/**
 * 从一批记录里收集「审稿人 2 号」质询，并丢掉没有证据编号的条目。
 *
 * 与 Python 侧 `src/rra/skills/reviewer2.py::is_grounded` 同一口径：
 * `evidence_ids` 非空且每一项都匹配 R-### 才算合格。
 */
const EVIDENCE_ID_RE = /^R-[0-9]{3,}$/;

export function groundedChallenges(records) {
  const out = [];
  for (const rec of Array.isArray(records) ? records : []) {
    if (!rec || typeof rec !== "object") continue;
    const block = rec.challenge;
    if (!block || typeof block !== "object" || Array.isArray(block)) continue;
    for (const item of Array.isArray(block.challenges) ? block.challenges : []) {
      if (!item || typeof item !== "object" || Array.isArray(item)) continue;
      const ids = Array.isArray(item.evidence_ids) ? item.evidence_ids : [];
      if (!ids.length || !ids.every(i => typeof i === "string" && EVIDENCE_ID_RE.test(i))) continue;
      out.push({ text: item.text, evidence_ids: ids, from: rec.id });
    }
  }
  return out;
}
