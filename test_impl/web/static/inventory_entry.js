let route = [];
let boardRow = null;
let selectedStages = [];
let supplierNames = [];
let editPanelOpen = false;
let editingMovId = null;
let lastMovementItems = [];

const INHOUSE_SUPPLIER_LABEL = "场内自制";

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

function stepLabel(step) {
  if (!step) return "";
  return `${step.code} ${step.name}`;
}

function stageRow(code) {
  return (boardRow?.stages || []).find((s) => s.process_code === code) || null;
}

function routeStep(code) {
  return route.find((s) => s.code === code) || null;
}

function selectionBadge(index) {
  return String(index + 1);
}

function defaultSupplierForCode(code) {
  const stage = stageRow(code);
  const step = routeStep(code);
  return (stage?.supplier || step?.supplier || INHOUSE_SUPPLIER_LABEL).trim();
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

function supplierChoices() {
  const names = supplierNames.filter((n) => n !== INHOUSE_SUPPLIER_LABEL);
  return [INHOUSE_SUPPLIER_LABEL].concat(names);
}

function supplierChoicesForCode(code) {
  const step = routeStep(code);
  const bomSuppliers = (step?.suppliers || []).filter(Boolean);
  if (bomSuppliers.length) {
    const names = bomSuppliers.filter((n) => n !== INHOUSE_SUPPLIER_LABEL);
    return [INHOUSE_SUPPLIER_LABEL].concat(names);
  }
  return supplierChoices();
}

function renderSupplierComboHtml(fieldId, selectedValue, processCode) {
  const val = (selectedValue || "").trim();
  const display = val || "请选择供应商";
  const placeholderCls = val ? "" : " is-placeholder";
  const codeAttr = processCode ? ` data-process-code="${esc(processCode)}"` : "";
  return `
    <div class="process-supplier-combo inv-supplier-combo" data-field-id="${esc(fieldId)}"${codeAttr}>
      <input type="hidden" class="inv-supplier-hidden" name="${esc(fieldId)}" value="${esc(val)}" />
      <button type="button" class="inv-supplier-trigger" aria-expanded="false">
        <span class="inv-supplier-trigger-text${placeholderCls}">${esc(display)}</span>
      </button>
      <div class="inv-supplier-panel" hidden>
        <input type="text" class="inv-supplier-filter" placeholder="输入关键字搜索" autocomplete="off" />
        <ul class="process-supplier-list"></ul>
      </div>
    </div>`;
}

function getSupplierComboValue(combo) {
  const hidden = combo?.querySelector(".inv-supplier-hidden");
  return hidden ? hidden.value.trim() : "";
}

function setSupplierComboValue(combo, value) {
  const hidden = combo?.querySelector(".inv-supplier-hidden");
  const triggerText = combo?.querySelector(".inv-supplier-trigger-text");
  const panel = combo?.querySelector(".inv-supplier-panel");
  const trigger = combo?.querySelector(".inv-supplier-trigger");
  const filter = combo?.querySelector(".inv-supplier-filter");
  const v = (value || "").trim();
  if (hidden) hidden.value = v;
  if (triggerText) {
    triggerText.textContent = v || "请选择供应商";
    triggerText.classList.toggle("is-placeholder", !v);
  }
  if (panel) panel.hidden = true;
  if (trigger) trigger.setAttribute("aria-expanded", "false");
  if (filter) filter.value = "";
}

function bindSupplierCombos(root) {
  const scope = root || document;
  scope.querySelectorAll(".inv-supplier-combo").forEach((combo) => {
    if (combo.dataset.bound === "1") return;
    combo.dataset.bound = "1";
    const trigger = combo.querySelector(".inv-supplier-trigger");
    const panel = combo.querySelector(".inv-supplier-panel");
    const filter = combo.querySelector(".inv-supplier-filter");
    const list = combo.querySelector(".process-supplier-list");
    const hidden = combo.querySelector(".inv-supplier-hidden");
    if (!trigger || !panel || !filter || !list || !hidden) return;

    function renderList(query) {
      const q = String(query || "").trim().toLowerCase();
      const current = hidden.value || "";
      const processCode = combo.dataset.processCode || "";
      let items = processCode ? supplierChoicesForCode(processCode) : supplierChoices();
      if (q) items = items.filter((n) => n.toLowerCase().includes(q));
      if (!items.length) {
        list.innerHTML = '<li class="process-supplier-empty">无匹配供应商</li>';
        return;
      }
      list.innerHTML = items
        .map((name) => {
          const cls =
            "process-supplier-option" +
            (name === INHOUSE_SUPPLIER_LABEL ? " is-inhouse" : "") +
            (name === current ? " is-selected" : "");
          return `<li class="${cls}" data-value="${esc(name)}">${esc(name)}</li>`;
        })
        .join("");
    }

    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      const willOpen = panel.hidden;
      document.querySelectorAll(".inv-supplier-panel").forEach((p) => {
        p.hidden = true;
      });
      document.querySelectorAll(".inv-supplier-trigger").forEach((t) => {
        t.setAttribute("aria-expanded", "false");
      });
      if (willOpen) {
        panel.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
        renderList("");
        filter.focus();
      }
    });

    filter.addEventListener("input", () => renderList(filter.value));
    filter.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        panel.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
      } else if (e.key === "Enter") {
        const first = list.querySelector(".process-supplier-option");
        if (first) setSupplierComboValue(combo, first.dataset.value || "");
      }
    });

    list.addEventListener("mousedown", (e) => {
      const opt = e.target.closest(".process-supplier-option");
      if (!opt) return;
      e.preventDefault();
      setSupplierComboValue(combo, opt.dataset.value || "");
    });

    combo.addEventListener("click", (e) => e.stopPropagation());
  });

  if (!document.documentElement.dataset.invSupplierDocBound) {
    document.documentElement.dataset.invSupplierDocBound = "1";
    document.addEventListener("click", () => {
      document.querySelectorAll(".inv-supplier-panel").forEach((p) => {
        p.hidden = true;
      });
      document.querySelectorAll(".inv-supplier-trigger").forEach((t) => {
        t.setAttribute("aria-expanded", "false");
      });
    });
  }
}

