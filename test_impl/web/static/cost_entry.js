let selectedCount = 0;
let entryProcessOptions = [];
let processLabelByName = {};
let lastLookupPart = "";
let lookupSeq = 0;
let processGridTouched = false;
let applyingProcessPrices = false;
let processApplyTimer = null;
const PROCESS_APPLY_DELAY_MS = 400;

function getCheckedProcessCodes() {
  return Array.from(document.querySelectorAll("#processGrid .process-pick:checked"))
    .map((cb) => cb.dataset.processCode)
    .filter(Boolean)
    .sort();
}

function cancelPendingProcessApply() {
  if (processApplyTimer) {
    clearTimeout(processApplyTimer);
    processApplyTimer = null;
  }
}

function shouldSkipProcessApply(checkedAtStart) {
  if (processGridTouched) return true;
  if ((checkedAtStart || []).length > 0) return true;
  return getCheckedProcessCodes().length > 0;
}

function scheduleProcessApply(processPrices, processSelections, checkedAtStart) {
  cancelPendingProcessApply();
  if (!hasProcessLookupData(processPrices, processSelections)) return;
  const snapshot = (checkedAtStart || []).slice();
  processApplyTimer = setTimeout(() => {
    processApplyTimer = null;
    if (shouldSkipProcessApply(snapshot)) return;
    applyProcessPrices(processPrices, processSelections);
  }, PROCESS_APPLY_DELAY_MS);
}

function hasProcessLookupData(processPrices, processSelections) {
  if (Array.isArray(processSelections) && processSelections.length) return true;
  if (processPrices && typeof processPrices === "object" && Object.keys(processPrices).length) {
    return true;
  }
  return false;
}

function buildProcessPricesByCode(processPrices, processSelections) {
  const byCode = {};
  if (Array.isArray(processSelections) && processSelections.length) {
    processSelections.forEach((item) => {
      byCode[item.code] = {
        price: item.price,
        supplier: item.supplier || "",
        suppliers: item.suppliers || (item.supplier ? [item.supplier] : []),
      };
    });
  } else if (processPrices && Object.keys(processPrices).length) {
    Object.entries(processPrices).forEach(([code, val]) => {
      if (val && typeof val === "object") {
        byCode[code] = {
          price: val.price != null ? val.price : "0",
          supplier: val.supplier || "",
          suppliers: val.suppliers || (val.supplier ? [val.supplier] : []),
        };
      } else {
        byCode[code] = { price: val, supplier: "", suppliers: [] };
      }
    });
  }
  return byCode;
}

function setProcessGridLoading(loading) {
  const grid = document.getElementById("processGrid");
  if (grid) grid.classList.toggle("is-lookup-loading", loading);
}

function markProcessGridTouched() {
  if (applyingProcessPrices) return;
  processGridTouched = true;
  cancelPendingProcessApply();
}

function resetProcessGridTouched() {
  processGridTouched = false;
  cancelPendingProcessApply();
}

function setupProcessGridWatch() {
  const form = document.getElementById("costEntryForm");
  if (!form || form.dataset.processTouchBound === "1") return;
  form.dataset.processTouchBound = "1";
  const changeSel =
    ".process-pick, .process-price, .process-supplier, .process-supplier-search, .process-supplier-add-input";
  form.addEventListener("change", (e) => {
    if (e.target.matches(changeSel)) markProcessGridTouched();
  });
  form.addEventListener("input", (e) => {
    if (e.target.matches(".process-price, .process-supplier-search, .process-supplier-add-input")) {
      markProcessGridTouched();
    }
  });
  form.addEventListener("click", (e) => {
    if (e.target.closest(".process-supplier-tag-remove")) markProcessGridTouched();
  });
  form.addEventListener(
    "mousedown",
    (e) => {
      if (
        e.target.closest(
          ".process-pick, .process-pick-item, .process-detail-row, .process-suppliers-panel, .process-price, .process-supplier-add-input"
        )
      ) {
        markProcessGridTouched();
      }
    },
    true
  );
}

function initCostEntryCombos() {
  const form = document.getElementById("costEntryForm");
  const IBL = window.InventoryBomLookup;
  if (!form || !IBL) return;
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
    hintEl: document.getElementById("partLookupHint"),
    onSelect: () => {
      lastLookupPart = "";
      lookupPartNo();
    },
    ...opts,
  });
}

function initMaterialCombo(materials) {
  const form = document.getElementById("costEntryForm");
  if (!form?.material || !window.InventoryBomLookup) return;
  window.InventoryBomLookup.bindMaterialList(form.material, materials);
}

