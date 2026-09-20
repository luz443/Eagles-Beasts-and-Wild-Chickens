/** 反驳入口：把「这个判断不对」变成一条人工纠错档案，并写入本地库。
 * 反驳不覆盖原判断（append-only），对应 nanopublication 的「撤回不删除」。 */

export class RefutationController {
  constructor(store) {
    this.store = store;
  }

  submit(recordId, reason) {
    if (!reason || reason.trim().length < 4) {
      throw new Error("反驳理由太短，请写清哪里不对");
    }
    const target = this.store.findById(recordId);
    if (!target) throw new Error("档案不存在：" + recordId);
    // 引用片段必须真的存在且够长（契约要求 ≥4 字符），否则这条记录本身就不合法，
    // 会让整库校验失败、库永远存不下去。逐级回退到 observation / blocker。
    const quote = [target.attribution && target.attribution.text, target.observation, target.blocker]
      .map((t) => String(t || "")).find((t) => t.trim().length >= 4);
    if (!quote) {
      throw new Error("目标档案没有可引用的原文片段（至少 4 字符），无法生成带证据的纠错记录");
    }
    const maxNo = Math.max(0, ...this.store.library.records.map(r => parseInt(r.id.slice(2), 10) || 0));
    const rec = {
      id: "R-" + String(maxNo + 1).padStart(3, "0"),
      attempt: "对 " + recordId + " 的人工纠错",
      expectation: "修正 " + recordId + " 的判断",
      observation: reason.trim(),
      blocker: target.blocker,
      attribution: { text: "人工纠错：" + reason.trim(), type: "observed" },
      // boundary 是必填且必须非空——人工纠错也要写清适用边界
      boundary: "仅针对 " + recordId + " 的判断，不改变其原始记录",
      confidence: "medium",
      status: "进行中",
      missing_info: [],
      artifacts: [],
      links: [{ target: recordId, relation: "冲突", same: [], diff: [], transferable: "" }],
      evidence_refs: [{ record: recordId, quote: quote.slice(0, 120) }],
      version: 1,
      // 人工纠错是**真实**输入（不是模拟数据），来源必须如实标注
      provenance: { author: "人工纠错", date: new Date().toISOString().slice(0, 10), source: "真实" },
    };
    // 先整体校验再落库：不留半成品（store.importLibrary 用同一种原子写法）
    const next = JSON.parse(JSON.stringify(this.store.library));
    next.records.push(rec);
    const vs = this.store.validator.validateLibrary(next);
    if (vs.length) {
      throw new Error("纠错记录未通过契约校验，已放弃写入：" + vs.map(v => v.path).join("；"));
    }
    this.store.commit(next);   // 先落盘、成功才替换内存（与 store.importLibrary 同一套原子写法）
    return rec.id;
  }

  listFor(recordId) {
    return this.store.library.records.filter(
      r => (r.links || []).some(l => l.target === recordId && r.attempt.includes("人工纠错")));
  }

  /** 纠错记录不应被当作孵化假设的支撑材料——它们不是"尝试"。 */
  static isRefutation(rec) {
    return !!(rec && typeof rec.attempt === "string" && rec.attempt.includes("人工纠错"));
  }
}
