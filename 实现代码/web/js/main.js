/**
 * 入口模块：依赖 DOM，只能在浏览器里加载。
 * 若要在 Node 里做静态检查，请用 node --check，不要直接 import。
 */
import { LibraryStore } from "./store.js";
import { PersistenceAdapter } from "./persist.js";
import { RecallScorer } from "./recall.js";
import { RefutationController } from "./refute.js";
import { LibraryView } from "./views/library.js";
import { DetailView } from "./views/detail.js";
import { MapView } from "./views/map.js";
import { ProjectCheckView } from "./views/projectCheck.js";
import { CompareMatrixView } from "./views/compareMatrix.js";
import { IncubationView } from "./views/incubation.js";
import { ResurrectionView } from "./views/resurrection.js";
import { toast } from "./ui/toast.js";
import { parseHash, routeToHash } from "./route.js";
import { VerificationStore } from './verification.js';
import { EvidenceDrawer } from './ui/evidence.js';
import { esc } from './util/html.js';

/** 视图注册表：标签页 → 视图类。新增视图只改这一处。 */
const VIEWS = {
  library: LibraryView,
  detail: DetailView,
  map: MapView,
  projectCheck: ProjectCheckView,
  compareMatrix: CompareMatrixView,
  incubation: IncubationView,
  resurrection: ResurrectionView,
};

export class App {
  /** 组合根：装载库、绑定标签页、挂载视图。 */
  constructor(root) {
    this.root = root;
    this.store = new LibraryStore(new PersistenceAdapter());
    this.recall = new RecallScorer();
    this.refute = new RefutationController(this.store);
    this.verification = new VerificationStore(this.store.adapter);
    this.evidence = new EvidenceDrawer(this.store);
    this.current = null;
    this.context = { store: this.store, recall: this.recall, refute: this.refute, verification:this.verification, evidence:this.evidence, app: this };
  }

  async boot() {
    await this.store.load();
    try { const scoring=await fetch('./data/scoring.json'); if(scoring.ok)this.recall.loadWeights(await scoring.json()); } catch { /* file:// retains mirrored defaults */ }
    document.addEventListener('click',e=>{const trigger=e.target.closest('[data-evidence]');if(trigger)this.evidence.open(trigger.dataset.evidence);});
    document.addEventListener('click',e=>{const anchor=e.target.closest('a[href^="#/"]');if(!anchor||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;const route=parseHash(anchor.getAttribute('href'),Object.keys(VIEWS));if(route){e.preventDefault();this.switchTo(route.name,route.params);}});
    this.bindImportExport();
    this.updateStat();
    this.store.onChange(() => {
      this.updateStat();
      // 数据变化引起的重挂载不是"导航"：只替换当前历史记录，不往历史里塞新条目
      this.switchTo(this.currentName, this.currentParams, { replace: true });
    });
    // 多标签页：另一端导入后本端整库替换（adoptExternal 内部与自己的上次写入比对，避免回环）
    this.store.adapter.onChanged((newValue) => {
      if (!newValue) return;
      try {
        this.store.adoptExternal(JSON.parse(newValue));
      } catch { /* 另一端写入的不是合法 JSON，忽略 */ }
    });
    const tabs = document.querySelectorAll("#tabs button");
    tabs.forEach(btn => btn.addEventListener("click", () => this.switchTo(btn.dataset.view)));
    this.bindShortcuts(tabs);
    window.addEventListener("hashchange", () => this.onHashChange());
    // 深链落地：刷新、分享链接、前进/后退都走这一条路径
    const initial = parseHash(location.hash, Object.keys(VIEWS));
    await this.switchTo(initial ? initial.name : "library", initial ? initial.params : {},
      { replace: true });
  }

  /** 选文件并导入。抽成方法，好让空状态里的「导入库文件」按钮复用同一条路径。 */
  openImport() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json,application/json";
    input.addEventListener("change", async () => {
      const file = input.files && input.files[0];
      if (!file) return;
      try {
        toast('正在读取并校验库文件…',{duration:2000});
        const text = await file.text();
        await new Promise(resolve=>setTimeout(resolve,0));
        const report = this.store.importLibrary(text);
        const renamed = Object.keys(report.renumbered).length;
        toast("导入完成：新增 " + report.added.length + " 条，重复 " +
          report.duplicated.length + " 条" +
          (renamed ? "，重编号 " + renamed + " 条（已记录 remap_from）" : "") + "。",
          { tone: "ok" });
        this.switchTo("library");
      } catch (e) {
        toast("导入失败：" + e.message, { tone: "danger", duration: 10000 });
      }
    });
    input.click();
  }

