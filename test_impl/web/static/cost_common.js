/** 成本分析公共：选项加载、金额格式化、报价预览、工序供应商 */
window.CostCommon = (function () {
  let processes = [];
  let processOptions = [];
  let materials = [];
  let supplierNames = [];

  const INHOUSE_PROCESS_CODE = "01";

  function money(v) {
    const n = parseFloat(v);
    if (Number.isNaN(n)) return "¥ 0.0000";
    return (
      "¥ " +
      n.toLocaleString("zh-CN", {
        minimumFractionDigits: 4,
        maximumFractionDigits: 4,
      })
    );
  }

  function formatDate(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return iso;
      return d.toLocaleString("zh-CN", { hour12: false });
    } catch (_e) {
      return iso;
    }
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function loadOptions() {
    const res = await fetch("/api/cost/options");
    const data = await res.json();
    processes = data.processes || [];
    processOptions = data.process_options || [];
    materials = data.materials || [];
    return { processes, processOptions, materials };
  }

  async function loadSuppliers() {
    const res = await fetch("/api/supplier-profiles");
    const data = await res.json();
    supplierNames = (data.rows || [])
      .map((row) => row.supplier)
      .filter(Boolean)
      .sort((a, b) => a.localeCompare(b, "zh-CN"));
    return supplierNames.slice();
  }

  function getSupplierNames() {
    return supplierNames.slice();
  }

  function isOutsourceProcess(code) {
    return String(code || "") !== INHOUSE_PROCESS_CODE;
  }

  function buildSupplierSelectHtml(code, selected, disabled) {
    if (!isOutsourceProcess(code)) {
      return '<span class="process-inhouse-tag">场内自制</span>';
    }
    const opts = ['<option value="">请选择供应商</option>']
      .concat(
        supplierNames.map((name) => {
          const sel = name === selected ? " selected" : "";
          return `<option value="${escapeHtml(name)}"${sel}>${escapeHtml(name)}</option>`;
        })
      )
      .join("");
    const dis = disabled ? " disabled" : "";
    return `<select class="process-supplier" data-process-code="${escapeHtml(code)}"${dis}>${opts}</select>`;
  }

  function bindProcessPickerGrid(grid) {
    if (!grid) return;
    grid.querySelectorAll(".process-pick").forEach((cb) => {
      cb.addEventListener("change", () => {
        const code = cb.dataset.processCode;
        const priceInput = grid.querySelector(`input.process-price[data-process-code="${code}"]`);
        const supplierInput = grid.querySelector(`select.process-supplier[data-process-code="${code}"]`);
        if (priceInput) {
          priceInput.disabled = !cb.checked;
          if (!cb.checked) {
            priceInput.value = "";
            priceInput.classList.remove("filled");
          }
        }
        if (supplierInput) {
          supplierInput.disabled = !cb.checked;
          if (!cb.checked) supplierInput.value = "";
        }
      });
    });
    grid.querySelectorAll(".process-price").forEach((inp) => {
      inp.addEventListener("input", () => {
        inp.classList.toggle("filled", inp.value !== "" && parseFloat(inp.value) > 0);
      });
    });
  }

  function collectProcessEntries(containerSelector) {
    const byCode = {};
    const byName = {};
    document.querySelectorAll(`${containerSelector} .process-pick:checked`).forEach((cb) => {
      const code = cb.dataset.processCode;
      const name = cb.dataset.process;
      const priceInput = document.querySelector(
        `${containerSelector} input.process-price[data-process-code="${code}"]`
      );
      const supplierInput = document.querySelector(
        `${containerSelector} select.process-supplier[data-process-code="${code}"]`
      );
      const price = priceInput && priceInput.value !== "" ? priceInput.value : "0";
      const supplier =
        isOutsourceProcess(code) && supplierInput ? supplierInput.value.trim() : "";
      byCode[code] = { price, supplier };
      byName[name] = price;
    });
    return { byCode, byName };
  }

  function validateProcessSuppliers(containerSelector) {
    const missing = [];
    document.querySelectorAll(`${containerSelector} .process-pick:checked`).forEach((cb) => {
      const code = cb.dataset.processCode;
      if (!isOutsourceProcess(code)) return;
      const supplierInput = document.querySelector(
        `${containerSelector} select.process-supplier[data-process-code="${code}"]`
      );
      if (!supplierInput || !supplierInput.value.trim()) {
        missing.push(cb.dataset.process);
      }
    });
    return missing;
  }

  function renderProcessGridHtml(processOptions, selectedByCode) {
    return processOptions
      .map((p) => {
        const entry = selectedByCode && selectedByCode[p.code];
        const checked = entry != null;
        const price =
          entry && typeof entry === "object" && entry.price != null
            ? entry.price
            : entry != null
              ? entry
              : "";
        const supplier =
          entry && typeof entry === "object" && entry.supplier != null ? entry.supplier : "";
        const priceVal = price !== "0" && price !== 0 ? price : "";
        return `
    <label class="process-pick-item">
      <span class="process-pick-head">
        <input type="checkbox" class="process-pick" data-process-code="${p.code}" data-process="${p.name}"${checked ? " checked" : ""} />
        <span class="process-code">${p.code}</span>
        <span class="process-name" title="${escapeHtml(p.name)}">${escapeHtml(p.name)}</span>
      </span>
      <input class="process-price" data-process-code="${p.code}" data-process-price="${escapeHtml(p.name)}" type="number" step="0.0001" min="0" placeholder="单价（可选）"${checked ? "" : " disabled"} value="${priceVal}" />
      ${buildSupplierSelectHtml(p.code, supplier, !checked)}
    </label>`;
      })
      .join("");
  }

  function getProcessOptions() {
    return processOptions.slice();
  }

  function getProcesses() {
    return processes.slice();
  }

  function getMaterials() {
    return materials.slice();
  }

  function renderQuotePreview(container, q, labelMap) {
    if (!container || !q) return;
    const chips = Object.entries(q.process_prices || {})
      .map(([k, v]) => {
        const label = labelMap && labelMap[k] ? labelMap[k] : k;
        return `<span class="chip">${label} <b>${money(v)}</b></span>`;
      })
      .join("");

    container.innerHTML = `
      <div class="result-grid">
        <div class="result-row">
          <span class="r-label">原材（${q.material_code}）成本　单价 ${money(q.material_unit_price)} × 重量 ${q.material_weight}</span>
          <span class="r-value">${money(q.material_cost)}</span>
        </div>
        <div class="result-row">
          <span class="r-label">工艺合计</span>
          <span class="r-value">${money(q.process_total)}</span>
        </div>
        <div class="result-row grand">
          <span class="r-label">单件成本合计</span>
          <span class="r-value">${money(q.unit_cost || q.quote_price)}</span>
        </div>
      </div>
      ${
        chips
          ? `<div class="result-processes"><h5>已选工序</h5><div class="chip-row">${chips}</div></div>`
          : ""
      }`;
  }

  function selectionsToMap(selections, fallbackPrices) {
    const byCode = {};
    if (Array.isArray(selections) && selections.length) {
      selections.forEach((item) => {
        byCode[item.code] = {
          price: item.price,
          supplier: item.supplier || "",
        };
      });
      return byCode;
    }
    if (fallbackPrices && typeof fallbackPrices === "object") {
      Object.entries(fallbackPrices).forEach(([code, val]) => {
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
    return byCode;
  }

  return {
    INHOUSE_PROCESS_CODE,
    loadOptions,
    loadSuppliers,
    getSupplierNames,
    isOutsourceProcess,
    buildSupplierSelectHtml,
    bindProcessPickerGrid,
    collectProcessEntries,
    validateProcessSuppliers,
    renderProcessGridHtml,
    selectionsToMap,
    getProcesses,
    getProcessOptions,
    getMaterials,
    money,
    formatDate,
    renderQuotePreview,
  };
})();