function selectionHintText() {
  if (!selectedStages.length) return "";
  return selectedStages
    .map((code, idx) => {
      if (code === "FIN") return `${selectionBadge(idx)} 成品库存`;
      const step = routeStep(code);
      const stage = stageRow(code);
      const label = step ? stepLabel(step) : `${code} ${stage?.process_name || ""}`.trim();
      return `${selectionBadge(idx)} ${label}`;
    })
    .join("　");
}

function toggleStageSelection(code) {
  const idx = selectedStages.indexOf(code);
  if (idx >= 0) {
    selectedStages.splice(idx, 1);
  } else if (selectedStages.length >= 2) {
    setMsg("最多选择 2 道工序，请先清除再选", false);
    return;
  } else if (code === "FIN" && selectedStages.length === 1) {
    selectedStages = ["FIN"];
  } else if (selectedStages.includes("FIN")) {
    selectedStages = [code];
  } else {
    selectedStages.push(code);
  }
  editPanelOpen = false;
  renderStations();
}

function clearSelection() {
  selectedStages = [];
  editPanelOpen = false;
  renderStations();
}

function statusSelectHtml(name, selected) {
  const opts = [
    { value: "inhouse", label: "场内库存" },
    { value: "outsource", label: "在途库存" },
    { value: "repair", label: "返修" },
  ];
  return (
    `<select name="${esc(name)}">` +
    opts
      .map((o) => {
        const sel = o.value === selected ? " selected" : "";
        return `<option value="${esc(o.value)}"${sel}>${esc(o.label)}</option>`;
      })
      .join("") +
    "</select>"
  );
}

