let records = [];
let allRecords = [];
let processOptions = [];
let materialOptions = [];
let editingRecordId = null;
let detailRecordId = null;
let queryCombosReady = false;
let editCombosReady = false;

const QUERY_COLS = [
  { field: "customer_name", label: "客户" },
  { field: "product_name", label: "产品名称" },
  { field: "product_part_no", label: "产品料号" },
  { field: "material", label: "材质" },
  { field: "unit_weight_g", label: "单重(g)" },
  { field: "machine_tonnage", label: "机台" },
  { field: "process_count", label: "工序数" },
  { field: "unit_cost", label: "单件成本" },
  { field: "updated_at", label: "更新时间" },
];

function queryCellKey(row, field) {
  let raw = "";
  switch (field) {
    case "customer_name":
      raw = row.customer_name;
      break;
    case "product_name":
      raw = row.product_name;
      break;
    case "product_part_no":
      raw = row.product_part_no;
      break;
    case "material":
      raw = row.material;
      break;
    case "unit_weight_g":
      raw = row.unit_weight_g;
      break;
    case "machine_tonnage":
      raw = row.machine_tonnage;
      break;
    case "process_count":
      raw = String((row.process_selections || row.selected_processes || []).length);
      break;
    case "unit_cost":
      raw = CostCommon.money(row.unit_cost);
      break;
    case "updated_at":
      raw = CostCommon.formatDate(row.updated_at || row.created_at);
      break;
    default:
      raw = "";
  }
  raw = String(raw ?? "").trim();
  return raw || "(空白)";
}

const queryColFilter = window.createListColFilter({
  prefix: "costQueryColFilter",
  headSelector: "#costQueryHead",
  columns: QUERY_COLS,
  getCellKey: queryCellKey,
  onChange(filtered, meta) {
    records = filtered;
    updateQueryCount(meta.shown, meta.total, meta.filtered);
    renderTable(filtered, { isFiltered: meta.filtered });
  },
});

function updateQueryCount(shown, total, filtered) {
  const el = document.getElementById("costQueryCount");
  if (!el) return;
  if (!total) {
    el.textContent = "共 0 条";
    return;
  }
  if (filtered && shown !== total) {
    el.textContent = `显示 ${shown} / 共 ${total} 条`;
    return;
  }
  el.textContent = `共 ${total} 条`;
}

function sortRecordsByUpdatedDesc(rows) {
  return (rows || []).slice().sort((a, b) => {
    const ta = String(a.updated_at || a.created_at || "");
    const tb = String(b.updated_at || b.created_at || "");
    if (ta !== tb) return tb.localeCompare(ta);
    return (Number(b.id) || 0) - (Number(a.id) || 0);
  });
}

function refreshQueryTable() {
  allRecords = sortRecordsByUpdatedDesc(allRecords || []);
  queryColFilter.setRows(allRecords);
  queryColFilter.bindHeader();
  queryColFilter.refresh();
}

function escHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function bindRowCellTips(tbody) {
  if (!tbody) return;
  tbody.querySelectorAll("td.list-td-text, td.list-td-mono").forEach((td) => {
    td.classList.add("no-hover-tip");
    td.removeAttribute("data-hover-text");
    td.classList.remove("has-ellipsis-tip");
  });
}

function initQueryFilterCombos() {
  if (queryCombosReady) return;
  const form = document.getElementById("costQueryForm");
  const IBL = window.InventoryBomLookup;
  if (!form || !IBL) return;
  queryCombosReady = true;
  const opts = IBL.STANDARD_COMBO_OPTS;
  IBL.bindKeyword({ keywordInput: form.q, ...opts });
  IBL.bindCustomer({
    customerInput: form.customer,
    fetchSuggestions: IBL.fetchMasterCustomerSuggestions,
    ...opts,
  });
  IBL.bindPartOnly({
    partInput: form.product_part_no,
    customerInput: form.customer,
    ...opts,
  });
}

