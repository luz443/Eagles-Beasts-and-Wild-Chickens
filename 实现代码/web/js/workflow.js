import { esc } from './util/html.js';
import { routeToHash } from './route.js';
import { DIM_LABELS } from './contracts.js';
export function expertRelationsHtml(records){
  const ids=records.map(r=>r.id),relations=records.flatMap(r=>(r.links||[]).filter(l=>ids.includes(l.target)).map(l=>'<section class="evidence-excerpt"><b>'+esc(l.target)+' → '+esc(r.id)+' · '+esc(l.relation)+'</b><p>'+esc(l.transferable||'尚未填写迁移结论')+'</p><ul>'+(l.same||[]).map(s=>'<li>相同条件 · '+esc(DIM_LABELS[s.dim]||s.dim)+'：'+esc(s.value)+'</li>').join('')+(l.diff||[]).map(d=>'<li>条件变化 · '+esc(DIM_LABELS[d.dim]||d.dim)+'：'+esc(d.from)+' → '+esc(d.to)+'</li>').join('')+'</ul></section>'));
  return relations.join('') || '<p class="muted">所选档案之间尚无专家关系说明。</p>';
}
export const isCorrection = r => (r.attempt || '').includes('人工纠错');
export const hasBlocker = r => !!r.blocker && !/^无([（(]|$)/.test(r.blocker);
export function blockerGroups(records) {
  const groups=new Map();
  records.filter(r=>!isCorrection(r)&&hasBlocker(r)).forEach(r=>{if(!groups.has(r.blocker))groups.set(r.blocker,[]);groups.get(r.blocker).push(r);});
  return [...groups].sort((a,b)=>b[1].length-a[1].length || a[0].localeCompare(b[0]));
}
export function link(name, params, label, cls='text-link') {
  return '<a class="'+cls+'" href="'+esc(routeToHash(name,params))+'">'+esc(label)+'</a>';
}
export function recordLinks(records) {return records.map(r=>link('detail',{id:r.id},r.id,'record-link')).join(' ');}
export function evidenceButton(rec) {
  return '<button type="button" class="ghost evidence-open" data-evidence="'+esc(rec.id)+'">'+((rec.evidence_refs||[]).length ? '查看引用证据 ↗':'查看原始观察 ↗')+'</button>';
}
export function nextAction(rec) {
  return (rec.missing_info||[]).length ? '先补齐：'+rec.missing_info.join('；') : '复核适用边界，并在当前条件下安排一次最小验证。';
}
export function chainHtml(records) {
  return '<ol class="evidence-chain">'+records.map((r,i)=>'<li><span class="chain-dot">'+String(i+1).padStart(2,'0')+'</span><div>'+link('detail',{id:r.id},r.id+' · '+r.attempt)+'<p>'+esc(r.observation)+'</p><small>'+esc(r.status)+' · '+esc(r.provenance?.date || '')+'</small></div></li>').join('')+'</ol>';
}
