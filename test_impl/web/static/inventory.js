function esc(t) {
  return String(t ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

let invEditMode = false;
let overviewFiltersSnapshot = null;

function snapshotOverviewFilters() {
  const form = invForm();
  if (!form) return null;
  return {
    product_part_no: form.product_part_no?.value ?? "",
    product_name: form.product_name?.value ?? "",
    customer_name: form.customer_name?.value ?? "",
  };
}

function restoreOverviewFilters(snapshot) {
  const form = invForm();
  if (!form || !snapshot) return;
  form.product_part_no.value = snapshot.product_part_no;
  if (form.product_name) form.product_name.value = snapshot.product_name;
  if (form.customer_name) form.customer_name.value = snapshot.customer_name;
  const hint = document.getElementById("invBomHint");
  if (hint) {
    hint.textContent = "";
    hint.hidden = true;
  }
}

function setBoardMsg(text, ok) {
  const el = document.getElementById("invBoardMsg");
  if (!el) return;
  el.textContent = text || "";
  el.className = "msg list-msg" + (text ? (ok ? " ok" : " error") : "");
}

function invForm() {
  return document.getElementById("invBoardForm");
}

function setPageMode(mode) {
  invEditMode = mode === "edit";
  const editSection = document.getElementById("invEditSection");
  const overviewSection = document.getElementById("invOverviewSection");
  const label = document.getElementById("invEditPartLabel");
  if (editSection) editSection.hidden = !invEditMode;
  if (overviewSection) overviewSection.hidden = invEditMode;
  if (!invEditMode && label) label.textContent = "";
  document.body.classList.toggle("inv-edit-mode", invEditMode);
}

function renderBoard(items) {
  const host = document.getElementById("invBoardCards");
  const empty = document.getElementById("invBoardEmpty");
  const count = document.getElementById("invBoardCount");
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
          const pendingHint = hasTransit
            ? `<div class="inv-stage-pending">待回货</div>`
            : "";
          return `<div class="${cls}">
            <div class="inv-stage-name">${esc(s.process_code)} ${esc(s.process_name)}</div>
            <div class="inv-stage-qty">场内库存 <b>${esc(s.inhouse_qty)}</b></div>
            <div class="inv-stage-qty">在途库存 <b>${esc(s.outsource_qty)}</b></div>
            <div class="inv-stage-qty">返修 <b>${esc(s.repair_qty || "0")}</b></div>
            ${pendingHint}
          </div>`;
        })
        .join("");
      const finishedBox = `<div class="inv-stage is-finished">
            <div class="inv-stage-name">成品库存</div>
            <div class="inv-stage-qty">成品库存 <b>${esc(row.finished_qty)}</b> PCS</div>
            <div class="inv-stage-qty">返修在途 <b>${esc(row.finished_repair_qty || "0")}</b> PCS</div>
          </div>`;
      return `<article class="inv-card" data-part-no="${esc(row.product_part_no)}" data-product-name="${esc(row.product_name || "")}" data-customer-name="${esc(row.customer_name || "")}">
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
          )}</span><button type="button" class="btn btn-outline btn-sm inv-card-edit">编辑</button></div>
        </div>
        <div class="inv-stages">${stages}${finishedBox}</div>
      </article>`;
    })
    .join("");

  host.querySelectorAll(".inv-card-edit").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const card = btn.closest(".inv-card");
      if (!card) return;
      openPartEditor({
        partNo: card.getAttribute("data-part-no") || "",
        productName: card.getAttribute("data-product-name") || "",
        customerName: card.getAttribute("data-customer-name") || "",
      });
    });
  });
}

async function openPartEditor({ partNo, productName = "", customerName = "" }) {
  const form = invForm();
  if (!form || !partNo) return;
  overviewFiltersSnapshot = snapshotOverviewFilters();
  setBoardMsg("", true);
  form.product_part_no.value = partNo;
  if (form.product_name) form.product_name.value = productName;
  if (form.customer_name) form.customer_name.value = customerName;
  const label = document.getElementById("invEditPartLabel");
  if (label) {
    const bits = [partNo];
    if (productName) bits.push(productName);
    if (customerName) bits.push(customerName);
    label.textContent = bits.join(" · ");
  }
  setPageMode("edit");
  window.InventoryEntry?.resetSelection?.();
  try {
    await window.InventoryEntry?.loadEntryPart?.();
  } catch (err) {
    setBoardMsg(String(err), false);
  }
}

async function exitEditMode() {
  restoreOverviewFilters(overviewFiltersSnapshot);
  overviewFiltersSnapshot = null;
  setPageMode("overview");
  window.InventoryEntry?.clearEntryBoard?.();
  setBoardMsg("", true);
  try {
    await loadBoardOverview();
  } catch (_e) {
    /* keep overview as-is */
  }
}

async function loadBoardOverview() {
  window.InventoryBomLookup?.closeAllCombos?.();
  const form = invForm();
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
  window.InventoryBomLookup?.closeAllCombos?.();
}

async function runInventoryQuery() {
  if (invEditMode) exitEditMode();
  setBoardMsg("", true);
  window.InventoryEntry?.clearEntryBoard?.();
  try {
    await loadBoardOverview();
  } catch (err) {
    setBoardMsg(String(err), false);
  }
}

window.loadBoardOverview = loadBoardOverview;
window.openPartEditor = openPartEditor;
window.exitInvEditMode = exitEditMode;
window.isInvEditMode = () => invEditMode;

document.getElementById("invBoardForm")?.addEventListener("submit", (e) => {
  e.preventDefault();
  runInventoryQuery();
});

document.getElementById("invBackOverview")?.addEventListener("click", () => {
  exitEditMode();
});

(function initBomLookup() {
  const form = invForm();
  if (!form || !window.InventoryBomLookup) return;
  const comboOpts = window.InventoryBomLookup?.STANDARD_COMBO_OPTS || {
    openOnFocus: true,
    minChars: 0,
    showToggle: true,
    simpleList: true,
  };
  ["product_part_no", "product_name", "customer_name"].forEach((name) => {
    const el = form.elements[name];
    if (el) {
      el.addEventListener("input", () => {
        if (invEditMode) window.InventoryEntry?.invalidateLoadedBoard?.();
      });
    }
  });
  window.InventoryBomLookup.bindPair({
    partInput: form.product_part_no,
    nameInput: form.product_name,
    customerInput: form.customer_name,
    hintEl: document.getElementById("invBomHint"),
    onSelect: () => {
      if (invEditMode) window.InventoryEntry?.invalidateLoadedBoard?.();
      form.requestSubmit();
    },
    ...comboOpts,
  });
  if (form.customer_name) {
    window.InventoryBomLookup.bindCustomer({ customerInput: form.customer_name, ...comboOpts });
  }
})();

setPageMode("overview");
runInventoryQuery();