function initEditModalCombos() {
  if (editCombosReady) return;
  const form = document.getElementById("costEditForm");
  const IBL = window.InventoryBomLookup;
  if (!form || !IBL) return;
  editCombosReady = true;
  const opts = IBL.STANDARD_COMBO_OPTS;
  IBL.bindCustomer({
    customerInput: form.customer_name,
    fetchSuggestions: IBL.fetchMasterCustomerSuggestions,
    ...opts,
  });
  IBL.bindPair({
    partInput: form.product_part_no,
    nameInput: form.product_name,
    customerInput: form.customer_name,
    ...opts,
  });
  if (materialOptions.length) {
    IBL.bindMaterialList(form.material, materialOptions);
  }
}

function renderTable(items, opts) {
  const options = opts || {};
  const tbody = document.getElementById("costQueryBody");
  const empty = document.getElementById("costQueryEmpty");
  if (!tbody) return;

  if (!items.length) {
    tbody.innerHTML = "";
    if (empty) {
      empty.hidden = false;
      empty.textContent = options.isFiltered
        ? "无匹配结果，请调整列筛选或查询条件"
        : "暂无记录，请先在「BOM录入」中保存";
    }
    return;
  }
  if (empty) empty.hidden = true;

  tbody.innerHTML = items
    .map((r, idx) => {
      const processCount = (r.process_selections || r.selected_processes || []).length;
      return `
    <tr data-id="${r.id}" tabindex="0">
      <td class="list-td-seq">${idx + 1}</td>
      <td class="list-td-text">${escHtml(r.customer_name)}</td>
      <td class="list-td-text">${escHtml(r.product_name)}</td>
      <td class="list-td-mono">${
        r.is_demo
          ? '<span class="inv-data-tag is-demo" style="margin-right:0.35rem">测</span>'
          : ""
      }${escHtml(r.product_part_no)}</td>
      <td>${escHtml(r.material)}</td>
      <td>${escHtml(r.unit_weight_g)}</td>
      <td>${escHtml(r.machine_tonnage)}</td>
      <td>${processCount}</td>
      <td class="list-td-money">${CostCommon.money(r.unit_cost)}</td>
      <td>${escHtml(CostCommon.formatDate(r.updated_at || r.created_at))}</td>
      <td class="action-cell">
        <button type="button" class="btn btn-outline btn-sm" data-action="edit" data-id="${r.id}">修改</button>
        <button type="button" class="btn btn-danger btn-sm" data-action="delete" data-id="${r.id}">删除</button>
      </td>
    </tr>`;
    })
    .join("");

  bindRowCellTips(tbody);

  tbody.querySelectorAll("tr[data-id]").forEach((row) => {
    let press = null;
    row.addEventListener("mousedown", (e) => {
      if (e.target.closest("[data-action]")) return;
      press = { x: e.clientX, y: e.clientY };
    });
    row.addEventListener("click", (e) => {
      if (e.target.closest("[data-action]")) return;
      const sel = window.getSelection();
      if (sel && sel.toString().trim()) return;
      if (press) {
        const dx = Math.abs(e.clientX - press.x);
        const dy = Math.abs(e.clientY - press.y);
        if (dx > 4 || dy > 4) return;
      }
      openDetail(Number(row.dataset.id));
    });
    row.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        if (e.target.closest("[data-action]")) return;
        e.preventDefault();
        openDetail(Number(row.dataset.id));
      }
    });
  });

  tbody.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = Number(btn.dataset.id);
      if (btn.dataset.action === "edit") openEdit(id);
      if (btn.dataset.action === "delete") deleteRecord(id);
    });
  });
}

function openDetail(id) {
  detailRecordId = id;
  const record = records.find((r) => r.id === id);
  if (!record) return;
  const modal = document.getElementById("costDetailModal");
  const body = document.getElementById("costDetailBody");
  body.innerHTML = CostCommon.renderCostRecordDetailHtml(record);
  if (window.HoverTip) {
    window.HoverTip.hide();
    body.querySelectorAll(".process-name, .process-detail-name").forEach((el) => {
      if (window.HoverTip.needsTip(el)) window.HoverTip.bind(el);
    });
  }
  modal.hidden = false;
}

