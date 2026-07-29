function esc(t) {
  return String(t ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setMsg(text, ok) {
  const el = document.getElementById("invBoardMsg");
  if (!el) return;
  el.textContent = text || "";
  el.className = "msg list-msg" + (text ? (ok ? " ok" : " error") : "");
}

function renderBoard(items) {
  const host = document.getElementById("invBoardCards");
  const empty = document.getElementById("invBoardEmpty");
  const count = document.getElementById("invBoardCount");
  const INHOUSE_SUPPLIER_LABEL = "场内自制";
  if (!host) return;
  if (!items.length) {
    host.innerHTML = "";
    if (empty) empty.hidden = false;
    if (count) count.textContent = "共 0 条";
    return;
  }
  if (empty) empty.hidden = true;
  if (count) count.textContent = `共 ${items.length} 个料号`;
  host.innerHTML = items
    .map((row) => {
      const stages = (row.stages || [])
        .map((s) => {
          const transitQty = Number(s.outsource_qty);
          const hasTransit = Number.isFinite(transitQty) && transitQty > 0;
          const cls =
            "inv-stage" +
            (s.is_outsource ? " is-outsource" : "") +
            (hasTransit ? " is-transit-pending" : "");
          const supplierLine = (s.supplier || INHOUSE_SUPPLIER_LABEL).trim();
          const pendingHint = hasTransit
            ? `<div class="inv-stage-pending">待回货</div>`
            : "";
          return `<div class="${cls}">
            <div class="inv-stage-name">${esc(s.process_code)} ${esc(s.process_name)}</div>
            <div class="inv-stage-qty">场内库存 <b>${esc(s.inhouse_qty)}</b></div>
            <div class="inv-stage-qty">在途库存 <b>${esc(s.outsource_qty)}</b></div>
            <div class="inv-stage-qty">返修 <b>${esc(s.repair_qty || "0")}</b></div>
            <div class="inv-stage-supplier">供应商：${esc(supplierLine)}</div>
            ${pendingHint}
          </div>`;
        })
        .join("");
      const finishedBox = `<div class="inv-stage is-finished">
            <div class="inv-stage-name">成品库存</div>
            <div class="inv-stage-qty">成品库存 <b>${esc(row.finished_qty)}</b> PCS</div>
            <div class="inv-stage-qty">返修在途 <b>${esc(row.finished_repair_qty || "0")}</b> PCS</div>
          </div>`;
      return `<article class="inv-card">
        <div class="inv-card-head">
          <div class="inv-card-title">
            <span class="inv-card-part">${esc(row.product_part_no)}</span>${
              row.product_name
                ? `<span class="inv-card-name">${esc(row.product_name)}</span>`
                : ""
            }
          </div>
          <div class="inv-card-head-meta">${
            row.customer_name
              ? `<span class="inv-card-customer" title="${esc(row.customer_name)}">${esc(row.customer_name)}</span>`
              : ""
          }<span class="inv-data-tag ${row.data_tag === "测" ? "is-demo" : "is-real"}">${esc(
            row.data_tag || "实"
          )}</span></div>
        </div>
        <div class="inv-stages">${stages}${finishedBox}</div>
      </article>`;
    })
    .join("");
}

async function loadAll() {
  const form = document.getElementById("invBoardForm");
  const hint = document.getElementById("invBomHint");
  const partInput = form?.product_part_no;
  const nameInput = form?.product_name;
  const customerInput = form?.customer_name;
  let partNo = partInput?.value.trim() || "";
  const nameQ = nameInput?.value.trim() || "";
  const customerQ = customerInput?.value.trim() || "";
  if (!partNo && nameQ && window.InventoryBomLookup) {
    partNo = await window.InventoryBomLookup.resolvePartNo(
      partInput,
      nameInput,
      hint,
      customerInput
    );
  } else if (partNo && window.InventoryBomLookup) {
    await window.InventoryBomLookup.lookupByPartNo(partInput, nameInput, hint, customerInput);
  }
  const params = new URLSearchParams();
  if (partNo) params.set("product_part_no", partNo);
  if (customerQ) params.set("customer_name", customerQ);
  const qs = params.toString() ? `?${params.toString()}` : "";
  const boardRes = await fetch(`/api/inventory/board${qs}`);
  const board = await boardRes.json();
  renderBoard(board.items || []);
}

document.getElementById("invBoardForm")?.addEventListener("submit", (e) => {
  e.preventDefault();
  loadAll();
});

(function initBomLookup() {
  const form = document.getElementById("invBoardForm");
  if (!form || !window.InventoryBomLookup) return;
  window.InventoryBomLookup.bindPair({
    partInput: form.product_part_no,
    nameInput: form.product_name,
    customerInput: form.customer_name,
    hintEl: document.getElementById("invBomHint"),
  });
  if (form.customer_name) {
    window.InventoryBomLookup.bindCustomer({ customerInput: form.customer_name });
  }
})();

loadAll();
