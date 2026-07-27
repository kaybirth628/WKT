let route = [];
let boardRow = null;
let selectedKey = ""; // process code or "FIN"
let selectedAction = "";
let supplierNames = [];

function esc(t) {
  return String(t ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString("zh-CN", { hour12: false });
  } catch (_e) {
    return iso;
  }
}

function setMsg(text, ok) {
  const el = document.getElementById("invEntryMsg");
  if (!el) return;
  el.hidden = !text;
  el.textContent = text || "";
  el.className = "msg list-msg" + (text ? (ok ? " ok" : " error") : "");
}

/** 载入成功后收起状态提示，腾出卡片空间 */
function setLoadedUi(loaded) {
  if (loaded) setMsg("", true);
}

function showEntrySuccess(detail) {
  return new Promise((resolve) => {
    const panel = document.getElementById("invActionPanel");
    const el = document.getElementById("invEntrySuccess");
    const detailEl = document.getElementById("invEntrySuccessDetail");
    if (!el) {
      resolve();
      return;
    }
    if (detailEl) detailEl.textContent = detail || "";
    el.hidden = false;
    el.classList.remove("is-leaving");
    if (panel) panel.classList.remove("is-submitting");
    window.setTimeout(() => {
      el.classList.add("is-leaving");
      window.setTimeout(() => {
        el.hidden = true;
        el.classList.remove("is-leaving");
        resolve();
      }, 380);
    }, 1500);
  });
}

function highlightMovementRow(movementId) {
  if (!movementId) return;
  const row = document.querySelector(`tr[data-mov-id="${movementId}"]`);
  if (!row) return;
  row.classList.add("inv-mov-flash-new");
  row.scrollIntoView({ block: "nearest", behavior: "smooth" });
  window.setTimeout(() => row.classList.remove("inv-mov-flash-new"), 1800);
}

function partNo() {
  const form = document.getElementById("invLoadForm");
  return form ? form.product_part_no.value.trim() : "";
}

function nextStep(code) {
  const idx = route.findIndex((s) => s.code === code);
  if (idx < 0 || idx >= route.length - 1) return null;
  return route[idx + 1];
}

function stepLabel(step) {
  if (!step) return "";
  return `${step.code} ${step.name}`;
}

function fillRouteSelect(selectEl, options, selected) {
  if (!selectEl) return;
  selectEl.innerHTML = options
    .map((opt) => {
      const val = typeof opt === "string" ? opt : opt.value;
      const label = typeof opt === "string" ? opt : opt.label;
      const sel = val === selected ? " selected" : "";
      return `<option value="${esc(val)}"${sel}>${esc(label)}</option>`;
    })
    .join("");
}

function syncOutboundToOptions() {
  const fromSel = document.getElementById("invOutboundFrom");
  const toSel = document.getElementById("invOutboundTo");
  if (!fromSel || !toSel) return;
  const fromCode = fromSel.value;
  if (fromCode === "FIN") {
    toSel.innerHTML = `<option value="">—</option>`;
    toSel.disabled = true;
    return;
  }
  toSel.disabled = false;
  const next = nextStep(fromCode);
  const opts = next
    ? [{ value: next.code, label: stepLabel(next) }]
    : [{ value: "", label: "请选择下道工序" }];
  fillRouteSelect(toSel, opts, next ? next.code : "");
}

function prevStep(code) {
  const idx = route.findIndex((s) => s.code === code);
  if (idx <= 0) return null;
  return route[idx - 1];
}

function stageRow(code) {
  return (boardRow?.stages || []).find((s) => s.process_code === code) || null;
}

function currentAdjustContext() {
  if (selectedKey === "FIN") {
    return {
      status: "finished",
      current: boardRow?.finished_qty || "0",
      label: "成品",
    };
  }
  const code = resolveAdjustProcessCode();
  const scope = document.getElementById("invAdjustScope")?.value || "inhouse";
  const stage = stageRow(code);
  if (scope === "outsource") {
    return {
      status: "outsource",
      current: stage?.outsource_qty || "0",
      label: "在途",
    };
  }
  return {
    status: "inhouse",
    current: stage?.inhouse_qty || "0",
    label: "场内",
  };
}

