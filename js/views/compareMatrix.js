import { ViewBase } from './base.js';
import { esc } from '../util/html.js';
import { conditionRows } from '../util/conditions.js';
import { link, expertRelationsHtml, hasBlocker } from '../workflow.js';
export class CompareMatrixView extends ViewBase {
  async render(params={}) {
    this.params={...params};this.selected=new Set((params.ids||'').split(',').filter(id=>this.context.store.findById(id)).slice(0,4));
    const records=this.context.store.library.records;
    this.el.innerHTML='<div class="page-heading"><div><span class="eyebrow">03 / CONDITION ATLAS</span><h2>先对齐条件，再讨论结论。</h2><p class="muted">选择 2–4 条档案；未知条件始终保留，不做隐含推断。</p></div></div><section class="card"><div class="toolbar"><div class="field field-wide"><label for="cm-q">查找档案</label><input type="search" id="cm-q" placeholder="编号、尝试或关键词" value="'+esc(params.query||'')+'"></div><div class="field"><label for="cm-blocker">阻塞点</label><select id="cm-blocker"><option value="">全部阻塞点</option>'+[...new Set(records.map(r=>r.blocker))].map(b=>'<option'+(params.blocker===b?' selected':'')+'>'+esc(b)+'</option>').join('')+'</select></div></div><div id="cm-options" class="compare-options"></div><div class="selection-bar"><span id="cm-selected" role="status"></span><button id="cm-go" class="primary">生成条件对比</button></div><p id="cm-error" class="field-error" hidden></p></section><div id="cm-result" aria-live="polite"></div>';
    this.el.querySelector('#cm-q').oninput=()=>this.filterOptions();
    this.el.querySelector('#cm-blocker').onchange=()=>this.filterOptions();
    this.el.querySelector('#cm-go').onclick=()=>this.buildMatrix([...this.selected]);
    this.filterOptions();if(this.selected.size>=2)this.buildMatrix([...this.selected]);
  }
  filterOptions(){
    const q=this.el.querySelector('#cm-q').value.toLowerCase(),b=this.el.querySelector('#cm-blocker').value;
    const records=this.context.store.library.records.filter(r=>(!b||r.blocker===b)&&[r.id,r.attempt,r.blocker].join(' ').toLowerCase().includes(q));
    this.el.querySelector('#cm-options').innerHTML=records.length?records.map(r=>'<label class="compare-choice"><input type="checkbox" value="'+esc(r.id)+'"'+(this.selected.has(r.id)?' checked':'')+'><span><b class="mono">'+esc(r.id)+'</b><span>'+esc(r.attempt)+'</span></span></label>').join(''):'<p class="muted">没有匹配档案，已选项仍保留。</p>';
    this.el.querySelectorAll('input[type=checkbox]').forEach(input=>input.onchange=()=>{if(input.checked&&this.selected.size>=4){input.checked=false;this.fail('最多选择四条档案，请先移除一个已选项。');return;}input.checked?this.selected.add(input.value):this.selected.delete(input.value);this.sync();});
    this.params.query=q;this.params.blocker=b;this.sync();
  }
  sync(){
    this.params.ids=[...this.selected].join(',');this.context.app.updateRoute(this.params);
    this.el.querySelector('#cm-selected').innerHTML='已选 '+this.selected.size+'/4 '+[...this.selected].map(id=>'<button class="ghost" data-remove="'+esc(id)+'" aria-label="移除 '+esc(id)+'">'+esc(id)+' ×</button>').join('');
    this.el.querySelectorAll('[data-remove]').forEach(btn=>btn.onclick=()=>{this.selected.delete(btn.dataset.remove);this.filterOptions();});
    this.el.querySelector('#cm-result').innerHTML='';
  }
  fail(message){const el=this.el.querySelector('#cm-error');el.hidden=false;el.textContent=message;}
  buildMatrix(ids){
    if(ids.length<2){this.fail('请至少选择两条档案。');return;}
    this.el.querySelector('#cm-error').hidden=true;
    const recs=ids.map(id=>this.context.store.findById(id)).filter(Boolean),rows=conditionRows(recs);
    const diff=rows.filter(r=>r.different).length,missing=rows.filter(r=>r.missing).length;
    this.el.querySelector('#cm-result').innerHTML='<section class="card matrix-result"><div class="section-heading"><h3>条件差异剖面</h3><span class="badge">'+diff+' 个差异维度 · '+missing+' 个信息不全维度</span></div><p class="notice">'+(diff?'存在已记录的条件差异，不能直接判为真冲突。':missing?'条件信息不全，暂不能判为同一问题或真冲突。':'已记录条件一致；结论是否冲突仍需专家复核。')+'</p><div class="table-scroll"><table class="matrix-table"><thead><tr><th scope="col">条件维度</th>'+recs.map(r=>'<th scope="col">'+link('detail',{id:r.id},r.id)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr class="'+(r.different?'diff':'')+'"><th scope="row">'+r.label+(r.different?' <span class="badge">差异</span>':'')+'</th>'+r.values.map(v=>'<td>'+ (v?esc(v):'<span class="missing-value">未提供</span>')+'</td>').join('')+'</tr>').join('')+'<tr><th scope="row">观察结果</th>'+recs.map(r=>'<td>'+esc(r.observation)+'</td>').join('')+'</tr><tr><th scope="row">适用边界</th>'+recs.map(r=>'<td>'+esc(r.boundary)+'</td>').join('')+'</tr></tbody></table></div><h3>专家关系与迁移说明</h3>'+expertRelationsHtml(recs)+'<p class="muted">缺失条件不参与差异判断；关系说明不替代当前档案的条件值。</p><div class="inline-actions">'+link('incubation',{blocker:recs.find(hasBlocker)?.blocker || ''},'查看相关验证计划 →')+'</div></section>';
  }
}
