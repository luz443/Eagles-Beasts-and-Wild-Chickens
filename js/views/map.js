import { ViewBase } from './base.js';
import { esc } from '../util/html.js';
import { blockerGroups, hasBlocker, chainHtml, link, recordLinks } from '../workflow.js';
export class MapView extends ViewBase {
 async render(params={}){
  const all=this.context.store.library.records,groups=blockerGroups(all);
  const cells=items=>items.map(([b,rs])=>{const solved=rs.filter(r=>['已解决','已绕过'].includes(r.status)).length,quoted=rs.filter(r=>(r.evidence_refs||[]).length).length;return '<button class="map-cell" data-blocker="'+esc(b)+'" aria-pressed="'+(params.blocker===b)+'"><span class="map-count">'+String(rs.length).padStart(2,'0')+'<small> 次尝试</small></span><b class="map-label">'+esc(b)+'</b><span class="map-ratio">'+solved+'/'+rs.length+' 已解决或绕过 · '+quoted+' 条附引用</span><span class="map-date">'+esc(rs.map(r=>r.provenance.date).sort().at(-1))+' 更新</span></button>';}).join('');
  this.el.innerHTML='<div class="page-heading"><div><span class="eyebrow">02 / RESEARCH LANDSCAPE</span><h2>让反复遇到的问题，浮出水面。</h2><p class="muted">按尝试密度聚合；解决状态与引用完整度分开呈现，不以失败次数判定方向价值。</p></div></div><div class="section-heading"><h3>持续探索区</h3><span class="muted small">至少 2 次尝试</span></div><div class="map-grid">'+(cells(groups.filter(([,rs])=>rs.length>=2))||'<p>暂未积累重复尝试。</p>')+'</div><details class="card low-samples" '+(groups.some(([b,rs])=>b===params.blocker&&rs.length<2)?'open':'')+'><summary>低样本区 · '+groups.filter(([,rs])=>rs.length<2).length+' 个阻塞点</summary><p class="muted small">每个阻塞点仅有一条尝试，证据不足以形成假设。</p><div class="map-grid">'+cells(groups.filter(([,rs])=>rs.length<2))+'</div></details><section id="map-list" aria-live="polite"></section><details class="card"><summary>独立成功经验</summary><p class="muted">未声明阻塞点的记录单独收纳。</p>'+recordLinks(all.filter(r=>!hasBlocker(r)))+'</details>';
  this.el.querySelectorAll('[data-blocker]').forEach(b=>b.onclick=()=>this.select(b.dataset.blocker));
  if(params.blocker)this.select(params.blocker);
 }
 select(blocker){
  const rs=this.context.store.library.records.filter(r=>r.blocker===blocker&&!r.attempt.includes('人工纠错'));
  this.context.app.updateRoute({blocker});
  this.el.querySelectorAll('[data-blocker]').forEach(b=>{const active=b.dataset.blocker===blocker;b.classList.toggle('is-active',active);b.setAttribute('aria-pressed',String(active));});
  this.el.querySelector('#map-list').innerHTML='<section class="card"><span class="eyebrow">SELECTED THREAD / 研究轨迹</span><h3>'+esc(blocker)+'</h3>'+chainHtml(rs)+'<div class="inline-actions">'+link('compareMatrix',{ids:rs.slice(0,4).map(r=>r.id).join(',')},'对比这些尝试 →')+link('incubation',{blocker},'进入验证计划 →')+'</div></section>';
 }
}