async function ensureSuppliers() {
  if (supplierNames.length) return supplierNames;
  try {
    const res = await fetch("/api/supplier-profiles");
    const data = await res.json();
    supplierNames = (data.rows || [])
      .map((row) => row.supplier)
      .filter(Boolean)
      .sort((a, b) => a.localeCompare(b, "zh-CN"));
  } catch (_e) {
    supplierNames = [];
  }
  return supplierNames;
}

function syncSupplierValue() {
  const hidden = document.getElementById("invSupplierHidden");
  const bom = document.getElementById("invSupplierBom");
  const sel = document.getElementById("invSupplierSelect");
  if (!hidden) return;
  if (bom && !bom.hidden) {
    hidden.value = bom.value.trim();
  } else if (sel && !sel.hidden) {
    hidden.value = (sel.value || "").trim();
  } else {
    hidden.value = "";
  }
}

function setupSupplierUI(bomSupplier) {
  const field = document.getElementById("invSupplierField");
  const bom = document.getElementById("invSupplierBom");
  const sel = document.getElementById("invSupplierSelect");
  const hidden = document.getElementById("invSupplierHidden");
  if (!field || !bom || !sel || !hidden) return;
  const fromBom = (bomSupplier || "").trim();
  if (fromBom) {
    bom.hidden = false;
    bom.value = fromBom;
    sel.hidden = true;
    sel.innerHTML = "";
    hidden.value = fromBom;
  } else {
    bom.hidden = true;
    bom.value = "";
    sel.hidden = false;
    const names = supplierNames.slice();
    sel.innerHTML =
      `<option value="">请选择供应商</option>` +
      names.map((n) => `<option value="${esc(n)}">${esc(n)}</option>`).join("");
    hidden.value = "";
  }
}

function renderStations() {
  const host = document.getElementById("invStationHost");
  if (!host) return;
  if (!boardRow) {
    host.hidden = true;
    host.innerHTML = "";
    return;
  }
  host.hidden = false;
  const stages = boardRow.stages || [];
  const stageHtml = stages
    .map((s) => {
      const transitQty = Number(s.outsource_qty);
      const hasTransit = Number.isFinite(transitQty) && transitQty > 0;
      const selected = selectedKey === s.process_code ? " is-selected" : "";
      const cls =
        "inv-stage inv-stage-clickable" +
        (s.is_outsource ? " is-outsource" : "") +
        (hasTransit ? " is-transit-pending" : "") +
        selected;
      const pendingHint = hasTransit ? `<div class="inv-stage-pending">待回货</div>` : "";
      return `<button type="button" class="${cls}" data-key="${esc(s.process_code)}" data-kind="process">
        <div class="inv-stage-name">${esc(s.process_code)} ${esc(s.process_name)}</div>
        <div class="inv-stage-qty">场内 <b>${esc(s.inhouse_qty)}</b></div>
        <div class="inv-stage-qty">在途 <b>${esc(s.outsource_qty)}</b></div>
        ${pendingHint}
      </button>`;
    })
    .join("");
  const finSelected = selectedKey === "FIN" ? " is-selected" : "";
  const tag = boardRow.data_tag || (boardRow.is_demo ? "测" : "实");
  const tagCls = tag === "测" ? "is-demo" : "is-real";
  const head = `<div class="inv-card-head inv-station-head">
    <div class="inv-card-title">
      <span class="inv-card-part">${esc(boardRow.product_part_no)}</span>${
        boardRow.product_name
          ? `<span class="inv-card-name">${esc(boardRow.product_name)}</span>`
          : ""
      }
    </div>
    <div class="inv-card-head-meta">${
      boardRow.customer_name
        ? `<span class="inv-card-customer" title="${esc(boardRow.customer_name)}">${esc(boardRow.customer_name)}</span>`
        : ""
    }<span class="inv-data-tag ${tagCls}">${esc(tag)}</span></div>
  </div>`;
  const finishedHtml = `<button type="button" class="inv-stage inv-stage-clickable is-finished${finSelected}" data-key="FIN" data-kind="finished">
    <div class="inv-stage-name">成品库存</div>
    <div class="inv-stage-qty"><b>${esc(boardRow.finished_qty)}</b> PCS</div>
  </button>`;
  host.innerHTML = `${head}<div class="inv-stages">${stageHtml}${finishedHtml}</div>`;
  host.querySelectorAll(".inv-stage-clickable").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectedKey = btn.getAttribute("data-key") || "";
      if (selectedKey === "FIN" && selectedAction === "inbound") {
        selectedAction = "outbound";
      }
      renderStations();
      renderActionPanel();
    });
  });
}