function renderSingleStageEditPanel(code) {
  const stage = stageRow(code);
  const step = routeStep(code);
  const label = step ? stepLabel(step) : code;
  const defaultSupplier = defaultSupplierForCode(code);
  return `<div class="inv-stage-edit-panel" id="invEditPanel">
    <div class="inv-stage-edit-head">
      <div class="inv-stage-edit-head-main">
        <span class="inv-stage-edit-title">编辑 ${esc(label)}</span>
        <span class="inv-flow-current-inline">当前：场内库存 <b>${esc(stage?.inhouse_qty || "0")}</b> · 在途库存 <b>${esc(stage?.outsource_qty || "0")}</b> · 返修 <b>${esc(stage?.repair_qty || "0")}</b></span>
      </div>
    </div>
    <form id="invSingleEditForm" class="inv-submit-row">
      <label class="field inv-inline-field inv-supplier-field">
        <span>供应商</span>
        ${renderSupplierComboHtml("supplier_name", defaultSupplier, code)}
      </label>
      <label class="field inv-inline-field">
        <span>场内库存 (PCS)</span>
        <input name="inhouse_qty" type="number" step="0.1" min="0" value="${esc(stage?.inhouse_qty || "0")}" required />
      </label>
      <label class="field inv-inline-field">
        <span>在途库存 (PCS)</span>
        <input name="outsource_qty" type="number" step="0.1" min="0" value="${esc(stage?.outsource_qty || "0")}" required />
      </label>
      <label class="field inv-inline-field">
        <span>返修 (PCS)</span>
        <input name="repair_qty" type="number" step="0.1" min="0" value="${esc(stage?.repair_qty || "0")}" required />
      </label>
      <div class="inv-submit-btn-wrap">
        <button type="submit" class="btn btn-primary btn-sm">保存</button>
        <button type="button" class="btn btn-outline btn-sm" id="invEditCancel">取消</button>
      </div>
    </form>
  </div>`;
}

function renderSingleFinishedEditPanel() {
  return `<div class="inv-stage-edit-panel" id="invEditPanel">
    <div class="inv-stage-edit-head">
      <div class="inv-stage-edit-head-main">
        <span class="inv-stage-edit-title">编辑 成品库存</span>
        <span class="inv-flow-current-inline">当前：成品库存 <b>${esc(boardRow?.finished_qty || "0")}</b> · 返修在途 <b>${esc(boardRow?.finished_repair_qty || "0")}</b></span>
      </div>
    </div>
    <form id="invSingleEditForm" class="inv-submit-row">
      <label class="field inv-inline-field">
        <span>成品库存 (PCS)</span>
        <input name="finished_qty" type="number" step="0.1" min="0" value="${esc(boardRow?.finished_qty || "0")}" required />
      </label>
      <label class="field inv-inline-field">
        <span>返修在途 (PCS)</span>
        <input name="finished_repair_qty" type="number" step="0.1" min="0" value="${esc(boardRow?.finished_repair_qty || "0")}" required />
      </label>
      <div class="inv-submit-btn-wrap">
        <button type="submit" class="btn btn-primary btn-sm">保存</button>
        <button type="button" class="btn btn-outline btn-sm" id="invEditCancel">取消</button>
      </div>
    </form>
  </div>`;
}