  bindImportExport() {
    document.querySelector('.library-menu')?.addEventListener('click',e=>{if(e.target.closest('button'))e.currentTarget.open=false;});
    const download=(data,name)=>{const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);};
    document.querySelector('#btn-backup')?.addEventListener('click',()=>download({format:'rra-verification-v1',plans:this.verification.all()},'verification.backup.json'));
    document.querySelector('#btn-restore')?.addEventListener('click',()=>{const file=document.createElement('input');file.type='file';file.accept='.json';file.onchange=async()=>{try{if(!file.files[0])return;const n=this.verification.restore(JSON.parse(await file.files[0].text()));toast('已恢复 '+n+' 项验证计划。',{tone:'ok'});this.switchTo('incubation');}catch(e){toast(e.message,{tone:'danger'});}};file.click();});
    const btnImport = document.getElementById("btn-import");
    const btnExport = document.getElementById("btn-export");
    if (btnImport) btnImport.addEventListener("click", () => this.openImport());

    // 事件委托：视图内部（空状态、提示条）随时可以放一个 .js-import 按钮
    document.addEventListener("click", (e) => {
      const trigger = e.target && e.target.closest ? e.target.closest(".js-import") : null;
      if (trigger) this.openImport();
    });

    if (btnExport) btnExport.addEventListener("click", () => {
      const blob = new Blob([this.store.exportLibrary()], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "library.exported.json";
      document.body.appendChild(a);
      a.click();
      // 立刻 revoke 会让部分浏览器的下载中断，延后释放
      setTimeout(() => {
        a.remove();
        URL.revokeObjectURL(a.href);
      }, 2000);
      toast("已导出库文件：library.exported.json（专家侧导入它即可续接）。", { tone: "ok" });
    });
  }

  updateStat() {
    const el = document.getElementById("lib-stat");
    if (!el) return;
    const recs = this.store.library.records || [];
    const simulated = recs.filter(r => (r.provenance || {}).source === "模拟").length;
    el.textContent = recs.length + " 条档案 · 模拟 " + simulated;
    const sync=document.querySelector('#sync-status');
    if(sync)sync.textContent='库版本 '+this.store.library.version+' · 数据日期 '+this.store.library.generated_at+' · 当前浏览器本地保存 · 与专家手动交换';
  }

  async switchTo(name, params = {}, opts = {}) {
    this.evidence.close();
    const ViewClass = VIEWS[name];
    if (!ViewClass) throw new Error("未知视图：" + name);
    this.currentName = name;
    this.currentParams = params;
    // 用 aria-current 而不是 aria-selected：这里是导航按钮，不是 tablist（tablist 需要每个 tab 配一个 panel）
    document.querySelectorAll("#tabs button").forEach(btn => {
      if (btn.dataset.view === name) btn.setAttribute("aria-current", "page");
      else btn.removeAttribute("aria-current");
    });
    if (this.current) this.current.destroy();
    this.current = new ViewClass(this.context);
    this.mounting=true;
    try { await this.current.mount(this.root, params); } finally { this.mounting=false; }
    this.syncHash(name, this.currentParams, !!opts.replace);
    document.title='研究复盘助手 · '+({library:'研究证据工作台',projectCheck:'立项检查',map:'失败地图',compareMatrix:'条件对比',incubation:'孵化清单',resurrection:'可重试方向',detail:'档案详情'}[name]||'');
    if(!opts.replace || opts.navigate) { window.scrollTo({top:0,behavior:'instant'}); this.root.focus({preventScroll:true}); }
  }

