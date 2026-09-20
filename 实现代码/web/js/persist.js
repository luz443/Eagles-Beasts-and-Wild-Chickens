/** 持久化适配器。全部读写集中在这里，便于替换存储而不影响视图。 */

export class PersistenceAdapter {
  constructor(namespace = "rra") {
    this.namespace = namespace;
  }

  key(k) { return this.namespace + ":" + k; }

  read(key) {
    try {
      const raw = localStorage.getItem(this.key(key));
      return raw === null ? null : JSON.parse(raw);
    } catch {
      return null;
    }
  }

  write(key, value) {
    /** 写失败（配额 / 隐私模式）必须抛出，让上层提示并保留内存态。 */
    localStorage.setItem(this.key(key), JSON.stringify(value));
  }

  readRaw(key) {
    try {
      return localStorage.getItem(this.key(key));
    } catch {
      return null;
    }
  }

  remove(key) {
    try { localStorage.removeItem(this.key(key)); } catch { /* 忽略 */ }
  }

  isAvailable() {
    try {
      const probe = this.key("__probe__");
      localStorage.setItem(probe, "1");
      localStorage.removeItem(probe);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * 监听 storage 事件：两个标签页打开时，一端导入另一端要能感知，避免互相覆盖。
   * 只处理 library 键，且把原始字符串交给回调，由上层与自己的上次写入比对去重，
   * 否则 A 写→B 收→B 写→A 收 会形成回环。
   */
  onChanged(callback) {
    window.addEventListener("storage", (e) => {
      if (!e.key || e.key !== this.key("library")) return;
      callback(e.newValue);
    });
  }
}
