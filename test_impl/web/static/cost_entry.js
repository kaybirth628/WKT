let selectedCount = 0;
let processLabelByName = {};
let partSuggestTimer = null;
let lastLookupPart = "";

function debouncePartSuggest(fn, ms) {
  return function (...args) {
    clearTimeout(partSuggestTimer);
    partSuggestTimer = setTimeout(() => fn.apply(this, args), ms);
  };
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

function fillCustomerOptions(customers) {
  const list = document.getElementById("customerOptions");
  if (!list) return;
  const names = new Set((customers || []).map((c) => c.customer_name || c).filter(Boolean));
  list.innerHTML = Array.from(names)
    .sort((a, b) => a.localeCompare(b, "zh-CN"))
    .map((name) => `<option value="${name}"></option>`)
    .join("");
}

async function fetchPartSuggestions(q) {
  const query = (q || "").trim();
  if (query.length < 1) {
    document.getElementById("partNoOptions").innerHTML = "";
    return;
  }
  const res = await fetch(`/api/cost/part-numbers?q=${encodeURIComponent(query)}&limit=20`);
  const data = await res.json();
  const list = document.getElementById("partNoOptions");
  if (!list) return;
  list.innerHTML = (data.items || [])
    .map((item) => {
      const labelParts = [item.customer_name, item.product_name];
      if (item.unit_weight_g && parseFloat(item.unit_weight_g) > 0) {
        labelParts.push(`${item.unit_weight_g}g`);
      }
      const label = labelParts.filter(Boolean).join(" · ");
      return `<option value="${item.product_part_no}"${label ? ` label="${label}"` : ""}></option>`;
    })
    .join("");
}

function markAutoFilledWeight(filled) {
  const input = document.querySelector('input[name="unit_weight_g"]');
  if (!input) return;
  input.classList.toggle("is-auto-filled", Boolean(filled));
}

function applyProcessPrices(processPrices, processSelections) {
  document.querySelectorAll(".process-pick:checked").forEach((cb) => {
    cb.checked = false;
    cb.dispatchEvent(new Event("change"));
  });

  const byCode = {};
  if (Array.isArray(processSelections) && processSelections.length) {
    processSelections.forEach((item) => {
      byCode[item.code] = {
        price: item.price,
        supplier: item.supplier || "",
      };
    });
  } else if (processPrices && Object.keys(processPrices).length) {
    Object.entries(processPrices).forEach(([code, val]) => {
      if (val && typeof val === "object") {
        byCode[code] = {
          price: val.price != null ? val.price : "0",
          supplier: val.supplier || "",
        };
      } else {
        byCode[code] = { price: val, supplier: "" };
      }
    });
  }
  if (!Object.keys(byCode).length) return;

  Object.entries(byCode).forEach(([code, entry]) => {
    const cb = document.querySelector(`.process-pick[data-process-code="${code}"]`);
    if (!cb) return;
    cb.checked = true;
    cb.dispatchEvent(new Event("change"));
    const inp = document.querySelector(`input.process-price[data-process-code="${code}"]`);
    if (inp && entry.price !== "" && entry.price != null) {
      inp.value = entry.price !== "0" ? entry.price : "";
      inp.classList.toggle("filled", parseFloat(entry.price) > 0);
    }
    const sel = document.querySelector(`select.process-supplier[data-process-code="${code}"]`);
    if (sel && entry.supplier) sel.value = entry.supplier;
  });
  selectedCount = document.querySelectorAll("#processGrid .process-pick:checked").length;
  updateProcessSelectionSummary();
}

function applySuggestedFill(suggested) {
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

  if (suggested.process_prices || suggested.process_selections) {
    applyProcessPrices(suggested.process_prices, suggested.process_selections);
  }
  markAutoFilledWeight(Boolean(suggested.unit_weight_g && parseFloat(suggested.unit_weight_g) > 0));
}

async function lookupPartNo() {
  const form = document.getElementById("costEntryForm");
  const partNo = form.product_part_no.value.trim();
  if (partNo.length < 2) {
    setPartLookupHint("");
    return;
  }
  if (partNo === lastLookupPart) return;

  const res = await fetch(`/api/cost/lookup?${new URLSearchParams({ product_part_no: partNo })}`);
  const data = await res.json();
  if (!res.ok) {
    lastLookupPart = "";
    setPartLookupHint(data.error || "料号查询失败", "error");
    return;
  }

  lastLookupPart = partNo;

  if (!data.found) {
    markAutoFilledWeight(false);
    setPartLookupHint("订单中未找到该料号，请手动填写", "warn");
    return;
  }

  applySuggestedFill(data.suggested || {});

  const hints = [];
  if (data.from_order_line) hints.push("已关联订单并绑定客户");
  if (data.from_cost_record) hints.push("已载入历史成本");
  if ((data.auto_filled || []).includes("unit_weight_g")) {
    hints.push(`产品单重 ${data.suggested.unit_weight_g}g`);
  } else {
    hints.push("产品单重需手动填写");
  }
  setPartLookupHint(hints.join(" · "), "ok");
}

function setupPartLookup() {
  const partInput = document.getElementById("productPartNoInput");
  const form = document.getElementById("costEntryForm");
  if (!partInput || !form) return;

  partInput.addEventListener(
    "input",
    debouncePartSuggest((e) => {
      lastLookupPart = "";
      fetchPartSuggestions(e.target.value);
    }, 250)
  );

  partInput.addEventListener("change", () => {
    lastLookupPart = "";
    lookupPartNo();
  });

  partInput.addEventListener("blur", () => {
    lookupPartNo();
  });

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
  processLabelByName = {};
  processOptions.forEach((p) => {
    processLabelByName[p.name] = `${p.code} ${p.name}`;
  });

  grid.innerHTML = CostCommon.renderProcessGridHtml(processOptions);
  selectedCount = 0;
  updateProcessSelectionSummary();
  CostCommon.bindProcessPickerGrid(grid);
  grid.querySelectorAll(".process-pick").forEach((cb) => {
    cb.addEventListener("change", () => {
      selectedCount = grid.querySelectorAll(".process-pick:checked").length;
      updateProcessSelectionSummary();
    });
  });
}

function fillMaterialDatalist(materials) {
  const list = document.getElementById("materialOptions");
  if (!list) return;
  list.innerHTML = materials.map((m) => `<option value="${m}"></option>`).join("");
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
  return CostCommon.collectProcessEntries("#processGrid");
}

function validateSuppliers(msgEl) {
  const missing = CostCommon.validateProcessSuppliers("#processGrid");
  if (!missing.length) return true;
  if (msgEl) {
    msgEl.textContent = `外发工序请选择供应商：${missing.join("、")}`;
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
  const payload = {
    ...collectBasicForm(form),
    process_prices: byCode,
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
  msg.textContent = "已保存，可在「成本查询」中查看";
  msg.className = "msg ok";
  form.reset();
  lastLookupPart = "";
  markAutoFilledWeight(false);
  setPartLookupHint("");
  document.querySelectorAll(".process-pick:checked").forEach((cb) => {
    cb.checked = false;
    cb.dispatchEvent(new Event("change"));
  });
  selectedCount = 0;
  updateProcessSelectionSummary();
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
    fillMaterialDatalist(materials);
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
    fetch("/api/master")
      .then((res) => res.json())
      .then((data) => fillCustomerOptions((data.customers || []).map((name) => ({ customer_name: name }))))
      .catch(() => {});
  });