function renderDualFlowEditPanel() {
  const fromCode = selectedStages[0];
  const toCode = selectedStages[1];
  const fromStep = routeStep(fromCode);
  const toStep = routeStep(toCode);
  const fromStage = stageRow(fromCode);
  const toStage = stageRow(toCode);
  const fromLabel = fromStep ? stepLabel(fromStep) : fromCode;
  const toLabel = toStep ? stepLabel(toStep) : toCode;
  const fromSupplier = defaultSupplierForCode(fromCode);
  const toSupplier = defaultSupplierForCode(toCode);
  return `<div class="inv-stage-edit-panel" id="invEditPanel">
    <div class="inv-stage-edit-head">
      <div class="inv-stage-edit-head-main">
        <span class="inv-stage-edit-title">登记流转 ${esc(fromLabel)} → ${esc(toLabel)}</span>
        <span class="inv-flow-current-inline">① 流出 · ② 流入</span>
      </div>
    </div>
    <form id="invDualEditForm" class="inv-submit-row">
      <label class="field inv-inline-field inv-supplier-field">
        <span>① 流出供应商</span>
        ${renderSupplierComboHtml("from_supplier_name", fromSupplier, fromCode)}
      </label>
      <label class="field inv-inline-field">
        <span>① 流出状态</span>
        ${statusSelectHtml("from_status", "inhouse")}
      </label>
      <label class="field inv-inline-field inv-supplier-field">
        <span>② 流入供应商</span>
        ${renderSupplierComboHtml("to_supplier_name", toSupplier, toCode)}
      </label>
      <label class="field inv-inline-field">
        <span>② 流入状态</span>
        ${statusSelectHtml("to_status", toStep?.is_outsource ? "outsource" : "inhouse")}
      </label>
      <label class="field inv-inline-field">
        <span>数量 (PCS)</span>
        <input name="qty" type="number" step="0.1" min="0.1" required placeholder="转出数量" />
      </label>
      <div class="inv-submit-btn-wrap">
        <button type="submit" class="btn btn-primary btn-sm">保存流转</button>
        <button type="button" class="btn btn-outline btn-sm" id="invEditCancel">取消</button>
      </div>
    </form>
    <p class="inv-entry-mode-hint">当前：① 场内 <b>${esc(fromStage?.inhouse_qty || "0")}</b> / 在途 <b>${esc(fromStage?.outsource_qty || "0")}</b> / 返修 <b>${esc(fromStage?.repair_qty || "0")}</b>；② 场内 <b>${esc(toStage?.inhouse_qty || "0")}</b> / 在途 <b>${esc(toStage?.outsource_qty || "0")}</b> / 返修 <b>${esc(toStage?.repair_qty || "0")}</b></p>
  </div>`;
}

function renderEditPanelHtml() {
  if (!editPanelOpen || !selectedStages.length) return "";
  if (selectedStages.length === 1) {
    return selectedStages[0] === "FIN"
      ? renderSingleFinishedEditPanel()
      : renderSingleStageEditPanel(selectedStages[0]);
  }
  if (selectedStages.includes("FIN")) {
    return `<div class="inv-stage-edit-panel"><p class="inv-entry-mode-hint">成品与工序不能同时做双道流转，请只选 2 道工序或单独编辑成品。</p></div>`;
  }
  return renderDualFlowEditPanel();
}

