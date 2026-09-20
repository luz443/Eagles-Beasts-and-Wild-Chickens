import { esc } from '../util/html.js';
import { conditionsHtml } from '../util/conditions.js';
import { link } from '../workflow.js';
export class EvidenceDrawer {
  constructor(store){this.store=store;}
  close(){if(!this.dialog)return;this.dialog.close();this.dialog.remove();this.dialog=null;const trigger=this.trigger;this.trigger=null;if(trigger?.isConnected)trigger.focus();}
  open(id, specificRef=null){
    this.close();this.trigger=document.activeElement;
    const rec=this.store.findById(id);if(!rec)return;
    const refs=specificRef?[specificRef]:(rec.evidence_refs||[]);
    const dialog=document.createElement('dialog');dialog.className='evidence-drawer';dialog.setAttribute('aria-labelledby','evidence-title');
    dialog.innerHTML='<div class="drawer-top"><span class="eyebrow">EVIDENCE / 证据阅览</span><button class="ghost" data-close aria-label="关闭证据">关闭 ×</button></div><h2 id="evidence-title">'+esc(rec.id)+' · 原始观察</h2><blockquote>'+esc(rec.observation)+'</blockquote><p class="muted">'+esc(rec.provenance?.author)+' · '+esc(rec.provenance?.date)+' · '+esc(rec.provenance?.source)+'</p><h3>适用条件</h3>'+conditionsHtml(rec)+'<p>'+esc(rec.boundary)+'</p><h3>引用原文</h3>'+(refs.length?refs.map(ref=>{
      const target=this.store.findById(ref.record);
      return '<section class="evidence-excerpt"><span class="mono">'+esc(ref.record)+'</span><blockquote>'+esc(ref.quote||'未附原文片段')+'</blockquote>'+(target?'<p class="muted">边界：'+esc(target.boundary)+'</p>'+link('detail',{id:target.id},'打开来源档案 →'):'<p class="warn">来源档案未找到</p>')+'</section>';
    }).join(''):'<p class="notice">本条有观察记录，但未附跨档案引用；观察记录不等于已独立验证的结论。</p>')+'<div class="drawer-actions">'+link('detail',{id:rec.id},'打开完整档案 →')+'</div>';
    document.body.appendChild(dialog);this.dialog=dialog;
    dialog.querySelector('[data-close]').onclick=()=>this.close();
    dialog.addEventListener('cancel',e=>{e.preventDefault();this.close();});
    dialog.addEventListener('click',e=>{if(e.target===dialog && e.clientX<dialog.getBoundingClientRect().left)this.close();if(e.target.closest('a'))this.close();});
    dialog.showModal();dialog.querySelector('button').focus();
  }
}