function resolveAdjustProcessCode() {
  if (selectedKey && selectedKey !== "FIN") return selectedKey;
  return document.getElementById("invInboundProcess")?.value || "";
}

async function renderActionPanel() {
  const panel = document.getElementById("invActionPanel");
  const btns = document.getElementById("invActionBtns");
  const supplierField = document.getElementById("invSupplierField");
  const inboundField = document.getElementById("invInboundField");
  const outboundFromField = document.getElementById("invOutboundFromField");
  const outboundToField = document.getElementById("invOutboundToField");
  if (!panel || !btns) return;
  if (!boardRow || !route.length) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const actions = [
    { id: "inbound", label: "入库" },
    { id: "outbound", label: "出库" },
    { id: "adjust", label: "校正库存" },
  ];
  if (!selectedAction) selectedAction = "inbound";
  btns.innerHTML = actions
    .map((a) => {
      const on = a.id === selectedAction ? " btn-primary" : " btn-outline";
      return `<button type="button" class="btn btn-sm${on} inv-pick-action" data-action="${a.id}">${esc(
        a.label
      )}</button>`;
    })
    .join("");
  btns.querySelectorAll(".inv-pick-action").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectedAction = btn.getAttribute("data-action") || "";
      renderActionPanel();
    });
  });

  document.getElementById("invActionType").value = selectedAction;
  const isInbound = selectedAction === "inbound";
  const isOutbound = selectedAction === "outbound";
  const isAdjust = selectedAction === "adjust";

  const inboundSel = document.getElementById("invInboundProcess");
  const outboundFromSel = document.getElementById("invOutboundFrom");
  const outboundToSel = document.getElementById("invOutboundTo");

  let inboundCode = route[0]?.code || "";
  if (selectedKey && selectedKey !== "FIN") {
    inboundCode = selectedKey;
  } else if (isInbound && inboundSel?.value) {
    inboundCode = inboundSel.value;
  }
  fillRouteSelect(
    inboundSel,
    route.map((s) => ({ value: s.code, label: stepLabel(s) })),
    inboundCode
  );

  let outboundFrom = route[0]?.code || "";
  if (selectedKey === "FIN") {
    outboundFrom = "FIN";
  } else if (selectedKey && selectedKey !== "FIN") {
    outboundFrom = selectedKey;
  } else if (isOutbound && outboundFromSel?.value) {
    outboundFrom = outboundFromSel.value;
  }
  const fromOpts = route.map((s) => ({ value: s.code, label: stepLabel(s) }));
  fromOpts.push({ value: "FIN", label: "成品（出库给客户）" });
  fillRouteSelect(outboundFromSel, fromOpts, outboundFrom);
  syncOutboundToOptions();
  if (isOutbound && outboundToSel && outboundFrom !== "FIN") {
    const nxt = nextStep(outboundFrom);
    if (nxt) outboundToSel.value = nxt.code;
  }

  if (inboundField) inboundField.hidden = !isInbound && !isAdjust;
  if (outboundFromField) outboundFromField.hidden = !isOutbound;
  if (outboundToField) outboundToField.hidden = !isOutbound;

  const adjustCode = resolveAdjustProcessCode();
  document.getElementById("invProcessCode").value = isAdjust
    ? selectedKey === "FIN"
      ? ""
      : adjustCode
    : isInbound
      ? inboundCode
      : outboundFrom === "FIN"
        ? ""
        : outboundFrom;

  const adjustScopeField = document.getElementById("invAdjustScopeField");
  const qtyInput = document.querySelector("#invQtyField input[name=qty]");
  const qtyLabel = document.getElementById("invQtyLabel");
  const isOutsourceStation =
    adjustCode && route.some((s) => s.code === adjustCode && s.is_outsource);
  if (adjustScopeField) adjustScopeField.hidden = !(isAdjust && isOutsourceStation && selectedKey !== "FIN");
  if (qtyLabel) qtyLabel.textContent = isAdjust ? "正确数量 (PCS)" : "数量 (PCS)";
  if (qtyInput) {
    qtyInput.min = isAdjust ? "0" : "0.1";
    qtyInput.step = "0.1";
    qtyInput.placeholder = isAdjust ? "填盘点后的正确余额" : "";
  }

  let needSupplier = false;
  let bomSupplier = "";
  if (isInbound) {
    const step = route.find((s) => s.code === inboundCode);
    const idx = route.findIndex((s) => s.code === inboundCode);
    needSupplier = Boolean(step?.is_outsource && idx > 0);
    bomSupplier = step?.supplier || "";
  } else if (isOutbound && outboundFrom !== "FIN") {
    const toCode = outboundToSel?.value || "";
    const toStep = route.find((s) => s.code === toCode);
    needSupplier = Boolean(toStep?.is_outsource);
    bomSupplier = toStep?.supplier || "";
  } else if (isAdjust && isOutsourceStation && selectedKey !== "FIN") {
    const scope = document.getElementById("invAdjustScope")?.value || "inhouse";
    needSupplier = scope === "outsource";
    const step = route.find((s) => s.code === adjustCode);
    bomSupplier = step?.supplier || "";
  }
  supplierField.hidden = !needSupplier;
  if (needSupplier) {
    await ensureSuppliers();
    setupSupplierUI(bomSupplier);
  } else {
    setupSupplierUI("");
    const hidden = document.getElementById("invSupplierHidden");
    if (hidden) hidden.value = "";
  }
}

