export const VERIFICATION_STATUSES=['待验证','验证中','已证实','已否定'];
/** Personal workflow notes are separate from the append-only evidence library. */
export class VerificationStore {
  constructor(adapter){this.adapter=adapter;}
  all(){ const value=this.adapter.read('verification'); return value && typeof value==='object'&&!Array.isArray(value)?value:{}; }
  get(key){const all=this.all();return Object.hasOwn(all,key)?all[key]:{status:'待验证',action:'',owner:'',due:'',result:''};}
  validate(value){
    if(!value||typeof value!=='object'||Array.isArray(value))throw new Error('验证计划格式错误。');
    if(!VERIFICATION_STATUSES.includes(value.status))throw new Error('请选择有效的验证状态。');
    const next={}; for(const k of ['status','action','owner','due','result'])next[k]=String(value[k]||'').trim();
    if(['已证实','已否定'].includes(next.status)&&(!next.result||!next.action))throw new Error('完成验证前，请填写验证动作和结果依据。');
    return next;
  }
  save(key,value){
    const next=this.validate(value),all=this.all();
    Object.defineProperty(all,key,{value:{...next,updated_at:new Date().toISOString()},enumerable:true,configurable:true,writable:true});
    this.adapter.write('verification',all);return all[key];
  }
  restore(raw){
    if(raw?.format!=='rra-verification-v1'||!raw.plans||typeof raw.plans!=='object'||Array.isArray(raw.plans))throw new Error('请导入验证计划备份文件。');
    const entries=Object.entries(raw.plans).map(([key,value])=>[key,this.validate(value)]);
    const next={...this.all(),...Object.fromEntries(entries)};this.adapter.write('verification',next);return entries.length;
  }
}
