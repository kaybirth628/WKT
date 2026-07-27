function esc(t) {
  return String(t ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setMsg(text, ok) {
  const el = document.getElementById("planMsg");
  if (!el) return;
  el.textContent = text || "";
  el.className = "msg list-msg" + (text ? (ok ? " ok" : " error") : "");
}

function numClass(v) {
  const n = Number(v);
  if (!Number.isFinite(n) || n <= 0) return "";
  return " inv-gap-hot";
}

function stagesHtml(stages) {
  if (!stages || !stages.length) {
    return '<div class="inv-plan-stages">无半成品明细</div>';
  }
  return `<div class="inv-plan-stages">${stages
    .map(
      (s) =>
        `<span class="inv-plan-stage">${esc(s.process_code)} ${esc(s.process_name)} · ${esc(
          s.status_label
        )}${s.supplier_name ? " · " + esc(s.supplier_name) : ""}：<b>${esc(s.qty)}</b></span>`
    )
    .join("")}</div>`;
}

function renderRows(items) {
  const tbody = document.getElementById("planBody");
  const empty = document.getElementById("planEmpty");
  const count = document.getElementById("planCount");
  if (!tbody) return;
  if (!items.length) {
    tbody.innerHTML = "";
    if (empty) empty.hidden = false;
    if (count) count.textContent = "共 0 行";
    return;
  }
  if (empty) empty.hidden = true;
  if (count) count.textContent = `共 ${items.length} 行（订单一行一条）`;
  tbody.innerHTML = items
    .map((r, idx) => {
      const detailId = `plan-detail-${idx}`;
      return `<tr class="inv-plan-row" data-detail="${detailId}">
        <td><button type="button" class="btn btn-outline btn-sm inv-plan-toggle" aria-expanded="false" aria-controls="${detailId}">明细</button></td>
        <td class="list-td-text">${esc(r.customer)}</td>
        <td class="list-td-text">${esc(r.order_no)}</td>
        <td>${esc(r.delivery_date || "—")}</td>
        <td class="list-td-mono">${esc(r.customer_part_no)}</td>
        <td class="list-td-text">${esc(r.product_spec || "—")}</td>
        <td>${esc(r.open_qty)}</td>
        <td>${esc(r.finished_qty)}</td>
        <td>${esc(r.semifinished_qty)}</td>
        <td class="${numClass(r.gap_ship).trim()}">${esc(r.gap_ship)}</td>
        <td class="${numClass(r.gap_cover).trim()}">${esc(r.gap_cover)}</td>
        <td class="${numClass(r.suggest_qty).trim()}">${esc(r.suggest_qty)}</td>
      </tr>
      <tr id="${detailId}" class="inv-plan-detail-row" hidden>
        <td colspan="12">${stagesHtml(r.stages)}
          <span class="inv-plan-meta">场内 ${esc(r.inhouse_qty)} · 在途 ${esc(r.outsource_qty)} · PO ${esc(
        r.po_qty
      )} · 已出 ${esc(r.shipped_qty)}</span>
        </td>
      </tr>`;
    })
    .join("");

  tbody.querySelectorAll(".inv-plan-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("aria-controls");
      const row = id ? document.getElementById(id) : null;
      if (!row) return;
      const open = row.hidden;
      row.hidden = !open;
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.textContent = open ? "收起" : "明细";
    });
  });
}

async function loadPlanning() {
  const form = document.getElementById("planFilterForm");
  const customer = form ? form.customer.value.trim() : "";
  const q = form ? form.q.value.trim() : "";
  const params = new URLSearchParams();
  if (customer) params.set("customer", customer);
  if (q) params.set("q", q);
  const qs = params.toString() ? `?${params}` : "";
  const res = await fetch(`/api/inventory/planning${qs}`);
  const data = await res.json();
  if (!res.ok) {
    setMsg(data.error || "加载失败", false);
    return;
  }
  renderRows(data.items || []);
  setMsg("", true);
}

document.getElementById("planFilterForm")?.addEventListener("submit", (e) => {
  e.preventDefault();
  loadPlanning().catch((err) => setMsg(String(err), false));
});

(function initPlanLookup() {
  const form = document.getElementById("planFilterForm");
  if (!form || !window.InventoryBomLookup) return;
  if (form.customer) {
    window.InventoryBomLookup.bindCustomer({ customerInput: form.customer });
  }
  if (form.q) {
    window.InventoryBomLookup.bindKeyword({ keywordInput: form.q });
  }
})();

document.getElementById("planSeedDemo")?.addEventListener("click", async () => {
  setMsg("正在写入演示数据…", true);
  try {
    const res = await fetch("/api/inventory/planning/seed-demo", { method: "POST" });
    const data = await res.json();
    if (!res.ok) {
      setMsg(data.error || "写入失败", false);
      return;
    }
    const form = document.getElementById("planFilterForm");
    if (form) form.customer.value = "演示客户";
    setMsg(
      `已写入 PLAN-A/B/C：需求各 1000，可用库存约 500/600/700（成品+半成品）。共 ${(data.items || []).length} 行。`,
      true
    );
    await loadPlanning();
  } catch (err) {
    setMsg(String(err), false);
  }
});

loadPlanning().catch((err) => setMsg(String(err), false));