let editingMovId = null;
let lastMovementItems = [];

function formatProcessCell(code, name) {
  const c = String(code ?? "").trim();
  const n = String(name ?? "").trim();
  if (!c && !n) return "—";
  if (c && n) return `${c} ${n}`;
  return c || n;
}

function renderMovements(items) {
  const tbody = document.getElementById("invEntryMovementBody");
  if (!tbody) return;
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="list-td-text">当日暂无出入库</td></tr>`;
    return;
  }
  tbody.innerHTML = items
    .map((r) => {
      const op = r.editable
        ? `<button type="button" class="btn btn-outline btn-sm inv-mov-edit" data-id="${esc(r.id)}">修改</button>`
        : `<span class="list-td-muted">—</span>`;
      const main = `<tr data-mov-id="${esc(r.id)}">
        <td>${esc(fmtDate(r.created_at))}</td>
        <td class="list-td-text">${esc(r.customer_name || "—")}</td>
        <td class="list-td-mono">${esc(r.product_part_no)}</td>
        <td class="list-td-text">${esc(r.product_name || "—")}</td>
        <td>${esc(r.action_label || r.action_type)}</td>
        <td>${esc(r.route_display || formatProcessCell(r.process_code, r.process_name))}</td>
        <td>${esc(r.qty)}</td>
        <td class="list-td-text">${esc(r.doc_no || "—")}</td>
        <td class="list-td-text">${esc(r.note || "—")}</td>
        <td>${op}</td>
      </tr>`;
      if (editingMovId !== r.id) return main;
      return (
        main +
        `<tr class="inv-mov-edit-row"><td colspan="10">
          <form class="inv-mov-edit-form" data-id="${esc(r.id)}">
            <label class="inv-mov-edit-field"><span>数量</span>
              <input name="qty" type="number" step="0.1" min="0.1" required value="${esc(r.qty)}" /></label>
            <label class="inv-mov-edit-field"><span>备注</span>
              <input name="note" type="text" value="${esc(r.note || "")}" placeholder="可选" /></label>
            <button type="submit" class="btn btn-primary btn-sm">保存</button>
            <button type="button" class="btn btn-outline btn-sm inv-mov-cancel">取消</button>
          </form>
        </td></tr>`
      );
    })
    .join("");
  tbody.querySelectorAll(".inv-mov-edit").forEach((btn) => {
    btn.addEventListener("click", () => {
      editingMovId = Number(btn.getAttribute("data-id"));
      renderMovements(lastMovementItems);
    });
  });
  tbody.querySelectorAll(".inv-mov-cancel").forEach((btn) => {
    btn.addEventListener("click", () => {
      editingMovId = null;
      renderMovements(lastMovementItems);
    });
  });
  tbody.querySelectorAll(".inv-mov-edit-form").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = Number(form.getAttribute("data-id"));
      const qty = form.qty.value;
      const note = form.note.value.trim();
      setMsg("保存修改中…", true);
      const res = await fetch(`/api/inventory/movements/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ qty, note }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMsg(data.error || "修改失败", false);
        return;
      }
      editingMovId = null;
      setMsg("✓ 已修改出入库流水，库存已同步", true);
      if (boardRow && partNo()) {
        await loadAll();
      } else {
        await loadTodayMovements();
      }
    });
  });
}