function initBatchCustomerCombo() {
  const el = document.getElementById("bomImportBatchCustomer");
  const IBL = window.InventoryBomLookup;
  if (!el || !IBL) return;
  IBL.bindCustomer({
    customerInput: el,
    fetchSuggestions: IBL.fetchMasterCustomerSuggestions,
    ...IBL.STANDARD_COMBO_OPTS,
  });
}

function setPartLookupHint(text, kind) {
  const el = document.getElementById("partLookupHint");
  if (!el) return;
  if (!text) {
    el.hidden = true;
    el.textContent = "";
    el.className = "field-hint";
    return;
  }
  el.hidden = false;
  el.textContent = text;
  el.className = "field-hint" + (kind ? ` ${kind}` : "");
}

function markAutoFilledWeight(filled) {
  const input = document.querySelector('input[name="unit_weight_g"]');
  if (!input) return;
  input.classList.toggle("is-auto-filled", Boolean(filled));
}

function applyProcessPrices(processPrices, processSelections) {
  const byCode = buildProcessPricesByCode(processPrices, processSelections);
  if (!Object.keys(byCode).length) return;

  applyingProcessPrices = true;
  try {
    document.querySelectorAll("#processGrid .process-pick").forEach((cb) => {
      cb.checked = false;
    });

    const detailState = {};
    Object.entries(byCode).forEach(([code, entry]) => {
      const cb = document.querySelector(`#processGrid .process-pick[data-process-code="${code}"]`);
      if (cb) cb.checked = true;
      detailState[code] = {
        price: entry.price,
        suppliers: entry.suppliers || (entry.supplier ? [entry.supplier] : []),
      };
    });

    CostCommon.refreshProcessDetailPanel(
      "processDetailPanel",
      "#processGrid",
      entryProcessOptions,
      detailState
    );

    selectedCount = document.querySelectorAll("#processGrid .process-pick:checked").length;
    updateProcessSelectionSummary();
    const order =
      Array.isArray(processSelections) && processSelections.length
        ? processSelections.map((s) => s.code)
        : null;
    if (order) CostCommon.setProcessOrder("processGrid", order);
    else CostCommon.refreshProcessOrder("processGrid");
    resetProcessGridTouched();
  } finally {
    applyingProcessPrices = false;
  }
}

function applySuggestedFill(suggested, opts) {
  const options = opts || {};
  const form = document.getElementById("costEntryForm");
  if (!form || !suggested) return;

  const map = {
    customer_name: suggested.customer_name,
    product_name: suggested.product_name,
    mold_no: suggested.mold_no,
    cavity: suggested.cavity,
    unit_weight_g: suggested.unit_weight_g,
    material: suggested.material,
    machine_tonnage: suggested.machine_tonnage,
    material_unit_price: suggested.material_unit_price,
  };
  Object.entries(map).forEach(([name, value]) => {
    if (value == null || value === "") return;
    if (form[name]) form[name].value = value;
  });

  if (
    !options.skipProcesses &&
    hasProcessLookupData(suggested.process_prices, suggested.process_selections)
  ) {
    if (options.deferProcesses) {
      scheduleProcessApply(
        suggested.process_prices,
        suggested.process_selections,
        options.checkedAtStart || []
      );
    } else {
      applyProcessPrices(suggested.process_prices, suggested.process_selections);
    }
  }
  markAutoFilledWeight(Boolean(suggested.unit_weight_g && parseFloat(suggested.unit_weight_g) > 0));
  return Boolean(options.skipProcesses);
}

async function lookupPartNo() {
  const form = document.getElementById("costEntryForm");
  const partNo = form.product_part_no.value.trim();
  if (partNo.length < 2) {
    setPartLookupHint("");
    return;
  }
  if (partNo === lastLookupPart) return;

  const checkedAtStart = getCheckedProcessCodes();
  const preserveProcesses = shouldSkipProcessApply(checkedAtStart);
  const seq = ++lookupSeq;
  setProcessGridLoading(true);
  setPartLookupHint("正在载入 BOM，请稍候再勾选工序…", "warn");

  try {
    const res = await fetch(`/api/cost/lookup?${new URLSearchParams({ product_part_no: partNo })}`);
    const data = await res.json();
    if (seq !== lookupSeq) return;

    if (!res.ok) {
      lastLookupPart = "";
      setPartLookupHint(data.error || "料号查询失败", "error");
      return;
    }

    lastLookupPart = partNo;

    if (!data.found) {
      markAutoFilledWeight(false);
      setPartLookupHint("BOM 中未找到该料号，请填写完整信息后保存", "warn");
      return;
    }

    const skippedProcesses = applySuggestedFill(data.suggested || {}, {
      skipProcesses: preserveProcesses,
      deferProcesses: !preserveProcesses,
      checkedAtStart,
    });

    const hints = [];
    if (data.from_bom) hints.push("已载入 BOM 主数据");
    if (data.from_cost_record) hints.push("已载入历史记录");
    if (skippedProcesses) hints.push("工序区保留您的手工勾选");
    else if (!preserveProcesses && hasProcessLookupData(
      data.suggested?.process_prices,
      data.suggested?.process_selections
    )) {
      hints.push(`${PROCESS_APPLY_DELAY_MS / 1000} 秒内点工序将保留手工勾选`);
    }
    if ((data.auto_filled || []).includes("unit_weight_g")) {
      hints.push(`产品单重 ${data.suggested.unit_weight_g}g`);
    } else {
      hints.push("产品单重需手动填写");
    }
    setPartLookupHint(hints.join(" · "), "ok");
  } catch (_err) {
    if (seq !== lookupSeq) return;
    lastLookupPart = "";
    setPartLookupHint("料号查询失败，请检查网络后重试", "error");
  } finally {
    if (seq === lookupSeq) setProcessGridLoading(false);
  }
}

