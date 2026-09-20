/** 视图基类：统一挂载、销毁、空状态与错误状态。 */

import { esc } from "../util/html.js";

/** 入场动画结束时间：最晚一组错峰(180+60*5=480ms) + 动画时长(320ms)，留一点余量。 */
const ENTER_MS = 1000;

export class ViewBase {
  constructor(context) {
    this.context = context;
    this.el = null;
    this._enterTimer = null;
  }

  async mount(container, params = {}) {
    this.el = document.createElement("div");
    this.el.className = "view";
    container.innerHTML = "";
    container.appendChild(this.el);
    await this.render(params);
    this.playEntrance();
    return this;
  }

  /**
   * 播放一次入场序列。
   * 只在挂载时加 .is-entering，动画结束后摘掉 ——
   * 否则检索、筛选引起的重渲染会反复播放动画，看起来像闪屏。
   */
  playEntrance() {
    if (!this.el) return;
    this.el.classList.add("is-entering");
    clearTimeout(this._enterTimer);
    this._enterTimer = setTimeout(() => {
      if (this.el) this.el.classList.remove("is-entering");
    }, ENTER_MS);
  }

  async render(_params = {}) {
    this.el.innerHTML = '<div class="card"><h3>未实现</h3><p class="muted">此视图尚未实现。</p></div>';
  }

  destroy() {
    clearTimeout(this._enterTimer);
    if (this.el) this.el.remove();
  }

  /**
   * 空状态：必须给出明确的下一步动作（只说明"空"等于把问题丢回给用户）。
   * @param {string} text 说明文案（可能来自用户输入，需转义）
   * @param {string} actionHtml 动作按钮的 HTML（由调用方拼，内容需自行保证安全）
   */
  empty(text = "库为空", actionHtml = "") {
    return '<div class="card"><div class="empty">' +
      "<h3>这里还没有内容</h3>" +
      "<p>" + esc(text) + "</p>" +
      (actionHtml ? '<div class="empty-action">' + actionHtml + "</div>" : "") +
      "</div></div>";
  }

  /** 空库时的标准动作：导入库文件（由 main.js 的事件委托接住）。 */
  importAction() {
    return '<button type="button" class="primary js-import">导入库文件</button>';
  }
}
