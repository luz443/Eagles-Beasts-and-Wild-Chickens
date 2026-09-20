import { ViewBase } from './base.js';
import { attributionLabel, esc, statusBadge } from '../util/html.js';
import { conditionsHtml } from '../util/conditions.js';
import { link, evidenceButton, nextAction } from '../workflow.js';
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
    const ids=hits.slice(0,4).map(h=>h.recordId).join(',');
    out.innerHTML='<div class="section-heading"><h3>'+hits.length+' 条可复核的历史线索</h3>'+link('compareMatrix',{ids},'对比这些档案 →')+'</div>'+hits.map(h=>{
      const r=this.context.store.findById(h.recordId);
      return '<article class="card check-card"><div class="section-heading"><span class="eyebrow">'+esc(r.id)+'</span>'+statusBadge(r.status)+'</div><h3>'+link('detail',{id:r.id},r.attempt)+'</h3><p>'+attributionLabel(r.attribution.type)+' '+esc(r.attribution.text)+'</p>'+conditionsHtml(r)+'<div class="evidence-excerpt"><small>原始观察</small><p>'+esc(r.observation)+'</p></div><p><b>适用边界</b> '+esc(r.boundary)+'</p><p class="next-action"><b>下一步核查</b> '+esc(nextAction(r))+'</p><details><summary>查看召回依据 · 排序分 '+h.score.toFixed(1)+'</summary><p class="small muted">'+esc(h.explain.join('；').replaceAll('blocker','阻塞点').replaceAll('attempt','尝试').replaceAll('observation','观察').replaceAll('boundary','边界'))+'。此分数不是可信度或成功概率。</p></details><div class="inline-actions">'+evidenceButton(r)+link('compareMatrix',{ids:r.id},'加入条件对比')+link('incubation',{blocker:r.blocker},'查看验证计划')+'</div></article>';
    }).join('');
  }
}