function bindEditPanelEvents(host) {
  host.querySelector("#invEditBtn")?.addEventListener("click", async () => {
    if (!selectedStages.length) return;
    if (selectedStages.length === 2 && selectedStages.includes("FIN")) {
      setMsg("成品与工序不能同时做双道流转", false);
      return;
    }
    await ensureSuppliers();
    editPanelOpen = true;
    renderStations();
  });

  host.querySelector("#invClearSelBtn")?.addEventListener("click", () => {
    clearSelection();
    setMsg("", true);
  });

  host.querySelector("#invEditCancel")?.addEventListener("click", () => {
    editPanelOpen = false;
    renderStations();
  });

  host.querySelector("#invSingleEditForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const part = partNo();
    if (!part) {
      setMsg("请先载入料号", false);
      return;
    }
    const code = selectedStages[0];
    let payload;
    let url;
    if (code === "FIN") {
      url = "/api/inventory/stage-set";
      payload = {
        product_part_no: part,
        process_code: "FIN",
        finished_qty: form.finished_qty.value,
        finished_repair_qty: form.finished_repair_qty.value,
      };
    } else {
      const combo = form.querySelector(".inv-supplier-combo");
      const supplier = getSupplierComboValue(combo);
      if (!supplier) {
        setMsg("请选择供应商", false);
        return;
      }
      url = "/api/inventory/stage-set";
      payload = {
        product_part_no: part,
        process_code: code,
        inhouse_qty: form.inhouse_qty.value,
        outsource_qty: form.outsource_qty.value,
        repair_qty: form.repair_qty.value,
        supplier_name: supplier,
      };
    }
    setMsg("保存中…", true);
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        setMsg(data.error || "保存失败", false);
        return;
      }
      editPanelOpen = false;
      selectedStages = [];
      await loadAll();
      const mov = data.movement || (data.movements || [])[data.movements?.length - 1];
      setMsg("✓ 已保存，库存已更新", true);
      highlightMovementRow(mov?.id);
    } catch (err) {
      setMsg(String(err), false);
    }
  });

  host.querySelector("#invDualEditForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const part = partNo();
    if (!part) {
      setMsg("请先载入料号", false);
      return;
    }
    const fromCombo = form.querySelector('[data-field-id="from_supplier_name"]');
    const toCombo = form.querySelector('[data-field-id="to_supplier_name"]');
    const fromSupplier = getSupplierComboValue(fromCombo);
    const toSupplier = getSupplierComboValue(toCombo);
    if (!fromSupplier || !toSupplier) {
      setMsg("两道均须选择供应商", false);
      return;
    }
    const payload = {
      product_part_no: part,
      from_process_code: selectedStages[0],
      from_status: form.from_status.value,
      to_process_code: selectedStages[1],
      to_status: form.to_status.value,
      qty: form.qty.value,
      from_supplier_name: fromSupplier,
      to_supplier_name: toSupplier,
    };
    setMsg("保存流转中…", true);
    try {
      const res = await fetch("/api/inventory/stage-flow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        setMsg(data.error || "流转失败", false);
        return;
      }
      editPanelOpen = false;
      selectedStages = [];
      await loadAll();
      setMsg("✓ 已登记流转", true);
      highlightMovementRow(data.movement?.id);
    } catch (err) {
      setMsg(String(err), false);
    }
  });

  bindSupplierCombos(host);
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
      const selIdx = selectedStages.indexOf(s.process_code);
      const selected = selIdx >= 0 ? " is-selected" : "";
      const badge =
        selIdx >= 0 ? `<span class="inv-stage-badge">${selectionBadge(selIdx)}</span>` : "";
      const transitQty = Number(s.outsource_qty);
      const hasTransit = Number.isFinite(transitQty) && transitQty > 0;
      const cls =
        "inv-stage inv-stage-clickable" +
        (s.is_outsource ? " is-outsource" : "") +
        (hasTransit ? " is-transit-pending" : "") +
        selected;
      const pendingHint = hasTransit ? `<div class="inv-stage-pending">待回货</div>` : "";
      const supplierLine = (s.supplier || INHOUSE_SUPPLIER_LABEL).trim();
      return `<button type="button" class="${cls}" data-key="${esc(s.process_code)}" data-kind="process">
        ${badge}
        <div class="inv-stage-name">${esc(s.process_code)} ${esc(s.process_name)}</div>
        <div class="inv-stage-qty">场内库存 <b>${esc(s.inhouse_qty)}</b></div>
        <div class="inv-stage-qty">在途库存 <b>${esc(s.outsource_qty)}</b></div>
        <div class="inv-stage-qty">返修 <b>${esc(s.repair_qty || "0")}</b></div>
        <div class="inv-stage-supplier">供应商：${esc(supplierLine)}</div>
        ${pendingHint}
      </button>`;
    })
    .join("");

  const finIdx = selectedStages.indexOf("FIN");
  const finSelected = finIdx >= 0 ? " is-selected" : "";
  const finBadge =
    finIdx >= 0 ? `<span class="inv-stage-badge">${selectionBadge(finIdx)}</span>` : "";
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
        ? `<span class="inv-card-customer">${esc(boardRow.customer_name)}</span>`
        : ""
    }<span class="inv-data-tag ${tagCls}">${esc(tag)}</span></div>
  </div>`;

  const finishedHtml = `<button type="button" class="inv-stage inv-stage-clickable is-finished${finSelected}" data-key="FIN" data-kind="finished">
    ${finBadge}
    <div class="inv-stage-name">成品库存</div>
    <div class="inv-stage-qty">成品库存 <b>${esc(boardRow.finished_qty)}</b> PCS</div>
    <div class="inv-stage-qty">返修在途 <b>${esc(boardRow.finished_repair_qty || "0")}</b> PCS</div>
  </button>`;

  const selectBar =
    selectedStages.length > 0
      ? `<div class="inv-select-bar">
          <span class="inv-select-hint">${esc(selectionHintText())}</span>
          <button type="button" class="btn btn-primary btn-sm" id="invEditBtn">编辑</button>
          <button type="button" class="btn btn-outline btn-sm" id="invClearSelBtn">清除</button>
        </div>`
      : "";

  host.innerHTML = `${head}<div class="inv-stages">${stageHtml}${finishedHtml}</div>${selectBar}${renderEditPanelHtml()}`;

  host.querySelectorAll(".inv-stage-clickable").forEach((btn) => {
    btn.addEventListener("click", () => {
      toggleStageSelection(btn.getAttribute("data-key") || "");
    });
  });

  bindEditPanelEvents(host);
}

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
    tbody.innerHTML = `<tr><td colspan="10" class="list-td-text">暂无出入库记录</td></tr>`;
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
        await loadMovements();
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

async function loadMovements() {
  const part = partNo();
  let qs;
  if (part && boardRow) {
    qs = `?product_part_no=${encodeURIComponent(part)}&limit=300`;
  } else {
    qs = `?on_date=${encodeURIComponent(todayYmd())}&limit=300`;
  }
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
    selectedStages = [];
    editPanelOpen = false;
    renderStations();
    return;
  }
  route = routeData.route || [];
  boardRow = (boardData.items || [])[0] || {
    product_part_no: part,
    product_name: "",
    customer_name: "",
    finished_qty: "0",
    finished_repair_qty: "0",
    is_demo: false,
    data_tag: "实",
    stages: route.map((s) => ({
      process_code: s.code,
      process_name: s.name,
      is_outsource: s.is_outsource,
      supplier: s.supplier || "",
      inhouse_qty: "0",
      outsource_qty: "0",
      repair_qty: "0",
    })),
  };
  selectedStages = selectedStages.filter(
    (code) => code === "FIN" || route.some((s) => s.code === code)
  );
  renderStations();
  await loadMovements();
  setLoadedUi(true);
}

document.getElementById("invLoadForm")?.addEventListener("submit", (e) => {
  e.preventDefault();
  selectedStages = [];
  editPanelOpen = false;
  boardRow = null;
  setLoadedUi(false);
  loadAll().catch((err) => setMsg(String(err), false));
});

(function initInvEntryBomLookup() {
  const form = document.getElementById("invLoadForm");
  if (!form || !window.InventoryBomLookup) return;
  const comboOpts = window.InventoryBomLookup?.STANDARD_COMBO_OPTS || {
    openOnFocus: true,
    minChars: 0,
    showToggle: true,
    simpleList: true,
  };
  window.InventoryBomLookup.bindPair({
    partInput: form.product_part_no,
    nameInput: form.product_name,
    customerInput: form.customer_name,
    hintEl: null,
    ...comboOpts,
  });
  if (form.customer_name) {
    window.InventoryBomLookup.bindCustomer({ customerInput: form.customer_name, ...comboOpts });
  }
})();

loadMovements().catch(() => renderMovements([]));