function setupPartLookup() {
  const partInput = document.getElementById("productPartNoInput");
  const form = document.getElementById("costEntryForm");
  if (!partInput || !form) return;

  partInput.addEventListener("change", () => {
    const partNo = partInput.value.trim();
    const prev = lastLookupPart;
    lastLookupPart = "";
    if (prev && partNo !== prev) resetProcessGridTouched();
    lookupPartNo();
  });

  // 仅 change 触发 lookup；避免 blur+change 重复请求导致工序被刷掉

  form.customer_name.addEventListener("change", () => {
    const partNo = form.product_part_no.value.trim();
    const customer = form.customer_name.value.trim();
    if (!partNo || !customer) return;
    fetch(`/api/cost/lookup?${new URLSearchParams({ product_part_no: partNo })}`)
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          setPartLookupHint(data.error || "客户与料号不匹配", "error");
          return;
        }
        const bound = (data.suggested && data.suggested.customer_name) || data.customer_name || "";
        if (bound && bound !== customer) {
          setPartLookupHint(`料号已绑定客户「${bound}」，请核对客户名称`, "error");
        }
      })
      .catch(() => {});
  });
}

function updateProcessSelectionSummary() {
  const el = document.getElementById("processSelectionSummary");
  if (el) {
    el.textContent = selectedCount > 0 ? `已选 ${selectedCount} 道工序` : "请勾选本料号适用的工序";
  }
}

function renderProcessPicker(processOptions) {
  const grid = document.getElementById("processGrid");
  if (!grid) return;
  entryProcessOptions = processOptions || [];
  processLabelByName = {};
  entryProcessOptions.forEach((p) => {
    processLabelByName[p.name] = `${p.code} ${p.name}`;
  });

  grid.innerHTML = CostCommon.renderProcessPickOnlyGridHtml(entryProcessOptions);
  selectedCount = 0;
  updateProcessSelectionSummary();
  CostCommon.bindStagedProcessPicker(grid, "processDetailPanel", entryProcessOptions, () => {
    selectedCount = grid.querySelectorAll(".process-pick:checked").length;
    updateProcessSelectionSummary();
    CostCommon.refreshProcessOrder("processGrid");
  });
  CostCommon.bindProcessOrder(
    "processGrid",
    "processOrderList",
    "processOrderBlock",
    entryProcessOptions
  );
  setupProcessGridWatch();
}

function collectBasicForm(form) {
  return {
    customer_name: form.customer_name.value.trim(),
    product_name: form.product_name.value.trim(),
    mold_no: form.mold_no.value.trim(),
    product_part_no: form.product_part_no.value.trim(),
    cavity: form.cavity.value.trim(),
    unit_weight_g: form.unit_weight_g.value.trim(),
    material: form.material.value.trim(),
    machine_tonnage: form.machine_tonnage.value.trim(),
    material_unit_price: form.material_unit_price.value || "0",
  };
}

function collectSelectedProcesses() {
  return CostCommon.collectProcessEntries("#costEntryForm");
}

function validateSuppliers(msgEl) {
  const missing = CostCommon.validateProcessSuppliers("#costEntryForm");
  if (!missing.length) return true;
  if (msgEl) {
    msgEl.textContent = `外发工序请至少添加一个供应商：${missing.join("、")}`;
    msgEl.className = "msg error";
  }
  return false;
}

function buildQuotePayload(basic, processPricesByName) {
  return {
    material_code: basic.material,
    material_unit_price: basic.material_unit_price,
    material_weight: basic.unit_weight_g,
    process_prices: processPricesByName,
    quantity: "1",
    markup_rate: "0",
  };
}