function todayYmd() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

async function loadTodayMovements() {
  const qs = `?on_date=${encodeURIComponent(todayYmd())}&limit=300`;
  const res = await fetch(`/api/inventory/movements${qs}`);
  const data = await res.json();
  if (!res.ok) {
    renderMovements([]);
    return;
  }
  lastMovementItems = data.items || [];
  renderMovements(lastMovementItems);
}

async function loadAll() {
  const form = document.getElementById("invLoadForm");
  const partInput = form?.product_part_no;
  const nameInput = form?.product_name;
  let part = partInput?.value.trim() || "";
  const nameQ = nameInput?.value.trim() || "";
  if (!part && !nameQ) {
    setMsg("请填写料号或产品名称", false);
    return;
  }
  if (!part && nameQ && window.InventoryBomLookup) {
    part = await window.InventoryBomLookup.resolvePartNo(
      partInput,
      nameInput,
      null,
      form?.customer_name || null
    );
  } else if (part && window.InventoryBomLookup) {
    await window.InventoryBomLookup.lookupByPartNo(
      partInput,
      nameInput,
      null,
      form?.customer_name || null
    );
    part = partInput?.value.trim() || part;
  }
  if (!part) {
    setMsg("未在 BOM 中找到对应料号", false);
    return;
  }
  const qs = `?product_part_no=${encodeURIComponent(part)}`;
  const [routeRes, boardRes] = await Promise.all([
    fetch(`/api/inventory/route${qs}`),
    fetch(`/api/inventory/board${qs}`),
  ]);
  const routeData = await routeRes.json();
  const boardData = await boardRes.json();
  if (!routeRes.ok) {
    setLoadedUi(false);
    setMsg(routeData.error || "载入工艺失败", false);
    boardRow = null;
    route = [];
    renderStations();
    document.getElementById("invActionPanel").hidden = true;
    return;
  }
  route = routeData.route || [];
  boardRow = (boardData.items || [])[0] || {
    product_part_no: part,
    product_name: "",
    customer_name: "",
    finished_qty: "0",
    is_demo: false,
    data_tag: "实",
    stages: route.map((s) => ({
      process_code: s.code,
      process_name: s.name,
      is_outsource: s.is_outsource,
      inhouse_qty: "0",
      outsource_qty: "0",
      suppliers: [],
    })),
  };
  if (selectedKey && selectedKey !== "FIN" && !route.some((s) => s.code === selectedKey)) {
    selectedKey = "";
    selectedAction = "";
  }
  renderStations();
  await renderActionPanel();
  await loadTodayMovements();
  setLoadedUi(true);
}

document.getElementById("invLoadForm")?.addEventListener("submit", (e) => {
  e.preventDefault();
  selectedKey = "";
  selectedAction = "";
  boardRow = null;
  setLoadedUi(false);
  loadAll().catch((err) => setMsg(String(err), false));
});

(function initInvEntryBomLookup() {
  const form = document.getElementById("invLoadForm");
  if (!form || !window.InventoryBomLookup) return;
  window.InventoryBomLookup.bindPair({
    partInput: form.product_part_no,
    nameInput: form.product_name,
    customerInput: form.customer_name,
    hintEl: null,
  });
  if (form.customer_name) {
    window.InventoryBomLookup.bindCustomer({ customerInput: form.customer_name });
  }
})();

document.getElementById("invSupplierSelect")?.addEventListener("change", syncSupplierValue);
document.getElementById("invAdjustScope")?.addEventListener("change", () => {
  if (selectedAction === "adjust") renderActionPanel();
});
document.getElementById("invInboundProcess")?.addEventListener("change", () => {
  const code = document.getElementById("invInboundProcess")?.value || "";
  if (code) selectedKey = code;
  if (selectedAction === "inbound" || selectedAction === "adjust") renderActionPanel();
});
document.getElementById("invOutboundFrom")?.addEventListener("change", () => {
  const code = document.getElementById("invOutboundFrom")?.value || "";
  selectedKey = code === "FIN" ? "FIN" : code;
  syncOutboundToOptions();
  if (selectedAction === "outbound") renderActionPanel();
});
document.getElementById("invOutboundTo")?.addEventListener("change", () => {
  if (selectedAction === "outbound") renderActionPanel();
});

