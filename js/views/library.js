import { ViewBase } from "./base.js";
import { attributionLabel, confidenceBadge, esc, idBadge, statusBadge } from "../util/html.js";
import { normalizeSort, sortRecords } from "../util/sort.js";
import { overviewHtml } from './overview.js';
import { link, evidenceButton } from '../workflow.js';

/** 排序标签：键的顺序就是下拉里的选项顺序（"库内顺序"是默认，排第一）。 */
const SORT_LABELS = { order: "库内顺序", confidence: "置信度低在前", linked: "被关联多在前" };

/** 经验库：列表 + 关键词检索 + 按状态筛选 + 被关联次数。 */
export class LibraryView extends ViewBase {
  async render(params = {}) {
    const lib = this.context.store.library;
    const q = (params.query || "").trim();
    const statusFilter = params.status || "";
    const sort = normalizeSort(params.sort);
    const all = lib.records || [];
    let records = all;
    if (q) records = records.filter(r =>
      [r.attempt, r.blocker, r.observation, r.boundary].some(t => t && t.includes(q)));
    if (statusFilter) records = records.filter(r => r.status === statusFilter);
    // 先筛选缩小范围，再决定"先看哪一条"
    records = sortRecords(records, sort, (r) => this.context.store.linkedCount(r.id));

    if (!all.length) {
      // 空库不是"错误"，是"还没开始"——给出唯一下一步动作
      this.el.innerHTML = this.empty(
        "库里还没有任何档案。导入一份库文件（JSON）即可开始查阅、召回与复核。",
        this.importAction());
      return;
    }

    const toolbar = '<div class="card card--toolbar">' +
      '<div class="toolbar">' +
      '<div class="field field-wide">' +
      '<label class="field-label" for="lib-q">检索</label>' +
      '<input id="lib-q" type="search" placeholder="阻塞点 / 尝试 / 观察…" value="' + esc(q) + '" />' +
      "</div>" +
      '<div class="field">' +
      '<label class="field-label" for="lib-status">状态</label>' +
      '<select id="lib-status"><option value="">全部状态</option>' +
      ["进行中", "已放弃", "已绕过", "已解决"].map(s =>
        "<option" + (s === statusFilter ? " selected" : "") + ">" + s + "</option>").join("") +
      "</select></div>" +
      '<div class="field">' +
      '<label class="field-label" for="lib-sort">排序</label>' +
      '<select id="lib-sort">' +
      Object.keys(SORT_LABELS).map(v =>
        '<option value="' + v + '"' + (v === sort ? " selected" : "") + ">" +
        SORT_LABELS[v] + "</option>").join("") +
      "</select></div></div>" +
      '<p class="muted hits-summary" role="status" aria-live="polite">' +
      (q || statusFilter
        ? "命中 " + records.length + " 条，共 " + all.length + " 条档案"
        : "共 " + all.length + " 条档案") +
      (sort === "order" ? "" : " · 按「" + SORT_LABELS[sort] + "」") +
      "</p></div>";

    if (!records.length) {
      this.el.innerHTML = toolbar + this.empty(
        "没有匹配「" + q + "」的档案。换个关键词，或清空筛选看看全部档案。");
      this.bindToolbar();
      this.restoreQueryFocus();   // 也是重绘：不回焦的话，用户就没法接着改检索词了
      return;
    }

    const pageSize=12,page=Math.min(Math.max(1,Number(params.page)||1),Math.max(1,Math.ceil(records.length/pageSize)));
    const items = records.slice((page-1)*pageSize,page*pageSize).map((r, i) => {
      const linked = this.context.store.linkedCount(r.id);
      return '<article class="card card--record" data-id="' + esc(r.id) + '"' +
        ' data-status="' + esc(r.status) + '">' +
        '<span class="rec-rail" aria-hidden="true"></span>' +
        '<div class="rec-body">' +
        '<div class="rec-top">' +
        '<span class="rec-index" aria-hidden="true">' + String(i + 1).padStart(2, "0") + "</span>" +
        idBadge(r.id) +
        '<h3 class="rec-title"><button type="button" class="rec-open">' + esc(r.attempt) + "</button></h3>" +
        "</div>" +
        '<p class="rec-blocker">阻塞点：' + esc(r.blocker) + "</p>" +
        '<p class="rec-attr">' + attributionLabel((r.attribution || {}).type) + " " +
        esc((r.attribution || {}).text || "") + "</p>" +
        '<div class="rec-meta">' + statusBadge(r.status) + confidenceBadge(r.confidence) +
        '<span class="badge">被关联 ' + linked + " 次</span></div>" +
        '<div class="inline-actions">'+evidenceButton(r)+link('compareMatrix',{ids:r.id},'加入对比 →')+'</div>'+
        "</div></article>";
    }).join("");

    this.el.innerHTML = (!q&&!statusFilter?overviewHtml(this.context.store):'')+'<div class="section-heading"><div><span class="eyebrow">ARCHIVE INDEX</span><h2>研究档案</h2></div><span class="small muted">每条记录，保留当时的条件。</span></div>'+toolbar+'<div class="archive-grid">'+items+'</div>'+(records.length>pageSize?'<nav class="pagination" aria-label="档案分页">'+Array.from({length:Math.ceil(records.length/pageSize)},(_,i)=>'<button data-page="'+(i+1)+'"'+(i+1===page?' aria-current="page"':'')+'>'+(i+1)+'</button>').join('')+'</nav>':'');
    this.el.querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>{this.apply({...params,page:b.dataset.page});this.el.querySelector('#lib-q').scrollIntoView({block:'start'});});
    this.bindToolbar();
    this.restoreQueryFocus();