function closePreviewModal() {
  const modal = document.getElementById("costPreviewModal");
  if (modal) modal.hidden = true;
}

function openPreviewModal() {
  const modal = document.getElementById("costPreviewModal");
  if (modal) modal.hidden = false;
}

async function previewQuote() {
  const form = document.getElementById("costEntryForm");
  const msg = document.getElementById("costMsg");
  const body = document.getElementById("previewBody");
  const { byCode, byName } = collectSelectedProcesses();
  if (!Object.keys(byCode).length) {
    msg.textContent = "请至少选择一道工序";
    msg.className = "msg error";
    return;
  }
  if (!validateSuppliers(msg)) return;
  const basic = collectBasicForm(form);
  const res = await fetch("/api/cost/quote", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildQuotePayload(basic, byName)),
  });
  const data = await res.json();
  if (!res.ok) {
    msg.textContent = data.error || "预览失败";
    msg.className = "msg error";
    return;
  }
  msg.textContent = "";
  msg.className = "msg";
  CostCommon.renderQuotePreview(body, data, processLabelByName);
  openPreviewModal();
}

async function submitRecord() {
  const form = document.getElementById("costEntryForm");
  const msg = document.getElementById("costMsg");
  const { byCode } = collectSelectedProcesses();
  if (!Object.keys(byCode).length) {
    msg.textContent = "请至少选择一道工序";
    msg.className = "msg error";
    return;
  }
  if (!validateSuppliers(msg)) return;
  const { order } = collectSelectedProcesses();
  const payload = {
    ...collectBasicForm(form),
    process_prices: byCode,
    process_order: order,
  };
  const res = await fetch("/api/cost/records", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    msg.textContent = data.error || "保存失败";
    msg.className = "msg error";
    return;
  }
  msg.textContent = "已保存，可在「BOM查询」中查看";
  msg.className = "msg ok";
  form.reset();
  lastLookupPart = "";
  resetProcessGridTouched();
  markAutoFilledWeight(false);
  setPartLookupHint("");
  document.querySelectorAll(".process-pick:checked").forEach((cb) => {
    cb.checked = false;
  });
  CostCommon.refreshProcessDetailPanel("processDetailPanel", "#processGrid", entryProcessOptions, {});
  selectedCount = 0;
  updateProcessSelectionSummary();
  CostCommon.clearProcessOrder("processGrid");
  closePreviewModal();
}

document.getElementById("previewBtn").addEventListener("click", (e) => {
  e.preventDefault();
  previewQuote();
});

document.getElementById("costEntryForm").addEventListener("submit", (e) => {
  e.preventDefault();
  submitRecord();
});

document.getElementById("costPreviewClose").addEventListener("click", closePreviewModal);
document.getElementById("costPreviewModal").addEventListener("click", (e) => {
  if (e.target.id === "costPreviewModal") closePreviewModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closePreviewModal();
});

CostCommon.loadOptions()
  .then(({ processOptions, materials }) => {
    initMaterialCombo(materials);
    return CostCommon.loadSuppliers()
      .catch(() => [])
      .then(() => processOptions);
  })
  .then((processOptions) => {
    renderProcessPicker(
      processOptions.length
        ? processOptions
        : CostCommon.getProcesses().map((name, i) => ({
            code: String(i + 1).padStart(2, "0"),
            name,
          }))
    );
    setupPartLookup();
    initCostEntryCombos();
    initBatchCustomerCombo();
    CostCommon.renderMissingSupplierAlert("bomMissingSupplierAlert");
  });

function switchBomMode(mode) {
  const isBatch = mode === "batch";
  const isManual = mode === "manual";
  const batchPanel = document.getElementById("bomBatchPanel");
  const manualPanel = document.getElementById("bomManualPanel");
  const modeHint = document.getElementById("bomModeHint");
  const batchBtn = document.getElementById("bomModeBatchBtn");
  const manualBtn = document.getElementById("bomModeManualBtn");
  if (batchPanel) batchPanel.classList.toggle("is-hidden", !isBatch);
  if (manualPanel) manualPanel.classList.toggle("is-hidden", !isManual);
  if (modeHint) modeHint.classList.toggle("is-hidden", isBatch || isManual);
  if (batchBtn) {
    batchBtn.classList.toggle("active", isBatch);
    batchBtn.setAttribute("aria-selected", isBatch ? "true" : "false");
  }
  if (manualBtn) {
    manualBtn.classList.toggle("active", isManual);
    manualBtn.setAttribute("aria-selected", isManual ? "true" : "false");
  }
}

document.getElementById("bomModeBatchBtn")?.addEventListener("click", () => switchBomMode("batch"));
document.getElementById("bomModeManualBtn")?.addEventListener("click", () => switchBomMode("manual"));