document.getElementById("invSubmitForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const action = form.action_type.value;
  const part = partNo();
  if (!part) {
    setMsg("请先载入料号", false);
    return;
  }
  if (!action) {
    setMsg("请选择动作", false);
    return;
  }
  syncSupplierValue();
  const payload = {
    product_part_no: part,
    qty: form.qty.value,
    doc_no: "",
    note: form.note.value.trim(),
  };
  let url = "";
  if (action === "inbound") {
    url = "/api/inventory/inbound";
    payload.process_code = document.getElementById("invInboundProcess")?.value || "";
    if (!payload.process_code) {
      setMsg("请选择入库工序", false);
      return;
    }
    const step = route.find((s) => s.code === payload.process_code);
    const idx = route.findIndex((s) => s.code === payload.process_code);
    if (step?.is_outsource && idx > 0) {
      payload.supplier_name = (document.getElementById("invSupplierHidden") || {}).value || "";
      if (!payload.supplier_name.trim()) {
        setMsg("外发工序入库须选择供应商", false);
        return;
      }
    }
  } else if (action === "outbound") {
    url = "/api/inventory/outbound";
    payload.from_process_code = document.getElementById("invOutboundFrom")?.value || "";
    payload.to_process_code = document.getElementById("invOutboundTo")?.value || "";
    if (!payload.from_process_code) {
      setMsg("请选择出库起始工序", false);
      return;
    }
    if (payload.from_process_code !== "FIN" && !payload.to_process_code) {
      setMsg("请选择出库目标工序", false);
      return;
    }
    const toStep = route.find((s) => s.code === payload.to_process_code);
    if (toStep?.is_outsource) {
      payload.supplier_name = (document.getElementById("invSupplierHidden") || {}).value || "";
      if (!payload.supplier_name.trim()) {
        setMsg("发往外发工序须选择供应商", false);
        return;
      }
    }
  } else if (action === "adjust") {
    url = "/api/inventory/adjust";
    payload.target_qty = form.qty.value;
    if (selectedKey === "FIN") {
      payload.status = "finished";
    } else {
      payload.process_code = resolveAdjustProcessCode();
      if (!payload.process_code) {
        setMsg("请选择校正工序", false);
        return;
      }
      const scope = document.getElementById("invAdjustScope")?.value || "inhouse";
      payload.status = scope === "outsource" ? "outsource" : "inhouse";
      if (payload.status === "outsource") {
        payload.supplier_name = (document.getElementById("invSupplierHidden") || {}).value || "";
        if (!payload.supplier_name.trim()) {
          setMsg("在途校正须选择供应商", false);
          return;
        }
      }
    }
  } else {
    setMsg("未知动作", false);
    return;
  }
  setMsg("提交中…", true);
  const panel = document.getElementById("invActionPanel");
  const submitBtn = document.getElementById("invSubmitBtn");
  if (panel) panel.classList.add("is-submitting");
  if (submitBtn) submitBtn.disabled = true;
  let movementId = null;
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      setMsg(data.error || "失败", false);
      return;
    }
    movementId = data.movement?.id || null;
    const docNo = data.movement?.doc_no || "";
    const qtyLabel =
      action === "adjust" ? `校正至 ${payload.target_qty || payload.qty} PCS` : `${payload.qty} PCS`;
    const detail = docNo ? `单号 ${docNo} · ${qtyLabel}` : qtyLabel;
    form.qty.value = "";
    form.note.value = "";
    await showEntrySuccess(detail);
    await loadAll();
    setMsg(docNo ? `✓ 已登记，单号 ${docNo}` : "✓ 已登记，库存已更新", true);
    highlightMovementRow(movementId);
  } finally {
    if (panel) panel.classList.remove("is-submitting");
    if (submitBtn) submitBtn.disabled = false;
  }
});

loadTodayMovements().catch(() => renderMovements([]));
