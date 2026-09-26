/**
 * 经验库排序：纯函数，显式规则 + 显式稳定排序。
 *
 * 为什么不用 Array.sort 直接排：同值记录的相对顺序必须保持"库内顺序"，
 * 否则每次重绘列表都会跳动 —— 用户会以为数据变了。这里显式用原索引兜底，
 * 不依赖具体引擎的排序稳定性。
 */

/** 可用排序模式（新增模式：改这里 + 视图里的标签表）。 */
export const SORT_MODES = ["order", "confidence", "linked"];

/** 置信度权重：低在前 —— 越不确定的档案越需要人先复核。 */
const CONFIDENCE_RANK = { low: 0, medium: 1, high: 2 };

/** 非法模式一律回落"库内顺序"，不抛错（URL 是用户可手改的）、不留空白列表。 */
export function normalizeSort(mode) {
  return SORT_MODES.includes(mode) ? mode : "order";
}

/**
 * @param {Array} records 已过滤的记录（顺序 = 库内顺序）
 * @param {string} mode 排序模式
 * @param {(rec: object) => number} linkedOf 取"被关联次数"，仅 linked 模式使用
 * @returns {Array} 新数组（不改动入参）
 */
export function sortRecords(records, mode = "order", linkedOf = () => 0) {
  const list = Array.isArray(records) ? records.slice() : [];
  const m = normalizeSort(mode);
  if (m === "order") return list;

  const pos = new Map(list.map((r, i) => [r, i]));
  const key = m === "confidence"
    ? (r) => {
      const rank = CONFIDENCE_RANK[r && r.confidence];
      return rank === undefined ? 3 : rank;   // 缺失/未知置信度排最后
    }
    : (r) => -linkedOf(r);                    // 被关联多的在前

  return list.slice().sort((a, b) => {
    const d = key(a) - key(b);
    return d !== 0 ? d : pos.get(a) - pos.get(b);
  });
}
