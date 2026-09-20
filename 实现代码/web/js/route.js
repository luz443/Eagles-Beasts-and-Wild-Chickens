/**
 * 路由：视图状态 ⇄ 地址栏 hash（唯一真源）。
 *
 * 为什么需要它：单页应用刷新会丢状态，评委拿到链接也只能进首页。
 * hash 是纯前端可用的深链接方案 —— 静态托管、本地 http、file:// 都能用，不需要服务端配合。
 *
 * 显式路由格式（不靠约定俗成）：
 *   #/library                                          经验库（默认）
 *   #/library?q=显存&status=进行中&sort=confidence      库内状态：检索词 / 状态 / 排序
 *   #/projectCheck | #/map | #/compareMatrix | #/incubation
 *   #/detail/R-003                                     档案详情：深链到某一条档案
 *
 * 本模块是纯函数：不碰 DOM、不碰 history，可以在 Node 里直接测。
 */

/** 视图状态 → hash 字符串。 */
export function routeToHash(name, params = {}) {
  if (name === "detail") {
    return "#/detail/" + encodeURIComponent(String(params.id == null ? "" : params.id));
  }
  if (name === "library") {
    const usp = new URLSearchParams();
    if (params.query) usp.set("q", String(params.query));
    if (params.status) usp.set("status", String(params.status));
    // 默认排序不写进 URL：地址栏只承载"与默认不同"的状态，链接更短也更好读
    if (params.sort && params.sort !== "order") usp.set("sort", String(params.sort));
    if(params.page&&String(params.page)!=='1')usp.set('page',String(params.page));
    const qs = usp.toString();
    return "#/library" + (qs ? "?" + qs : "");
  }
  const usp = new URLSearchParams();
  for (const [key, alias] of [['query','q'],['blocker','blocker'],['ids','ids'],['page','page']])
    if(params[key]) usp.set(alias,String(params[key]));
  return "#/" + name + (usp.size ? '?' + usp.toString() : '');
}

/**
 * hash → { name, params }。
 * 认不出、或视图不在注册表里时返回 null —— 语义是"不动作"：
 * 既不要把用户踹回首页，也不要把坏链接改写进地址栏。
 */
export function parseHash(hash, knownViews = []) {
  const raw = String(hash == null ? "" : hash).replace(/^#\/?/, "");
  if (!raw) return null;
  const cut = raw.indexOf("?");
  const pathPart = cut === -1 ? raw : raw.slice(0, cut);
  const queryPart = cut === -1 ? "" : raw.slice(cut + 1);
  const segs = pathPart.split("/").filter(Boolean);
  const name = segs[0];
  if (!name) return null;
  if (knownViews.length && !knownViews.includes(name)) return null;

  const params = {};
  if (name === "detail") {
    // #/detail 没有编号 → 定位不到任何档案，按坏链接处理
    if (!segs[1]) return null;
    try { params.id = decodeURIComponent(segs[1]); } catch { return null; }
  }
  if (queryPart) {
    const usp = new URLSearchParams(queryPart);
    if (usp.get("q")) params.query = usp.get("q");
    if (usp.get("status")) params.status = usp.get("status");
    if (usp.get("sort")) params.sort = usp.get("sort");
    for (const key of ['blocker','ids','page']) if(usp.get(key)) params[key]=usp.get(key);
  }
  return { name, params };
}

/**
 * 两个状态的参数是否等价。
 * 只做字符串浅比较 —— 视图参数本来就只允许字符串（数字/日期都不进 URL）。
 * 缺省值与空串视为等价，避免"undefined vs ''"造成无意义的重挂载。
 */
export function sameParams(a, b) {
  const x = a || {};
  const y = b || {};
  const keys = new Set(Object.keys(x).concat(Object.keys(y)));
  for (const k of keys) {
    const l = x[k] == null ? "" : String(x[k]);
    const r = y[k] == null ? "" : String(y[k]);
    if (l !== r) return false;
  }
  return true;
}