function closeDetail() {
  document.getElementById("costDetailModal").hidden = true;
  detailRecordId = null;
}

function selectedByCodeToDetailState(selectedByCode) {
  const state = {};
  Object.entries(selectedByCode || {}).forEach(([code, entry]) => {
    if (entry != null && typeof entry === "object") {
      state[code] = {
        price: entry.price != null ? entry.price : "",
        suppliers:
          entry.suppliers || (entry.supplier ? [entry.supplier] : []),
      };
    } else if (entry != null) {
      state[code] = { price: entry, suppliers: [] };
    }
  });
  return state;
}

function renderEditProcessGrid(selectedByCode, processOrder) {
  const grid = document.getElementById("editProcessGrid");
  if (!grid) return;
  grid.innerHTML = CostCommon.renderProcessPickOnlyGridHtml(processOptions, selectedByCode);
  CostCommon.bindStagedProcessPicker(
    grid,
    "editProcessDetailPanel",
    processOptions,
    () => CostCommon.refreshProcessOrder("editProcessGrid"),
    {
      blockId: "editProcessDetailBlock",
      initialState: selectedByCodeToDetailState(selectedByCode),
    }
  );
  const order =
    Array.isArray(processOrder) && processOrder.length
      ? processOrder
      : Object.keys(selectedByCode || {}).sort();
  CostCommon.setProcessOrder("editProcessGrid", order);
}

function collectEditProcessPrices() {
  return CostCommon.collectProcessEntries("#costEditForm");
}

function openEdit(id) {
  const record = records.find((r) => r.id === id);
  if (!record) return;
  editingRecordId = id;
  closeDetail();

  const form = document.getElementById("costEditForm");
  form.customer_name.value = record.customer_name;
  form.product_name.value = record.product_name;
  form.mold_no.value = record.mold_no;
  form.product_part_no.value = record.product_part_no;
  form.cavity.value = record.cavity;
  form.unit_weight_g.value = record.unit_weight_g;
  form.material.value = record.material;
  form.machine_tonnage.value = record.machine_tonnage;
  form.material_unit_price.value = record.material_unit_price || "0";

  renderEditProcessGrid(
    CostCommon.selectionsToMap(record.process_selections, record.process_prices),
    record.process_order || (record.process_selections || []).map((s) => s.code)
  );
  document.getElementById("costEditMsg").textContent = "";
  document.getElementById("costEditModal").hidden = false;
}

function closeEdit() {
  document.getElementById("costEditModal").hidden = true;
  editingRecordId = null;
}

function isEditModalOpen() {
  const modal = document.getElementById("costEditModal");
  return !!(modal && !modal.hidden);
}

function isEditSupplierDropdownOpen() {
  if (!isEditModalOpen()) return false;
  return !!(
    document.querySelector("#costEditModal .process-supplier-list:not([hidden])") ||
    document.querySelector("#costEditModal .inv-bom-suggest:not([hidden])")
  );
}

async function saveEdit(e) {
  e.preventDefault();
  if (!editingRecordId) return;
  const form = document.getElementById("costEditForm");
  const msg = document.getElementById("costEditMsg");
  const { byCode, order } = collectEditProcessPrices();
  if (!Object.keys(byCode).length) {
    msg.textContent = "请至少选择一道工序";
    msg.className = "msg error";
    return;
  }
  const missing = CostCommon.validateProcessSuppliers("#costEditForm");
  if (missing.length) {
    msg.textContent = `外发工序请至少添加一个供应商：${missing.join("、")}`;
    msg.className = "msg error";
    return;
  }

  const payload = {
    customer_name: form.customer_name.value.trim(),
    product_name: form.product_name.value.trim(),
    mold_no: form.mold_no.value.trim(),
    product_part_no: form.product_part_no.value.trim(),
    cavity: form.cavity.value.trim(),
    unit_weight_g: form.unit_weight_g.value.trim(),
    material: form.material.value.trim(),
    machine_tonnage: form.machine_tonnage.value.trim(),
    material_unit_price: form.material_unit_price.value || "0",
    process_prices: byCode,
    process_order: order,
  };

  const res = await fetch(`/api/cost/records/${editingRecordId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    msg.textContent = data.error || "保存失败";
    msg.className = "msg error";
    return;
  }

  closeEdit();
  await loadRecords();
}

async function deleteRecord(id) {
  const record = records.find((r) => r.id === id);
  const label = record ? `${record.product_part_no}（${record.customer_name}）` : `#${id}`;
  if (!window.confirm(`确定删除成本记录 ${label}？此操作不可恢复。`)) return;

  const res = await fetch(`/api/cost/records/${id}`, { method: "DELETE" });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "删除失败");
    return;
  }
  if (detailRecordId === id) closeDetail();
  if (editingRecordId === id) closeEdit();
  await loadRecords();
}

