import { DIMS, DIM_LABELS } from '../contracts.js';
import { esc } from './html.js';
export function conditionRows(records) {
  return DIMS.map(dim => {
    const values=records.map(r=>String(r.conditions?.[dim] || '').trim());
    const known=values.filter(Boolean);
    return {dim,label:DIM_LABELS[dim],values,different:new Set(known).size>1,missing:known.length<records.length};
  });
}
export function conditionsHtml(record) {
  const known=Object.entries(record.conditions || {}).filter(([k,v])=>DIMS.includes(k)&&String(v).trim());
  return known.length ? '<div class="condition-chips">'+known.map(([k,v])=>'<span><small>'+DIM_LABELS[k]+'</small> '+esc(v)+'</span>').join('')+'</div>' : '<p class="muted">结构化条件未提供；请在专家侧补全后导入。</p>';
}
