import { ViewBase } from './base.js';
import { esc } from '../util/html.js';
import { blockerGroups, recordLinks, link } from '../workflow.js';
import { VERIFICATION_STATUSES } from '../verification.js';
import { toast } from '../ui/toast.js';
export class IncubationView extends ViewBase {
 async render(params={}){
  const all=this.context.store.library.records;
  const recs = all.filter(r => !(r.attempt || "").includes("人工纠错"));
  const eligible=blockerGroups(recs).filter(([,rs])=>rs.length>=3);
  this.el.innerHTML='<div class="page-heading"><div><span class="eyebrow">04 / FROM EVIDENCE TO ACTION</span><h2>把未解的问题，变成下一次验证。</h2><p class="muted">同一阻塞点至少 3 条独立尝试记录才能形成候选；人工纠错不计入门槛。</p></div></div><p class="notice">以下为证据聚合形成的待验证候选，不是模型生成的结论。验证状态由使用者填写，仅保存在当前浏览器。</p>'+(!eligible.length?this.empty('尚无阻塞点积累到三条记录。',this.importAction()):eligible.map(([blocker,rs],i)=>{
   const v=this.context.verification.get(blocker),observed=rs,assumptions=rs.filter(r=>r.attribution.type!=='observed');
   return '<details class="card hypothesis" data-blocker="'+esc(blocker)+'" '+(!params.blocker||params.blocker===blocker?'open':'')+'><summary><span class="mono">H-'+String(i+1).padStart(3,'0')+'</span> '+esc(blocker)+' <span class="badge">'+esc(v.status)+'</span></summary><div class="hypothesis-body"><p>支撑记录 '+recordLinks(rs)+'</p><div class="two-col"><div><h3>已观察</h3><ul>'+observed.map(r=>'<li>'+esc(r.observation)+' '+link('detail',{id:r.id},r.id)+'</li>').join('')+'</ul></div><div><h3>尚未验证</h3><ul>'+assumptions.map(r=>'<li>'+esc(r.attribution.text)+'</li>').join('')+[...new Set(rs.flatMap(r=>r.missing_info||[]))].map(m=>'<li>'+esc(m)+'</li>').join('')+'</ul></div></div><form><div class="two-col"><label class="field">验证状态<select name="status">'+VERIFICATION_STATUSES.map(s=>'<option'+(s===v.status?' selected':'')+'>'+s+'</option>').join('')+'</select></label><label class="field">负责人<input name="owner" value="'+esc(v.owner)+'" placeholder="填写负责复核的研究者"></label><label class="field">最小验证动作<textarea name="action" placeholder="明确变量、对照组和观察指标">'+esc(v.action)+'</textarea></label><label class="field">验证结果 / 证据编号<textarea name="result" placeholder="例如：R-015；对应日志与观察">'+esc(v.result)+'</textarea></label><label class="field">计划日期<input type="date" name="due" value="'+esc(v.due)+'"></label></div><p class="field-error" hidden></p><div class="inline-actions"><button class="primary" type="submit">保存验证计划</button>'+link('compareMatrix',{ids:rs.slice(0,4).map(r=>r.id).join(',')},'复核条件差异 →')+'</div><p class="small muted">保存不改变原始档案；完成验证时必须填写动作与结果依据。</p></form></div></details>';
  }).join(''))+(params.blocker&&!eligible.some(([b])=>b===params.blocker)?'<p class="notice">所选阻塞点暂不满足三条尝试门槛。'+link('map',{blocker:params.blocker},'查看已有证据')+'</p>':'');
  this.el.querySelectorAll('.hypothesis').forEach(d=>{
   d.addEventListener('toggle',()=>{if(d.open)this.context.app.updateRoute({blocker:d.dataset.blocker});});
   d.querySelector('form').onsubmit=e=>{e.preventDefault();const form=e.currentTarget,error=form.querySelector('.field-error');try{const value=Object.fromEntries(new FormData(form));this.context.verification.save(d.dataset.blocker,value);d.querySelector('summary .badge').textContent=value.status;error.hidden=true;toast('验证计划已保存到当前浏览器。',{tone:'ok'});}catch(err){error.hidden=false;error.textContent=err.message;}};
  });
 }
}