  /**
   * 把当前状态写回地址栏。
   * replace=true 用于"同一视图内的状态变化"（检索词 / 筛选 / 排序）：否则每敲一个字
   * 就多一条历史记录，返回键要按十几次才退得出去。
   */
  syncHash(name, params, replace = false) {
    const next = routeToHash(name, params);
    if (location.hash === next) return;
    try {
      history[replace ? "replaceState" : "pushState"](null, "", next);
    } catch {
      // file:// 等来源为 opaque 的环境会抛 SecurityError；退化为直接改 hash（同文档内导航）
      try { location.hash = next; } catch { /* 环境彻底不支持：功能降级，但不报错中断 */ }
    }
  }

  /** 地址栏变化（前进 / 后退 / 手改 hash）→ 同步视图。 */
  onHashChange() {
    const parsed = parseHash(location.hash, Object.keys(VIEWS));
    if (!parsed) return;   // 未知路由：什么都不做，也不改写地址栏
    // 用同一个序列化函数比较"规范化后的地址"：默认值会被折叠，
    // 因此 #/library 与 #/library?sort=order 不会被误判成两次导航。
    const same = parsed.name === this.currentName &&
      routeToHash(parsed.name, parsed.params) === routeToHash(this.currentName, this.currentParams);
    if (same) return;      // 这就是自己刚写进去的那一次
    this.switchTo(parsed.name, parsed.params, { replace: true, navigate: true });
  }

  /** 视图内部状态变化（检索词 / 筛选 / 排序）→ 只替换当前历史记录。 */
  updateRoute(params) {
    this.currentParams = params;
    if(this.mounting)return;
    this.syncHash(this.currentName, params, true);
  }

  /**
   * 键盘快捷键：数字键切换视图、/ 定位检索框。
   * 焦点在输入控件上时不生效 —— 否则用户打字按到 1，整页就跳走了。
   */
  bindShortcuts(tabs) {
    const list = Array.from(tabs || []);
    document.addEventListener("keydown", (e) => {
      if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target;
      const tag = t && t.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (t && t.isContentEditable)) return;
      if (/^[1-9]$/.test(e.key)) {
        const btn = list[Number(e.key) - 1];
        if (!btn) return;          // 超出标签数量：不拦截，交给浏览器
        e.preventDefault();
        this.switchTo(btn.dataset.view);
        return;
      }
      if (e.key === "/") {
        e.preventDefault();
        this.focusSearch();
      }
    });
  }

  /** / 的行为：已在库视图就就地聚焦（不重挂载，保住已经输入的检索词）。 */
  focusSearch() {
    const focus = () => {
      const q = document.querySelector("#lib-q");
      if (q) q.focus();
    };
    if (this.currentName === "library") { focus(); return; }
    this.switchTo("library").then(focus).catch(() => {});
  }

  mount(viewClass, params) {
    return new viewClass(this.context).mount(this.root, params);
  }
}

const TAB_NAMES = Array.from(document.querySelectorAll("#tabs button"))
  .map((b) => b.dataset.view);
const MISSING = TAB_NAMES.filter((n) => !(n in VIEWS));
if (MISSING.length) {
  throw new Error("标签页与视图注册表不一致，缺少实现: " + MISSING.join(", "));
}

const app = new App(document.getElementById("view-root"));
window.__app = app;
app.boot().catch((err) => {
  document.getElementById("view-root").innerHTML =
    '<div class="card"><h3 class="warn">启动失败</h3><p class="muted">' +
    esc(String(err && err.message ? err.message : err)) + "</p></div>";
});