    this.el.querySelectorAll(".card--record").forEach(card => {
      card.addEventListener("click", e => {if(!e.target.closest('a,[data-evidence]'))this.open(card.dataset.id);});
    });
  }

  /**
   * 重绘会替换掉输入框节点，光标会丢 —— 打字打到一半失焦是真实的可用性缺陷，
   * 所以整列表重绘后把焦点与光标位置还原回检索框末尾。
   */
  restoreQueryFocus() {
    if (!this._refocusQuery) return;
    this._refocusQuery = false;
    const input = this.el.querySelector("#lib-q");
    if (!input) return;
    input.focus();
    const end = input.value.length;
    if (typeof input.setSelectionRange === "function") input.setSelectionRange(end, end);
  }

  /** 检索、筛选、排序：输入防抖 200ms，避免每敲一个字就整列表重绘。 */
  bindToolbar() {
    const input = this.el.querySelector("#lib-q");
    const sel = this.el.querySelector("#lib-status");
    const sortSel = this.el.querySelector("#lib-sort");
    if (!input || !sel || !sortSel) return;
    const state = () => ({ query: input.value, status: sel.value, sort: sortSel.value });
    input.addEventListener("compositionstart",()=>{this.composing=true;clearTimeout(this.searchTimer);});
    input.addEventListener("compositionend",()=>{this.composing=false;input.dispatchEvent(new Event('input'));});
    input.addEventListener("input", () => {
      if(this.composing)return;
      clearTimeout(this.searchTimer);
      this._refocusQuery = true;
      this.searchTimer = setTimeout(() => this.apply(state()), 200);
    });
    sel.addEventListener("change", () => this.apply(state()));
    sortSel.addEventListener("change", () => this.apply(state()));
  }

  /**
   * 状态变化：先写回地址栏（替换当前历史记录），再重绘。
   * 顺序不能反 —— 先同步 URL，重绘之后即使立刻刷新也能复原到同一状态。
   */
  apply(state) {
    this.context.app.updateRoute(state);
    return this.render(state);
  }

  open(id) {
    this.context.app.switchTo("detail", { id });
  }
  destroy(){clearTimeout(this.searchTimer);super.destroy();}
}
