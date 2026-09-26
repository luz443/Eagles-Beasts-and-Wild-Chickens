/**
 * 立项检查（设计方案 5.2）——**主动质询**版。
 *
 * 原版只做「召回 → 给你看历史」。按设计方案附录 D.1 的 D5（审稿人 2 号），
 * 这里在展示历史之前先问一句：这个方向库内已有几次记录、主要卡在哪、还有几条结论
 * 没被验证？——请解释为什么认为这次会不同。
 *
 * 分工不能含糊：
 *   - 「N 次 / 卡在 X / M 条未验证」是**纯计数**，由网页算；
 *   - 「这次是否真的不同」是语义判断，只由专家写回（`challenge.challenges`，每条带证据编号）；
 *   - 网页既不猜语义，也不因为「失败过」就给方向下判决。
 */
import { ViewBase } from './base.js';
import { attributionLabel, esc, statusBadge } from '../util/html.js';
import { conditionsHtml } from '../util/conditions.js';
import { link, evidenceButton, nextAction, blockerGroups } from '../workflow.js';
import { groundedChallenges } from '../util/resurrection.js';

export class ProjectCheckView extends ViewBase {
  async render(params={}){
    this.el.innerHTML='<div class="page-heading"><div><span class="eyebrow">01 / BEFORE THE NEXT EXPERIMENT</span><h2>下一次尝试，从已有证据开始。</h2><p class="muted">检索历史尝试、核对适用边界，再决定需要验证什么。</p></div></div><section class="card"><label class="field-label" for="pc-q">研究方向 / 阻塞点</label><div class="toolbar"><div class="field-wide"><input id="pc-q" type="search" placeholder="例如：长序列训练显存怎么处理" value="'+esc(params.query||'')+'"></div><button id="pc-go" class="primary">检查历史经验</button></div><div class="query-examples">试一试：<button class="ghost" data-example="长序列训练显存">长序列显存</button><button class="ghost" data-example="数据版本">数据版本变更</button><button class="ghost" data-example="混合精度">混合精度</button></div><p class="muted small">按关键词召回候选；是否同因、是否冲突由专家复核。</p></section><div id="pc-result" aria-live="polite"></div>';
    const q=this.el.querySelector('#pc-q');this.el.querySelector('#pc-go').onclick=()=>this.runCheck(q.value);
    q.onkeydown=e=>{if(e.key==='Enter')this.runCheck(q.value);};
    this.el.querySelectorAll('[data-example]').forEach(b=>b.onclick=()=>{q.value=b.dataset.example;this.runCheck(q.value);});
    if(params.query)this.runCheck(params.query);
  }
  runCheck(query){
    const out=this.el.querySelector('#pc-result');this.context.app.updateRoute({query});
    if(!query.trim()){out.innerHTML='<p class="notice">请输入研究方向或阻塞点。</p>';return;}
    const hits=this.context.recall.recall(query,this.context.store.library.records);
    if(!hits.length){out.innerHTML=this.empty('没有相关记录。可以在专家侧记录这次尝试，再将档案导入经验库。',this.importAction());return;}
    const hitRecords=hits.map(h=>this.context.store.findById(h.recordId)).filter(Boolean);
    const ids=hits.slice(0,4).map(h=>h.recordId).join(',');
    out.innerHTML=this.challengeHtml(hitRecords)+'<div class="section-heading"><h3>'+hits.length+' 条可复核的历史线索</h3>'+link('compareMatrix',{ids},'对比这些档案 →')+'</div>'+hits.map(h=>{
      const r=this.context.store.findById(h.recordId);
      return '<article class="card check-card"><div class="section-heading"><span class="eyebrow">'+esc(r.id)+'</span>'+statusBadge(r.status)+'</div><h3>'+link('detail',{id:r.id},r.attempt)+'</h3><p>'+attributionLabel(r.attribution.type)+' '+esc(r.attribution.text)+'</p>'+conditionsHtml(r)+'<div class="evidence-excerpt"><small>原始观察</small><p>'+esc(r.observation)+'</p></div><p><b>适用边界</b> '+esc(r.boundary)+'</p><p class="next-action"><b>下一步核查</b> '+esc(nextAction(r))+'</p><details><summary>查看召回依据 · 排序分 '+h.score.toFixed(1)+'</summary><p class="small muted">'+esc(h.explain.join('；').replaceAll('blocker','阻塞点').replaceAll('attempt','尝试').replaceAll('observation','观察').replaceAll('boundary','边界'))+'。此分数不是可信度或成功概率。</p></details><div class="inline-actions">'+evidenceButton(r)+link('compareMatrix',{ids:r.id},'加入条件对比')+link('incubation',{blocker:r.blocker},'查看验证计划')+link('resurrection',{blocker:r.blocker},'查看该方向的已放弃记录')+'</div></article>';
    }).join('');
  }

  /**
   * 主动质询块。
   * 上半段是网页按库内证据算出来的计数（可能让人不舒服，但那正是重点）；
   * 下半段才消费专家写回的、带证据编号的质询。两边分开标注，不含糊。
   */
  challengeHtml(hitRecords){
    const groups = blockerGroups(hitRecords);
    const [blocker, rs] = groups[0] || [];
    const expertChallenges = groundedChallenges(hitRecords);
    if (!blocker) {
      if (!expertChallenges.length) return '';
      return '<section class="card challenge"><div class="section-heading"><h3>审稿人 2 号</h3><span class="badge accent">专家质询</span></div>' + this.challengeList(expertChallenges) + '</section>';
    }
    const unverified = rs.filter(r => (r.attribution || {}).type !== 'observed').length;
    const preface = '<p class="challenge-ask">这个方向库内已有 <b>' + rs.length + '</b> 次记录，主要卡在「' + esc(blocker) + '」，' +
      '其中 <b>' + unverified + '</b> 条结论尚未被验证。<b>请解释为什么认为这次会不同。</b></p>' +
      '<p class="small muted">以上数字由库内证据直接计数得到（人工纠错记录不计入）。' +
      '「这次是否真的不同」由专家复核后写回，网页不代替专家下结论。</p>';
    return '<section class="card challenge"><div class="section-heading"><h3>审稿人 2 号：先回答，再开工</h3>' +
      '<span class="badge accent">主动质询</span></div>' + preface +
      '<h3>专家写回的质询</h3>' +
      (expertChallenges.length ? this.challengeList(expertChallenges)
        : '<p class="muted">专家侧尚未写回针对该方向的质询。可请专家复核这些记录后再立项。</p>') +
      '<div class="inline-actions">' + link('resurrection', { blocker }, '这个方向放弃过什么 →') + '</div></section>';
  }

  /** 每条质询都必须显示它的证据编号——没有编号的质询根本不进这里（见 reviewer2.is_grounded）。 */
  challengeList(challenges){
    return '<ul class="challenge-list">' + challenges.map(c => '<li>' + esc(c.text) + ' <span class="small muted">证据 ' +
      c.evidence_ids.map(id => link('detail', { id }, id)).join(' ') + '</span></li>').join('') + '</ul>';
  }
}
