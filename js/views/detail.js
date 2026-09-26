import { ViewBase } from "./base.js";
import { CitationRenderer } from "../citation.js";
import { attributionLabel, confidenceBadge, esc } from "../util/html.js";
import { toast } from "../ui/toast.js";
import { conditionsHtml } from '../util/conditions.js';
import { link, chainHtml, evidenceButton } from '../workflow.js';

/** 档案详情：完整字段 + 证据引用（可点回被引用记录）+ 反驳入口。 */
export class DetailView extends ViewBase {
  async render(params = {}) {
    const rec = this.context.store.findById(params.id);
    if (!rec) {
      this.el.innerHTML = this.empty("档案不存在：" + esc(params.id) + "。可能已被另一端导入的库覆盖。");
      return;
    }
    const cit = new CitationRenderer({
      onJump: (rid) => this.context.evidence.open(rec.id, (rec.evidence_refs||[]).find(r=>r.record===rid)),
    });
    const rows = [
      ["尝试", rec.attempt], ["预期", rec.expectation], ["观察", rec.observation],
      ["阻塞点", rec.blocker],
    ];
    let html = '<div class="inline-actions">'+link('library',{},'← 经验库')+link('compareMatrix',{ids:rec.id},'加入条件对比')+link('incubation',{blocker:rec.blocker},'查看验证计划')+'</div><article class="card">' +
      "<h2>" + esc(rec.id) + "　" + esc(rec.attempt) + "</h2>" +
      '<p class="muted">' + attributionLabel((rec.attribution || {}).type) + " " +
      esc((rec.attribution || {}).text || "") + "</p>" +
      '<div class="table-scroll"><table class="matrix-table">' +
      rows.map(([k, v]) => '<tr><th class="th-key">' + k + "</th><td>" + esc(v || "") + "</td></tr>").join("") +
      '<tr><th class="th-key">适用边界</th><td>' + esc(rec.boundary) + "</td></tr>" +
      '<tr><th class="th-key">置信度</th><td>' + confidenceBadge(rec.confidence) + "</td></tr>" +
      '<tr><th class="th-key">状态</th><td>' + esc(rec.status) + "</td></tr>" +
      '<tr><th class="th-key">提出人 / 时间</th><td>' + esc((rec.provenance || {}).author) + " / " +
      esc((rec.provenance || {}).date) +
      ((rec.provenance || {}).remap_from
        ? "（重编号自 " + esc(rec.provenance.remap_from) + "）" : "") + "</td></tr>" +
      "</table></div>" + '<h3>结构化条件</h3>'+conditionsHtml(rec)+evidenceButton(rec);

    if ((rec.missing_info || []).length) {
      html += '<p class="notice">缺失信息：' + esc(rec.missing_info.join("；")) + "</p>";
    }

    html += '<p id="detail-evidence" class="hits-summary"></p>';
    const corrections=this.context.refute.listFor(rec.id);
    const target=(rec.links||[]).map(l=>this.context.store.findById(l.target)).filter(Boolean);
    const related=[...target,rec,...corrections].filter((r,i,all)=>all.findIndex(x=>x.id===r.id)===i);
    html += '<h3>证据与判断演化</h3>'+chainHtml(related);
    if(corrections.length) html+='<p class="notice">这条判断有 '+corrections.length+' 条人工纠错，请同时复核双方依据。</p>';
    if((rec.artifacts||[]).length)html+='<details><summary>关联实验产物</summary><ul>'+rec.artifacts.map(a=>'<li>'+esc(a.kind)+' · <code>'+esc(a.ref)+'</code></li>').join('')+'</ul></details>';

    // 反驳：展开式表单，不用 prompt()（原生弹窗会打断操作流，也没有校验位置）
    html += '<div class="refute-form">' +
      '<button type="button" id="btn-refute" class="warn" aria-expanded="false" aria-controls="refute-body">' +
      "这个判断不对（反驳）</button>" +
      '<div id="refute-body" hidden>' +
      '<div class="field">' +
      '<label class="field-label" for="refute-reason">反驳理由（写清哪里不对，至少 4 个字）</label>' +
      '<textarea id="refute-reason" rows="3" placeholder="例如：该观察只发生在 batch size ≤ 8 的条件下，边界写得过宽。"></textarea>' +
      "</div>" +
      '<p id="refute-error" hidden></p>' +
      '<div class="refute-actions">' +
      '<button type="button" class="primary" id="refute-submit">提交纠错档案</button>' +
      '<button type="button" class="ghost" id="refute-cancel">取消</button>' +
      '<span id="refute-result" class="muted"></span>' +
      "</div></div></div></article>";
    this.el.innerHTML = html;

    const ev = this.el.querySelector("#detail-evidence");
    const refs = rec.evidence_refs || [];
    ev.appendChild(document.createTextNode("证据引用：" + (refs.length ? "" : "（本档案未附原文片段）")));
    refs.forEach(ref => {
      ev.appendChild(cit.render("[" + ref.record + "]", refs));
      ev.appendChild(document.createTextNode(" "));
    });

    this.bindRefute(rec);
  }

  /** 反驳表单：校验、错误定位、提交反馈。 */
  bindRefute(rec) {
    const trigger = this.el.querySelector("#btn-refute");
    const body = this.el.querySelector("#refute-body");
    const reason = this.el.querySelector("#refute-reason");
    const errBox = this.el.querySelector("#refute-error");
    const result = this.el.querySelector("#refute-result");

    const toggle = (open) => {
      body.hidden = !open;
      trigger.setAttribute("aria-expanded", String(open));
      if (open) reason.focus();
    };

    trigger.addEventListener("click", () => toggle(body.hidden));
    this.el.querySelector("#refute-cancel").addEventListener("click", () => {
      reason.value = "";
      errBox.hidden = true;
      toggle(false);
      trigger.focus();
    });

    const showError = (message) => {
      errBox.className = "field-error";
      errBox.textContent = message;
      errBox.hidden = false;
      reason.setAttribute("aria-invalid", "true");
      reason.focus();
    };

    this.el.querySelector("#refute-submit").addEventListener("click", () => {
      const text = reason.value.trim();
      // 先在本地拦一道：错误提示贴着输入框，而不是弹窗
      if (text.length < 4) {
        showError("反驳理由太短（至少 4 个字）。请写清哪一条观察、哪个边界不成立。");
        return;
      }
      errBox.hidden = true;
      reason.removeAttribute("aria-invalid");
      try {
        const newId = this.context.refute.submit(rec.id, text);
        result.textContent = "已记录为 " + newId + "（原判断保留，不覆盖）";
        result.className = "ok";
        reason.value = "";
        toggle(false);
        toast("已生成纠错档案 " + newId + "：原判断保留，两条并存。", { tone: "ok" });
      } catch (e) {
        showError(e.message);
      }
    });
  }
}
