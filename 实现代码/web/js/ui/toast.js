/**
 * 轻提示（toast）：替代 alert()。
 *
 * 为什么不用 alert：原生弹窗会打断操作流、样式不可控、无法承载"导入明细"这类结构化结果，
 * 而且在部分浏览器里会阻塞主线程。这里用页面内的轻提示，配合 aria-live 让屏幕阅读器也能听到。
 */

const DEFAULT_DURATION = 6000;
const MAX_VISIBLE = 3;

function container() {
  let el = document.getElementById("toast-stack");
  if (!el) {
    // 兜底：HTML 里没写容器也不至于报错（例如测试环境直接调本模块）
    el = document.createElement("div");
    el.id = "toast-stack";
    el.className = "toast-stack";
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");
    document.body.appendChild(el);
  }
  return el;
}

/**
 * 弹出一条轻提示。
 * @param {string} message 正文文案
 * @param {{tone?: "info"|"ok"|"danger", duration?: number}} options
 */
export function toast(message, options = {}) {
  const tone = options.tone || "info";
  const duration = options.duration === undefined ? DEFAULT_DURATION : options.duration;
  const box = container();

  // 超过上限先挤掉最旧的，避免刷屏
  while (box.children.length >= MAX_VISIBLE) box.removeChild(box.firstElementChild);

  const el = document.createElement("div");
  el.className = "toast" + (tone === "ok" ? " toast--ok" : tone === "danger" ? " toast--danger" : "");

  const text = document.createElement("span");
  text.textContent = message;            // 用户输入/文件名可能进来，一律 textContent
  el.appendChild(text);

  const close = document.createElement("button");
  close.type = "button";
  close.className = "ghost";
  close.setAttribute("aria-label", "关闭提示");
  close.textContent = "关闭";
  close.addEventListener("click", () => el.remove());
  el.appendChild(close);

  box.appendChild(el);

  if (duration > 0) {
    const timer = setTimeout(() => el.remove(), duration);
    // 鼠标停留在提示上时暂缓消失，方便阅读长文案
    el.addEventListener("mouseenter", () => clearTimeout(timer));
  }
  return el;
}
