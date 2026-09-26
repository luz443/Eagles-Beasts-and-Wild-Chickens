/** 共用小工具：HTML 转义与徽标。原先 5 个视图各写一份 esc，容易只改一处。 */

export function esc(s) {
  return String(s === undefined || s === null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/** 状态徽标：颜色由状态决定，文案原样展示（底色 + 文字双承载，不靠颜色单独表意）。 */
export function statusBadge(status) {
  return '<span class="badge st-' + esc(status) + '">' + esc(status) + "</span>";
}

/** 档案编号徽标：等宽数字，便于纵向对齐。 */
export function idBadge(id) {
  return '<span class="badge id accent">' + esc(id) + "</span>";
}

/**
 * 归因类型标签：假设与已观察必须一眼可分。
 * 区分手段有三重 —— 文案（已观察 / 归因假设）、底色（绿 / 赭）、线型（实线 / 虚线），
 * 色盲用户与黑白打印都不会误读。样式在 components.css，函数只负责给类名。
 */
export function attributionLabel(type) {
  return type === "observed"
    ? '<span class="badge attr-observed">已观察</span>'
    : '<span class="badge attr-assumption">归因假设</span>';
}

/** 置信度徽标：low / medium / high → 中文，避免界面里冒出英文枚举值。 */
export function confidenceBadge(confidence) {
  const label = { low: "低", medium: "中", high: "高" }[confidence] || String(confidence || "—");
  return '<span class="badge">置信度 ' + esc(label) + "</span>";
}
