/** 引用上标：判断后面挂 [R-008]，悬停/聚焦显示原文片段，点击或回车跳到档案。 */

export class CitationRenderer {
  constructor(options = {}) {
    this.onJump = options.onJump || (() => {});
  }

  /** 把文本里的 [R-###] 渲染成可交互的上标引用。 */
  render(text, evidenceRefs = []) {
    const el = document.createElement("span");
    const parts = String(text || "").split(/(\[R-[0-9]{3,}\])/g);
    for (const part of parts) {
      const m = part.match(/^\[(R-[0-9]{3,})\]$/);
      if (m) {
        const ref = (evidenceRefs || []).find(r => r.record === m[1]);
        const hasQuote = !!(ref && typeof ref.quote === "string" && ref.quote.trim().length >= 4);
        const a = document.createElement("sup");
        // 规则：没有原文片段的引用不允许表现成"有证据"——只标编号并给出提示
        a.className = hasQuote ? "citation" : "citation citation-bad";
        a.textContent = "[" + m[1] + "]";
        // 可聚焦：键盘用户也必须能读原文片段，不能只有鼠标悬停这一条路
        a.tabIndex = 0;
        a.setAttribute("role", "button");
        a.setAttribute("aria-label",
          hasQuote ? "引用 " + m[1] + "，查看原文片段并可跳转" : "引用 " + m[1] + "，无原文片段，无法复核");
        if (hasQuote) {
          this.attachPopup(a, ref.quote);
        } else {
          a.title = "该引用没有原文片段，无法复核";
        }
        a.addEventListener("click", () => this.onJump(m[1]));
        a.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();          // 空格默认会滚动页面
            this.onJump(m[1]);
          }
        });
        el.appendChild(a);
      } else if (part) {
        el.appendChild(document.createTextNode(part));
      }
    }
    return el;
  }

  attachPopup(el, quote) {
    let popup = null;
    const show = () => {
      if (popup) return;                     // 反复 mouseenter / focus 不重复创建
      popup = document.createElement("div");
      popup.className = "citation-popup";
      popup.setAttribute("role", "tooltip");
      popup.textContent = "「" + quote + "」";   // 用 textContent，天然无注入风险
      document.body.appendChild(popup);
      const rect = el.getBoundingClientRect();
      // getBoundingClientRect 是视口坐标，浮层是文档坐标 → 必须加滚动量，否则滚动后错位
      popup.style.left = (rect.left + window.scrollX) + "px";
      popup.style.top = (rect.bottom + window.scrollY + 6) + "px";
    };
    const hide = () => { if (popup) { popup.remove(); popup = null; } };
    el.addEventListener("mouseenter", show);
    el.addEventListener("mouseleave", hide);
    el.addEventListener("focus", show);
    el.addEventListener("blur", hide);
    el.addEventListener("click", hide);      // 点击跳转时也清掉，避免留下孤儿浮层
    el.addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });
  }
}
