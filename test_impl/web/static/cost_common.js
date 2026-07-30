/** 成本分析公共：选项加载、金额格式化、报价预览、工序供应商 */
window.CostCommon = (function () {
  let processes = [];
  let processOptions = [];
  let materials = [];
  let supplierNames = [];

  const INHOUSE_PROCESS_CODE = "01";
  const INHOUSE_SUPPLIER_LABEL = "场内自制";

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

  async function renderMissingSupplierAlert(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;
    try {
      const res = await fetch("/api/cost/missing-suppliers");
      if (!res.ok) {
        el.classList.add("is-hidden");
        el.innerHTML = "";
        return;
      }
      const data = await res.json();
      const items = data.items || [];
      if (!items.length) {
        el.classList.add("is-hidden");
        el.innerHTML = "";
        return;
      }
      const chips = items
        .map((item) => {
          const count =
            item.occurrence_count > 1
              ? ` <span class="bom-missing-supplier-count">×${item.occurrence_count}</span>`
              : "";
          return `<span class="bom-missing-supplier-chip">${escapeHtml(item.supplier_name)}${count}</span>`;
        })
        .join("");
      el.classList.remove("is-hidden");
      el.innerHTML = `
        <div class="bom-missing-supplier-alert-inner">
          <div class="bom-missing-supplier-head">
            <strong>供应商档案缺失</strong>
            <span class="bom-missing-supplier-meta">${data.total_distinct} 家 · ${data.total_occurrences} 处引用</span>
            <a href="/#supplier" class="bom-missing-supplier-link">去维护 →</a>
          </div>
          <div class="bom-missing-supplier-chips">${chips}</div>
        </div>`;
    } catch (_e) {
      el.classList.add("is-hidden");
      el.innerHTML = "";
    }
  }

  function getSupplierNames() {
    return supplierNames.slice();
  }

  function supplierChoices() {
    const names = supplierNames.filter((n) => n !== INHOUSE_SUPPLIER_LABEL);
    return [INHOUSE_SUPPLIER_LABEL].concat(names);
  }

  function isOutsourceProcess(code) {
    return String(code || "") !== INHOUSE_PROCESS_CODE;
  }

  function buildSupplierSelectHtml(code, selected, disabled) {
    if (!isOutsourceProcess(code)) {
      return '<span class="process-inhouse-tag">场内自制</span>';
    }
    const val = selected || "";
    const dis = disabled ? " disabled" : "";
    const display = val || "";
    const placeholder = val ? "" : "搜索或选择供应商";
    return `
      <div class="process-supplier-combo"${disabled ? " data-disabled=1" : ""}>
        <input type="hidden" class="process-supplier" data-process-code="${escapeHtml(code)}" value="${escapeHtml(val)}"${dis} />
        <input type="text" class="process-supplier-search" data-process-code="${escapeHtml(code)}"
          value="${escapeHtml(display)}" placeholder="${placeholder}" autocomplete="off"${dis} />
        <ul class="process-supplier-list" hidden></ul>
      </div>`;
  }

  function normalizeSupplierList(entry) {
    if (!entry) return [];
    if (Array.isArray(entry.suppliers) && entry.suppliers.length) {
      return entry.suppliers.map((s) => String(s || "").trim()).filter(Boolean);
    }
    const one = String(entry.supplier || "").trim();
    return one ? [one] : [];
  }

  function supplierTagHtml(name, disabled) {
    return `
      <li class="process-supplier-tag" data-value="${escapeHtml(name)}">
        <span class="process-supplier-tag-label">${escapeHtml(name)}</span>
        <button type="button" class="process-supplier-tag-remove" aria-label="移除"${disabled ? " disabled" : ""}>×</button>
      </li>`;
  }

  function buildProcessSuppliersHtml(code, suppliers, disabled) {
    if (!isOutsourceProcess(code)) {
      return '<span class="process-inhouse-tag">场内自制</span>';
    }
    const list = Array.isArray(suppliers) ? suppliers.filter(Boolean) : [];
    const tags = list.map((name) => supplierTagHtml(name, disabled)).join("");
    const dis = disabled ? " disabled" : "";
    return `
      <div class="process-suppliers-panel" data-process-code="${escapeHtml(code)}"${disabled ? " data-disabled=1" : ""}>
        <ul class="process-supplier-tags">${tags}</ul>
        <div class="process-supplier-add-wrap">
          <input type="text" class="process-supplier-add-input" data-process-code="${escapeHtml(code)}"
            placeholder="搜索或选择供应商" autocomplete="off" spellcheck="false"${dis} />
        </div>
      </div>`;
  }

  function getProcessSuppliersFromPanel(panel) {
    if (!panel) return [];
    const names = [];
    panel.querySelectorAll(".process-supplier-tag").forEach((tag) => {
      const value = (tag.dataset.value || "").trim();
      if (value && !names.includes(value)) names.push(value);
    });
    return names;
  }

  function setProcessSuppliersPanel(panel, suppliers) {
    if (!panel) return;
    const tags = panel.querySelector(".process-supplier-tags");
    if (!tags) return;
    const disabled = panel.dataset.disabled === "1";
    tags.innerHTML = (suppliers || []).filter(Boolean).map((name) => supplierTagHtml(name, disabled)).join("");
  }

  function addSupplierToPanel(panel, name) {
    const value = String(name || "").trim();
    if (!panel || !value) return false;
    const current = getProcessSuppliersFromPanel(panel);
    if (current.some((s) => s.toLowerCase() === value.toLowerCase())) return false;
    setProcessSuppliersPanel(panel, current.concat(value));
    return true;
  }

  function clearProcessSuppliersPanel(panel) {
    setProcessSuppliersPanel(panel, []);
    const input = panel?.querySelector(".process-supplier-add-input");
    if (input) input.value = "";
  }

  function setProcessSuppliersDisabled(panel, disabled) {
    if (!panel) return;
    panel.dataset.disabled = disabled ? "1" : "0";
    const input = panel.querySelector(".process-supplier-add-input");
    if (input) input.disabled = disabled;
    panel.querySelectorAll(".process-supplier-tag-remove").forEach((btn) => {
      btn.disabled = disabled;
    });
  }

  function bindProcessSupplierAddCombos(root) {
    if (!window.InventoryBomLookup) return;
    const scope = root || document;
    const comboOpts = window.InventoryBomLookup.STANDARD_COMBO_OPTS || {
      openOnFocus: true,
      minChars: 0,
      showToggle: true,
    };
    scope.querySelectorAll(".process-supplier-add-input").forEach((input) => {
      if (input.dataset.bound === "1") return;
      input.dataset.bound = "1";
      const panel = input.closest(".process-suppliers-panel");
      window.InventoryBomLookup.bindCustomer({
        customerInput: input,
        fetchSuggestions: (q) => {
          const exclude = getProcessSuppliersFromPanel(panel);
          const excludeSet = new Set(exclude.map((n) => n.toLowerCase()));
          const query = (q || "").trim().toLowerCase();
          return Promise.resolve(
            supplierChoices()
              .filter((n) => !excludeSet.has(n.toLowerCase()))
              .filter((n) => !query || n.toLowerCase().includes(query))
              .slice(0, 50)
          );
        },
        openOnFocus: comboOpts.openOnFocus,
        minChars: comboOpts.minChars,
        showToggle: comboOpts.showToggle,
        onSelect: (name) => {
          if (panel && addSupplierToPanel(panel, name)) {
            input.value = "";
          }
        },
      });
    });
  }

  function filterSupplierChoices(query, excludeNames) {
    const q = String(query || "").trim().toLowerCase();
    const exclude = new Set((excludeNames || []).map((n) => String(n || "").trim().toLowerCase()));
    const all = supplierChoices().filter((name) => !exclude.has(name.toLowerCase()));
    if (!q) return all;
    return all.filter((name) => name.toLowerCase().includes(q));
  }

  function renderSupplierList(combo, query, excludeNames) {
    const list = combo.querySelector(".process-supplier-list");
    if (!list) return;
    const hidden = combo.querySelector(".process-supplier, .process-supplier-add-hidden");
    const current = hidden ? hidden.value : "";
    const items = filterSupplierChoices(query, excludeNames);
    if (!items.length) {
      list.innerHTML = '<li class="process-supplier-empty">无匹配供应商</li>';
      list.hidden = false;
      return;
    }
    list.innerHTML = items
      .map((name) => {
        const cls =
          "process-supplier-option" +
          (name === INHOUSE_SUPPLIER_LABEL ? " is-inhouse" : "") +
          (name === current ? " is-selected" : "");
        return `<li class="${cls}" data-value="${escapeHtml(name)}">${escapeHtml(name)}</li>`;
      })
      .join("");
    list.hidden = false;
  }

  function setSupplierValue(combo, value) {
    const hidden = combo.querySelector(".process-supplier");
    const search = combo.querySelector(".process-supplier-search");
    const list = combo.querySelector(".process-supplier-list");
    if (hidden) hidden.value = value || "";
    if (search) {
      search.value = value || "";
      search.placeholder = value ? "" : "搜索或选择供应商";
    }
    if (list) list.hidden = true;
  }

  function bindSupplierCombos(root) {
    const scope = root || document;
    scope.querySelectorAll(".process-supplier-combo").forEach((combo) => {
      if (combo.dataset.bound === "1") return;
      combo.dataset.bound = "1";
      const search = combo.querySelector(".process-supplier-search");
      const list = combo.querySelector(".process-supplier-list");
      if (!search || !list) return;
      if (combo.classList.contains("is-add-supplier")) return;

      function excludedNames() {
        return [];
      }

      search.addEventListener("focus", () => {
        if (search.disabled) return;
        renderSupplierList(combo, "", excludedNames());
      });
      search.addEventListener("click", (ev) => {
        ev.stopPropagation();
        if (search.disabled) return;
        renderSupplierList(combo, search.value, excludedNames());
      });
      search.addEventListener("mousedown", (ev) => ev.stopPropagation());
      search.addEventListener("input", () => {
        if (search.disabled) return;
        const hidden = combo.querySelector(".process-supplier");
        if (hidden) hidden.value = "";
        renderSupplierList(combo, search.value, excludedNames());
      });
      search.addEventListener("keydown", (ev) => {
        if (ev.key === "Escape") {
          ev.stopPropagation();
          list.hidden = true;
          const hidden = combo.querySelector(".process-supplier");
          if (hidden && hidden.value) search.value = hidden.value;
        } else if (ev.key === "Enter") {
          const first = list.querySelector(".process-supplier-option");
          if (first && !list.hidden) {
            ev.preventDefault();
            ev.stopPropagation();
            setSupplierValue(combo, first.dataset.value || "");
          }
        }
      });
      list.addEventListener("mousedown", (ev) => {
        const opt = ev.target.closest(".process-supplier-option");
        if (!opt) return;
        ev.preventDefault();
        ev.stopPropagation();
        setSupplierValue(combo, opt.dataset.value || "");
      });
      combo.addEventListener("click", (ev) => ev.stopPropagation());
    });

    scope.querySelectorAll(".process-suppliers-panel").forEach((panel) => {
      if (panel.dataset.tagsBound === "1") return;
      panel.dataset.tagsBound = "1";
      panel.addEventListener("click", (ev) => {
        const btn = ev.target.closest(".process-supplier-tag-remove");
        if (!btn || btn.disabled) return;
        const tag = btn.closest(".process-supplier-tag");
        if (tag) tag.remove();
      });
    });

    if (!document.documentElement.dataset.supplierComboDocBound) {
      document.documentElement.dataset.supplierComboDocBound = "1";
      document.addEventListener("click", (ev) => {
        document.querySelectorAll(".process-supplier-combo").forEach((combo) => {
          if (!combo.contains(ev.target)) {
            const listEl = combo.querySelector(".process-supplier-list");
            const searchEl = combo.querySelector(".process-supplier-search");
            const hidden = combo.querySelector(".process-supplier");
            if (listEl) listEl.hidden = true;
            if (searchEl && hidden && hidden.value) searchEl.value = hidden.value;
            else if (searchEl && hidden && !hidden.value) searchEl.value = "";
          }
        });
      });
    }
  }

  function bindProcessPickerGrid(grid, onSelectionChange) {
    if (!grid) return;
    bindSupplierCombos(grid);
    bindProcessSupplierAddCombos(grid);
    if (window.HoverTip) {
      grid.querySelectorAll(".process-name").forEach((el) => window.HoverTip.bind(el));
    }
    grid.querySelectorAll(".process-pick").forEach((cb) => {
      cb.addEventListener("change", () => {
        const code = cb.dataset.processCode;
        const priceInput = grid.querySelector(`input.process-price[data-process-code="${code}"]`);
        const panel = grid.querySelector(`.process-suppliers-panel[data-process-code="${code}"]`);
        const combo = grid.querySelector(
          `.process-supplier-combo:not(.is-add-supplier):has(.process-supplier[data-process-code="${code}"])`
        );
        const supplierInput = grid.querySelector(
          `input.process-supplier[data-process-code="${code}"]`
        );
        const searchInput = panel
          ? panel.querySelector(".process-supplier-search")
          : grid.querySelector(`input.process-supplier-search[data-process-code="${code}"]`);
        if (priceInput) {
          priceInput.disabled = !cb.checked;
          if (!cb.checked) {
            priceInput.value = "";
            priceInput.classList.remove("filled");
          }
        }
        if (panel) {
          setProcessSuppliersDisabled(panel, !cb.checked);
          if (!cb.checked) clearProcessSuppliersPanel(panel);
        } else if (supplierInput) {
          supplierInput.disabled = !cb.checked;
          if (!cb.checked) {
            if (combo) setSupplierValue(combo, "");
            else supplierInput.value = "";
          }
        }
        if (searchInput && !panel) searchInput.disabled = !cb.checked;
        if (typeof onSelectionChange === "function") onSelectionChange();
      });
    });
    grid.querySelectorAll(".process-price").forEach((inp) => {
      inp.addEventListener("input", () => {
        inp.classList.toggle("filled", inp.value !== "" && parseFloat(inp.value) > 0);
      });
    });
  }

  const processOrderState = {};

  function gridDomId(gridId) {
    return String(gridId || "").replace(/^#/, "");
  }

  function getSelectedProcessCodes(containerSelector) {
    const codes = [];
    document.querySelectorAll(`${containerSelector} .process-pick:checked`).forEach((cb) => {
      codes.push(cb.dataset.processCode);
    });
    return codes;
  }

  function bindProcessOrder(gridId, listId, blockId, processOptions) {
    const key = gridDomId(gridId);
    const optionsByCode = {};
    (processOptions || []).forEach((p) => {
      optionsByCode[p.code] = p;
    });
    processOrderState[key] = {
      listId,
      blockId,
      optionsByCode,
      customOrder: null,
      gridSelector: `#${key}`,
    };
    refreshProcessOrder(key);
  }

  function setProcessOrder(gridId, codes) {
    const key = gridDomId(gridId);
    const state = processOrderState[key];
    if (!state) return;
    state.customOrder = Array.isArray(codes) ? codes.slice() : null;
    refreshProcessOrder(key);
  }

  function clearProcessOrder(gridId) {
    const key = gridDomId(gridId);
    const state = processOrderState[key];
    if (!state) return;
    state.customOrder = null;
    refreshProcessOrder(key);
  }

  function getProcessOrder(gridId) {
    const key = gridDomId(gridId);
    const state = processOrderState[key];
    if (!state || !state.customOrder) return null;
    return state.customOrder.slice();
  }

  function moveProcessOrder(key, code, delta) {
    const state = processOrderState[key];
    if (!state || !state.customOrder) return;
    const idx = state.customOrder.indexOf(code);
    if (idx < 0) return;
    const next = idx + delta;
    if (next < 0 || next >= state.customOrder.length) return;
    const arr = state.customOrder.slice();
    [arr[idx], arr[next]] = [arr[next], arr[idx]];
    state.customOrder = arr;
    refreshProcessOrder(key);
  }

  function refreshProcessOrder(key) {
    const state = processOrderState[key];
    if (!state) return;
    const block = document.getElementById(state.blockId);
    const list = document.getElementById(state.listId);
    const selected = getSelectedProcessCodes(state.gridSelector);

    if (!selected.length) {
      if (block) block.hidden = true;
      if (list) list.innerHTML = "";
      state.customOrder = null;
      return;
    }
    if (block) block.hidden = false;

    const ordered = [];
    if (state.customOrder) {
      state.customOrder.forEach((code) => {
        if (selected.includes(code) && !ordered.includes(code)) ordered.push(code);
      });
    }
    selected.forEach((code) => {
      if (!ordered.includes(code)) ordered.push(code);
    });
    state.customOrder = ordered;

    if (!list) return;
    list.innerHTML = ordered
      .map((code, idx) => {
        const opt = state.optionsByCode[code] || { code, name: code };
        return `
      <li class="process-order-item" data-process-code="${escapeHtml(code)}">
        <span class="process-order-seq">${idx + 1}</span>
        <span class="process-order-code">${escapeHtml(code)}</span>
        <span class="process-order-name">${escapeHtml(opt.name)}</span>
        <span class="process-order-actions">
          <button type="button" class="btn-icon process-order-up" aria-label="上移"${idx === 0 ? " disabled" : ""}>↑</button>
          <button type="button" class="btn-icon process-order-down" aria-label="下移"${idx === ordered.length - 1 ? " disabled" : ""}>↓</button>
        </span>
      </li>`;
      })
      .join("");

    list.querySelectorAll(".process-order-up").forEach((btn) => {
      btn.addEventListener("click", () => {
        moveProcessOrder(key, btn.closest(".process-order-item").dataset.processCode, -1);
      });
    });
    list.querySelectorAll(".process-order-down").forEach((btn) => {
      btn.addEventListener("click", () => {
        moveProcessOrder(key, btn.closest(".process-order-item").dataset.processCode, 1);
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
      const panel = document.querySelector(
        `${containerSelector} .process-suppliers-panel[data-process-code="${code}"]`
      );
      const price = priceInput && priceInput.value !== "" ? priceInput.value : "0";
      let suppliers = [];
      if (panel) {
        suppliers = getProcessSuppliersFromPanel(panel);
      } else {
        const supplierInput = document.querySelector(
          `${containerSelector} input.process-supplier[data-process-code="${code}"], ${containerSelector} select.process-supplier[data-process-code="${code}"]`
        );
        const one =
          isOutsourceProcess(code) && supplierInput ? supplierInput.value.trim() : "";
        suppliers = one ? [one] : [];
      }
      const supplier = suppliers[0] || "";
      byCode[code] = { price, supplier, suppliers };
      byName[name] = price;
    });
    const gridId = containerSelector.replace(/^#/, "");
    const order = getProcessOrder(gridId);
    const fallbackOrder = Object.keys(byCode).sort();
    return { byCode, byName, order: order && order.length ? order : fallbackOrder };
  }

  function validateProcessSuppliers(containerSelector) {
    const missing = [];
    document.querySelectorAll(`${containerSelector} .process-pick:checked`).forEach((cb) => {
      const code = cb.dataset.processCode;
      if (!isOutsourceProcess(code)) return;
      const panel = document.querySelector(
        `${containerSelector} .process-suppliers-panel[data-process-code="${code}"]`
      );
      let suppliers = panel ? getProcessSuppliersFromPanel(panel) : [];
      if (!suppliers.length) {
        const supplierInput = document.querySelector(
          `${containerSelector} input.process-supplier[data-process-code="${code}"], ${containerSelector} select.process-supplier[data-process-code="${code}"]`
        );
        if (supplierInput && supplierInput.value.trim()) suppliers = [supplierInput.value.trim()];
      }
      if (!suppliers.length) {
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
        const suppliers = normalizeSupplierList(entry);
        const priceVal = price !== "0" && price !== 0 ? price : "";
        return `
    <label class="process-pick-item">
      <span class="process-pick-head">
        <input type="checkbox" class="process-pick" data-process-code="${p.code}" data-process="${p.name}"${checked ? " checked" : ""} />
        <span class="process-code">${p.code}</span>
        <span class="process-name" data-hover-text="${escapeHtml(p.name)}">${escapeHtml(p.name)}</span>
      </span>
      <input class="process-price" data-process-code="${p.code}" data-process-price="${escapeHtml(p.name)}" type="number" step="0.0001" min="0" placeholder="单价（可选）"${checked ? "" : " disabled"} value="${priceVal}" />
      ${buildProcessSuppliersHtml(p.code, suppliers, !checked)}
    </label>`;
      })
      .join("");
  }

  /** BOM 录入：工序区仅勾选，单价/供应商在下方明细区填写 */
  function renderProcessPickOnlyGridHtml(processOptions, selectedByCode) {
    return processOptions
      .map((p) => {
        const entry = selectedByCode && selectedByCode[p.code];
        const checked = entry != null;
        return `
    <label class="process-pick-item process-pick-item--pick-only">
      <span class="process-pick-head">
        <input type="checkbox" class="process-pick" data-process-code="${p.code}" data-process="${escapeHtml(p.name)}"${checked ? " checked" : ""} />
        <span class="process-code">${p.code}</span>
        <span class="process-name" data-hover-text="${escapeHtml(p.name)}">${escapeHtml(p.name)}</span>
      </span>
    </label>`;
      })
      .join("");
  }

  function captureProcessDetailState(detailPanel) {
    const state = {};
    if (!detailPanel) return state;
    detailPanel.querySelectorAll(".process-detail-row").forEach((row) => {
      const code = row.dataset.processCode;
      const priceInp = row.querySelector("input.process-price");
      const panel = row.querySelector(".process-suppliers-panel");
      state[code] = {
        price: priceInp ? priceInp.value : "",
        suppliers: panel ? getProcessSuppliersFromPanel(panel) : [],
      };
    });
    return state;
  }

  function refreshProcessDetailPanel(
    detailPanelId,
    gridSelector,
    processOptions,
    externalState,
    detailBlockId
  ) {
    const detailPanel = document.getElementById(detailPanelId);
    const block = document.getElementById(detailBlockId || "processDetailBlock");
    if (!detailPanel) return;
    const mergedState = Object.assign(
      {},
      captureProcessDetailState(detailPanel),
      externalState || {}
    );
    const checked = [];
    document.querySelectorAll(`${gridSelector} .process-pick:checked`).forEach((cb) => {
      checked.push({ code: cb.dataset.processCode, name: cb.dataset.process });
    });
    if (!checked.length) {
      if (block) block.hidden = true;
      detailPanel.innerHTML = "";
      return;
    }
    if (block) block.hidden = false;

    detailPanel.innerHTML = checked
      .map(({ code, name }) => {
        const saved = mergedState[code] || {};
        const suppliers = saved.suppliers || [];
        const priceRaw = saved.price;
        const priceVal =
          priceRaw !== "" && priceRaw != null && priceRaw !== "0" && priceRaw !== 0
            ? priceRaw
            : "";
        const inhouse = !isOutsourceProcess(code);
        return `
    <div class="process-detail-row" data-process-code="${escapeHtml(code)}">
      <div class="process-detail-head">
        <span class="process-detail-code">${escapeHtml(code)}</span>
        <span class="process-detail-name">${escapeHtml(name)}</span>
      </div>
      <div class="process-detail-fields">
        <div class="field process-detail-supplier-field">
          <span class="field-label">${inhouse ? "类型" : "供应商"}</span>
          <div class="field-control">${inhouse ? '<span class="process-inhouse-tag">场内自制</span>' : buildProcessSuppliersHtml(code, suppliers, false)}</div>
        </div>
        <div class="field process-detail-price-field">
          <span class="field-label">单价（可选）</span>
          <input class="process-price" data-process-code="${escapeHtml(code)}" type="number" step="0.0001" min="0" placeholder="0" value="${escapeHtml(String(priceVal))}" />
        </div>
      </div>
    </div>`;
      })
      .join("");

    bindSupplierCombos(detailPanel);
    bindProcessSupplierAddCombos(detailPanel);
    detailPanel.querySelectorAll("input.process-price").forEach((inp) => {
      inp.addEventListener("input", () => {
        inp.classList.toggle("filled", inp.value !== "" && parseFloat(inp.value) > 0);
      });
    });
    if (window.HoverTip) {
      detailPanel.querySelectorAll(".process-detail-name").forEach((el) => window.HoverTip.bind(el));
    }
  }

  function bindStagedProcessPicker(grid, detailPanelId, processOptions, onSelectionChange, opts) {
    if (!grid) return;
    const options = opts && typeof opts === "object" ? opts : {};
    const blockId = options.blockId || "processDetailBlock";
    const gridSelector = grid.id ? `#${grid.id}` : "#processGrid";
    if (window.HoverTip) {
      grid.querySelectorAll(".process-name").forEach((el) => window.HoverTip.bind(el));
    }
    function onPickChange() {
      refreshProcessDetailPanel(detailPanelId, gridSelector, processOptions, null, blockId);
      if (typeof onSelectionChange === "function") onSelectionChange();
    }
    grid.querySelectorAll(".process-pick").forEach((cb) => {
      cb.addEventListener("change", onPickChange);
    });
    refreshProcessDetailPanel(
      detailPanelId,
      gridSelector,
      processOptions,
      options.initialState,
      blockId
    );
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
          suppliers: item.suppliers || (item.supplier ? [item.supplier] : []),
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
            suppliers: normalizeSupplierList(val),
          };
        } else {
          byCode[code] = { price: val, supplier: "" };
        }
      });
    }
    return byCode;
  }

  function supplierDisplayForSelection(item) {
    if (!item || !isOutsourceProcess(item.code) || item.inhouse) {
      return INHOUSE_SUPPLIER_LABEL;
    }
    const list = item.suppliers || (item.supplier ? [item.supplier] : []);
    const names = list.filter(Boolean);
    return names.length ? names.join("、") : "—";
  }

  function buildReadonlySuppliersHtml(suppliers) {
    const list = (suppliers || []).map((s) => String(s || "").trim()).filter(Boolean);
    if (!list.length) {
      return '<span class="process-inhouse-tag">—</span>';
    }
    if (list.length === 1) {
      return `<span class="cost-preview-supplier-tag">${escapeHtml(list[0])}</span>`;
    }
    return `<ul class="cost-preview-supplier-tags">${list
      .map((name) => `<li class="cost-preview-supplier-tag">${escapeHtml(name)}</li>`)
      .join("")}</ul>`;
  }

  function orderedProcessSelections(record) {
    const selections = record.process_selections || [];
    if (!selections.length) return [];
    const byCode = {};
    selections.forEach((item) => {
      byCode[item.code] = item;
    });
    const order =
      Array.isArray(record.process_order) && record.process_order.length
        ? record.process_order
        : selections.map((s) => s.code);
    const seen = new Set();
    const ordered = [];
    order.forEach((code) => {
      if (byCode[code] && !seen.has(code)) {
        ordered.push(byCode[code]);
        seen.add(code);
      }
    });
    selections.forEach((item) => {
      if (!seen.has(item.code)) ordered.push(item);
    });
    return ordered;
  }

  function renderCostRecordDetailHtml(record) {
    if (!record) return "";
    const ordered = orderedProcessSelections(record);
    const ro = ' readonly tabindex="-1"';

    const pickHtml = ordered
      .map(
        (item) => `
    <div class="process-pick-item process-pick-item--pick-only process-pick-item--readonly">
      <span class="process-pick-head">
        <span class="process-pick-checkmark" aria-hidden="true">✓</span>
        <span class="process-code">${escapeHtml(item.code)}</span>
        <span class="process-name" data-hover-text="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
      </span>
    </div>`
      )
      .join("");

    const detailHtml = ordered
      .map((item) => {
        const inhouse = !isOutsourceProcess(item.code) || item.inhouse;
        const priceVal =
          item.price !== "" && item.price != null && item.price !== "0" && item.price !== 0
            ? item.price
            : "0";
        const supplierNames = item.suppliers || (item.supplier ? [item.supplier] : []);
        const supplierControl = inhouse
          ? `<span class="process-inhouse-tag">${escapeHtml(INHOUSE_SUPPLIER_LABEL)}</span>`
          : buildReadonlySuppliersHtml(supplierNames);
        return `
    <div class="process-detail-row process-detail-row--readonly" data-process-code="${escapeHtml(item.code)}">
      <div class="process-detail-head">
        <span class="process-detail-code">${escapeHtml(item.code)}</span>
        <span class="process-detail-name" data-hover-text="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
      </div>
      <div class="process-detail-fields">
        <div class="field process-detail-supplier-field">
          <span class="field-label">${inhouse ? "类型" : "供应商"}</span>
          <div class="field-control cost-preview-supplier-control">
            ${supplierControl}
          </div>
        </div>
        <div class="field process-detail-price-field">
          <span class="field-label">单价（可选）</span>
          <input class="process-price cost-readonly-input" type="text"${ro} value="${escapeHtml(String(priceVal))}" />
        </div>
      </div>
    </div>`;
      })
      .join("");

    const orderHtml =
      ordered.length > 1
        ? `
        <div class="process-order-block items-block">
          <div class="items-head">
            <h5>工艺顺序</h5>
          </div>
          <ol class="process-order-list process-order-list--readonly">
            ${ordered
              .map(
                (item, idx) => `
              <li class="process-order-item process-order-item--readonly">
                <span class="process-order-seq">${idx + 1}</span>
                <span class="process-order-code">${escapeHtml(item.code)}</span>
                <span class="process-order-name">${escapeHtml(item.name)}</span>
              </li>`
              )
              .join("")}
          </ol>
        </div>`
        : "";

    const metaExtra =
      record.created_at &&
      record.updated_at &&
      record.created_at !== record.updated_at
        ? ` · 首次录入：${formatDate(record.created_at)}`
        : "";

    return `
    <div class="cost-entry-layout cost-preview-layout">
      <div class="cost-header-table">
        <div class="cost-header-row">
          <label class="field">
            <span>客户名称</span>
            <input type="text" class="cost-readonly-input"${ro} value="${escapeHtml(record.customer_name)}" />
          </label>
          <label class="field">
            <span>产品名称</span>
            <input type="text" class="cost-readonly-input"${ro} value="${escapeHtml(record.product_name)}" />
          </label>
          <label class="field">
            <span>模具编号</span>
            <input type="text" class="cost-readonly-input"${ro} value="${escapeHtml(record.mold_no)}" />
          </label>
          <label class="field">
            <span>产品料号</span>
            <input type="text" class="cost-readonly-input"${ro} value="${escapeHtml(record.product_part_no)}" />
          </label>
        </div>
        <div class="cost-header-row">
          <label class="field">
            <span>模穴</span>
            <input type="text" class="cost-readonly-input"${ro} value="${escapeHtml(record.cavity)}" />
          </label>
          <label class="field">
            <span>产品单重 (g)</span>
            <input type="text" class="cost-readonly-input"${ro} value="${escapeHtml(record.unit_weight_g)}" />
          </label>
          <label class="field">
            <span>材质</span>
            <input type="text" class="cost-readonly-input"${ro} value="${escapeHtml(record.material)}" />
          </label>
          <label class="field">
            <span>机台吨位</span>
            <input type="text" class="cost-readonly-input"${ro} value="${escapeHtml(record.machine_tonnage)}" />
          </label>
        </div>
        <div class="cost-header-row cost-header-row--calc">
          <label class="field">
            <span>原材单价</span>
            <input type="text" class="cost-readonly-input"${ro} value="${escapeHtml(record.material_unit_price || "0")}" />
          </label>
        </div>
      </div>
      <div class="items-block">
        <div class="items-head">
          <h4>工序选择</h4>
          <p class="items-subhint">已选 ${ordered.length} 道工序（预览不可修改）</p>
        </div>
        <div class="process-grid process-pick-grid process-pick-only-grid cost-preview-process-grid">${pickHtml || '<p class="empty-hint">未选择工序</p>'}</div>
      </div>
      ${
        ordered.length
          ? `
      <div class="items-block process-detail-block">
        <div class="items-head">
          <h4>单价与供应商</h4>
        </div>
        <div class="process-detail-panel">${detailHtml}</div>
      </div>`
          : ""
      }
      ${orderHtml}
      <div class="result-grid cost-detail-costs">
        <div class="result-row">
          <span class="r-label">原材成本</span>
          <span class="r-value">${money(record.material_cost)}</span>
        </div>
        <div class="result-row">
          <span class="r-label">工艺合计</span>
          <span class="r-value">${money(record.process_total)}</span>
        </div>
        <div class="result-row grand">
          <span class="r-label">单件成本</span>
          <span class="r-value">${money(record.unit_cost)}</span>
        </div>
      </div>
      <p class="detail-meta">更新时间：${formatDate(record.updated_at || record.created_at)}${metaExtra}</p>
    </div>`;
  }

  return {
    INHOUSE_PROCESS_CODE,
    INHOUSE_SUPPLIER_LABEL,
    loadOptions,
    loadSuppliers,
    renderMissingSupplierAlert,
    getSupplierNames,
    isOutsourceProcess,
    buildSupplierSelectHtml,
    buildProcessSuppliersHtml,
    setProcessSuppliersPanel,
    getProcessSuppliersFromPanel,
    bindProcessPickerGrid,
    bindProcessOrder,
    setProcessOrder,
    clearProcessOrder,
    getProcessOrder,
    refreshProcessOrder,
    bindProcessSupplierAddCombos,
    bindSupplierCombos,
    collectProcessEntries,
    validateProcessSuppliers,
    renderProcessGridHtml,
    renderProcessPickOnlyGridHtml,
    refreshProcessDetailPanel,
    bindStagedProcessPicker,
    captureProcessDetailState,
    selectionsToMap,
    getProcesses,
    getProcessOptions,
    getMaterials,
    money,
    formatDate,
    renderQuotePreview,
    renderCostRecordDetailHtml,
  };
})();
