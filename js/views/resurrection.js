/**
 * 可重试方向（设计方案附录 D.1 的 S2「死实验复活」的网页落点）。
 *
 * 网页只做两件确定性的事：
 *   1. 筛出「已放弃且阻塞点明确」的记录（规则唯一真源见 util/resurrection.js，与 Python 同口径）；
 *   2. 把专家写回的 `resurrection.unblocks[]`（带编号与原文的解除依据）汇总展示。
 *
 * 「这条阻塞点到底有没有被解除」是语义判断，只由专家给出；网页不猜、也不因为
 * 「放弃过」就给方向下判决（设计方案 5.4 明确禁止用失败次数判方向死刑）。
 */
import { ViewBase } from './base.js';
import { esc } from '../util/html.js';
import { link, recordLinks, evidenceButton } from '../workflow.js';
import { isResurrectionCandidate, collectUnblocks } from '../util/resurrection.js';

export class ResurrectionView extends ViewBase {
  async render(params = {}) {
    const all = this.context.store.library.records || [];
    const unblocks = collectUnblocks(all);
    const candidates = all.filter(isResurrectionCandidate);
    const rows = candidates.filter(r => !params.blocker || r.blocker === params.blocker);
    const marked = candidates.filter(r => unblocks.has(r.id)).length;

    const head = '<div class="page-heading"><div><span class="eyebrow">05 / REOPEN THE ABANDONED</span>' +
      '<h2>把放弃过的方向，重新放回桌面。</h2>' +
      '<p class="muted">新档案入库时反向检查：它是否解除了某条已放弃记录的阻塞点。' +
      '这里只列出候选与专家写回的解除依据——是否真的可以重试，仍由专家判断。</p></div></div>';

    if (!candidates.length) {
      this.el.innerHTML = head +
        this.empty('库内暂无「已放弃且阻塞点明确」的记录。阻塞点写清楚的记录，才有被复活的可能。', this.importAction());
      return;
    }

    const summary = '<p class="notice">候选 <b>' + candidates.length + '</b> 条（已放弃且阻塞点非空），' +
      '其中 <b>' + marked + '</b> 条已标注解除依据。' +
      '「放弃过一次」不构成任何结论：多次尝试可能来自同一次实验的重复记录，也可能条件已经变了。</p>';

    const filtered = params.blocker && !rows.length
      ? '<p class="notice">没有阻塞点为「' + esc(params.blocker) + '」的已放弃记录。' +
        link('map', { blocker: params.blocker }, '查看该阻塞点的全部证据') + '</p>'
      : '';

    this.el.innerHTML = head + summary + filtered +
      rows.map(r => this.card(r, all, unblocks.get(r.id) || [], !params.blocker || params.blocker === r.blocker)).join('');
  }

  /** 单条候选：原始记录 + 解除依据 + 下一步入口。 */
  card(r, all, marks, open = false) {
    const sameBlocker = all.filter(x => x.blocker === r.blocker && x.id !== r.id);
    const status = marks.length
      ? '<span class="badge ok">已标注解除依据</span>'
      : '<span class="badge">待专家复核</span>';

    const basisHtml = marks.length
      ? marks.map(m => '<section class="evidence-excerpt"><b>' + esc(m.from) + ' 标记：已解除 ' + esc(m.record) + '</b>' +
          '<p>解除依据 ' + link('detail', { id: m.basis }, m.basis) + '</p>' +
          '<blockquote>' + esc(m.quote) + '</blockquote></section>').join('')
      : '<p class="muted">尚未标注解除依据。请把相关新记录交给专家复核，由专家写回带编号与原文的解除依据。</p>';

    const ids = [r.id].concat(marks.map(m => m.basis)).filter((v, i, a) => a.indexOf(v) === i).join(',');

    return '<details class="card" data-blocker="' + esc(r.blocker) + '"' + (open ? ' open' : '') + '>' +
      '<summary><span class="mono">' + esc(r.id) + '</span> ' + esc(r.blocker) + ' ' + status + '</summary>' +
      '<div class="hypothesis-body">' +
        '<p><b>尝试</b> ' + esc(r.attempt) + '</p>' +
        '<p><b>观察</b> ' + esc(r.observation) + '</p>' +
        '<p><b>放弃时的归因</b> ' + esc(r.attribution.text) + '（' + esc(r.attribution.type) + '）</p>' +
        '<p><b>适用边界</b> ' + esc(r.boundary) + '</p>' +
        (sameBlocker.length ? '<p><b>同一阻塞点的其他记录</b> ' + recordLinks(sameBlocker) + '</p>' : '') +
        '<h3>解除依据</h3>' + basisHtml +
        '<div class="inline-actions">' +
          link('projectCheck', { query: r.blocker }, '以该阻塞点做立项检查 →') +
          link('compareMatrix', { ids }, '对比条件差异') +
          evidenceButton(r) +
        '</div>' +
        '<p class="small muted">被解除 ≠ 可以照搬：请先核对条件维度（模型 / 序列长度 / 精度 / 硬件 / 数据版本 / 阶段）是否与当年一致。</p>' +
      '</div></details>';
  }
}