async function loadRecords() {
  const form = document.getElementById("costQueryForm");
  const params = new URLSearchParams();
  const q = form.q.value.trim();
  const customer = form.customer.value.trim();
  const productPartNo = form.product_part_no.value.trim();
  if (q) params.set("q", q);
  if (customer) params.set("customer", customer);
  if (productPartNo) params.set("product_part_no", productPartNo);

  const res = await fetch("/api/cost/records?" + params.toString());
  const data = await res.json();
  allRecords = data.records || [];
  refreshQueryTable();
}

function applyQueryFromUrl() {
  const form = document.getElementById("costQueryForm");
  if (!form) return;
  const sp = new URLSearchParams(window.location.search);
  ["q", "customer", "product_part_no"].forEach((key) => {
    const value = sp.get(key);
    if (value && form.elements[key]) {
      form.elements[key].value = value;
    }
  });
}

document.getElementById("costQueryForm").addEventListener("submit", (e) => {
  e.preventDefault();
  loadRecords();
});

document.getElementById("costQueryReset").addEventListener("click", () => {
  document.getElementById("costQueryForm").reset();
  queryColFilter.clearAll();
  loadRecords();
});

document.getElementById("costQueryClearColFilters")?.addEventListener("click", () => {
  queryColFilter.clearAll();
});

document.getElementById("costDetailClose").addEventListener("click", closeDetail);
document.getElementById("costDetailEdit").addEventListener("click", () => {
  if (detailRecordId) openEdit(detailRecordId);
});
document.getElementById("costDetailDelete").addEventListener("click", () => {
  if (detailRecordId) deleteRecord(detailRecordId);
});
document.getElementById("costDetailModal").addEventListener("click", (e) => {
  if (e.target.id === "costDetailModal") closeDetail();
});

document.getElementById("costEditClose").addEventListener("click", closeEdit);
document.getElementById("costEditCancel").addEventListener("click", closeEdit);
document.getElementById("costEditForm").addEventListener("submit", saveEdit);
document.getElementById("costEditForm").addEventListener("keydown", (e) => {
  if (e.key !== "Enter") return;
  const tag = (e.target && e.target.tagName) || "";
  if (tag === "TEXTAREA") return;
  if (e.target && e.target.type === "submit") return;
  if (e.target && e.target.closest(".process-supplier-combo, .inv-bom-combo, .process-detail-row")) return;
  e.preventDefault();
});

document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (isEditSupplierDropdownOpen()) return;
  const detailModal = document.getElementById("costDetailModal");
  if (isEditModalOpen()) {
    closeEdit();
    return;
  }
  if (detailModal && !detailModal.hidden) closeDetail();
});

CostCommon.loadOptions()
  .then(({ processOptions: opts, materials }) => {
    processOptions = opts || [];
    materialOptions = materials || [];
    initEditModalCombos();
    CostCommon.bindProcessOrder(
      "editProcessGrid",
      "editProcessOrderList",
      "editProcessOrderBlock",
      processOptions
    );
    return CostCommon.loadSuppliers().catch(() => []);
  })
  .then(() => {
    initQueryFilterCombos();
    queryColFilter.bindHeader();
    applyQueryFromUrl();
    return loadRecords();
  });
