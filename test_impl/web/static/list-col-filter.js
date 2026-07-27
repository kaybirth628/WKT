/** 表头列筛选（▾ 下拉面板），供订单列表、客商维护等复用 */
window.createListColFilter = function createListColFilter(options) {
  const {
    prefix,
    headSelector,
    columns,
    getCellKey,
    onChange,
  } = options;

  const ids = {
    panel: `${prefix}Panel`,
    title: `${prefix}PanelTitle`,
    close: `${prefix}PanelClose`,
    search: `${prefix}Search`,
    selectAll: `${prefix}SelectAll`,
    selectAllLabel: `${prefix}SelectAllLabel`,
    options: `${prefix}Options`,
    apply: `${prefix}Apply`,
    reset: `${prefix}Reset`,
  };

  const filters = {};
  let rowsCache = [];
  let panelCol = null;
  let pending = null;

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function getFilterSet(field) {
    const f = filters[field];
    return f instanceof Set ? f : null;
  }

  function setFilterSet(field, valueSet) {
    if (valueSet === null || valueSet === undefined) {
      delete filters[field];
      return;
    }
    filters[field] = new Set(valueSet);
  }

  function hasActiveFilters() {
    return Object.values(filters).some((v) => v instanceof Set);
  }

  function getUniqueValues(field) {
    const seen = new Set();
    rowsCache.forEach((row) => seen.add(getCellKey(row, field)));
    return [...seen].sort((a, b) => a.localeCompare(b, "zh-CN", { numeric: true }));
  }

  function applyFilters(rows) {
    return (rows || []).filter((row) => {
      for (const col of columns) {
        const allowed = getFilterSet(col.field);
        if (!allowed) continue;
        if (!allowed.has(getCellKey(row, col.field))) return false;
      }
      return true;
    });
  }

  function updateBtnStates() {
    document.querySelectorAll(`${headSelector} .list-filter-btn`).forEach((btn) => {
      btn.classList.toggle("is-active", Boolean(getFilterSet(btn.dataset.col)));
    });
  }

  function closePanel() {
    document.getElementById(ids.panel)?.classList.add("is-hidden");
    panelCol = null;
    pending = null;
  }

  function positionPanel(anchor) {
    const panel = document.getElementById(ids.panel);
    if (!panel || !anchor) return;
    const rect = anchor.getBoundingClientRect();
    const margin = 8;
    let left = rect.left;
    let top = rect.bottom + 4;
    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
    panel.classList.remove("is-hidden");
    requestAnimationFrame(() => {
      const pr = panel.getBoundingClientRect();
      if (left + pr.width > window.innerWidth - margin) {
        left = Math.max(margin, window.innerWidth - pr.width - margin);
        panel.style.left = `${left}px`;
      }
      if (top + pr.height > window.innerHeight - margin) {
        top = Math.max(margin, rect.top - pr.height - 4);
        panel.style.top = `${top}px`;
      }
    });
  }

  function getSearchQuery() {
    return (document.getElementById(ids.search)?.value || "").trim().toLowerCase();
  }

  function collectSelection() {
    const box = document.getElementById(ids.options);
    const cbs = box ? [...box.querySelectorAll("input[type=checkbox]")] : [];
    const q = getSearchQuery();
    if (q) {
      return new Set(cbs.filter((cb) => cb.checked).map((cb) => cb.dataset.value));
    }
    const selected = new Set(pending.selected);
    cbs.forEach((cb) => {
      if (cb.checked) selected.add(cb.dataset.value);
      else selected.delete(cb.dataset.value);
    });
    return selected;
  }

  function isFullSelection(selected, allValues) {
    return (
      allValues.length > 0 &&
      selected.size === allValues.length &&
      allValues.every((v) => selected.has(v))
    );
  }

  function syncSelectAll() {
    const selAll = document.getElementById(ids.selectAll);
    const box = document.getElementById(ids.options);
    if (!selAll || !box || !pending) return;
    const cbs = [...box.querySelectorAll("input[type=checkbox]")];
    if (!cbs.length) {
      selAll.checked = false;
      selAll.indeterminate = false;
      return;
    }
    const checkedVisible = cbs.filter((cb) => cb.checked).length;
    selAll.checked = checkedVisible === cbs.length;
    selAll.indeterminate = checkedVisible > 0 && checkedVisible < cbs.length;
    selAll.title = getSearchQuery() ? "仅作用于当前搜索结果中的选项" : "";
  }

  function renderOptions(searchQ) {
    const box = document.getElementById(ids.options);
    if (!box || !panelCol || !pending) return;
    const q = (searchQ || "").trim().toLowerCase();
    const values = pending.allValues.filter((v) => !q || v.toLowerCase().includes(q));
    const labelEl = document.getElementById(ids.selectAllLabel);
    if (labelEl) labelEl.textContent = q ? "全选当前搜索结果" : "全选";
    if (!values.length) {
      box.innerHTML = '<p class="list-col-filter-empty">无匹配选项</p>';
      syncSelectAll();
      return;
    }
    box.innerHTML = values
      .map(
        (v) =>
          `<label class="list-col-filter-opt"><input type="checkbox" data-value="${esc(v)}"${pending.selected.has(v) ? " checked" : ""} /> ${esc(v)}</label>`
      )
      .join("");
    box.querySelectorAll("input[type=checkbox]").forEach((cb) => {
      cb.addEventListener("change", () => {
        if (cb.checked) pending.selected.add(cb.dataset.value);
        else pending.selected.delete(cb.dataset.value);
        syncSelectAll();
      });
    });
    syncSelectAll();
  }

  function openPanel(btn) {
    const colField = btn.dataset.col;
    const col = columns.find((c) => c.field === colField);
    if (!col) return;
    const allValues = getUniqueValues(colField);
    const current = getFilterSet(colField);
    const selected = current
      ? new Set([...current].filter((v) => allValues.includes(v)))
      : new Set(allValues);
    panelCol = colField;
    pending = { allValues, selected, col };
    const titleEl = document.getElementById(ids.title);
    if (titleEl) titleEl.textContent = `筛选 · ${col.label}`;
    const search = document.getElementById(ids.search);
    if (search) search.value = "";
    renderOptions("");
    positionPanel(btn);
    search?.focus();
  }

  function applyPanel() {
    if (!panelCol || !pending) return;
    const { allValues } = pending;
    const selected = collectSelection();
    if (isFullSelection(selected, allValues)) {
      setFilterSet(panelCol, null);
    } else {
      setFilterSet(panelCol, selected);
    }
    closePanel();
    updateBtnStates();
    emitChange();
  }

  function resetPanel() {
    if (!panelCol) return;
    setFilterSet(panelCol, null);
    closePanel();
    updateBtnStates();
    emitChange();
  }

  function emitChange() {
    const filtered = applyFilters(rowsCache);
    onChange(filtered, {
      total: rowsCache.length,
      shown: filtered.length,
      filtered: hasActiveFilters(),
    });
  }

  function bindHeader() {
    document.querySelectorAll(`${headSelector} .list-filter-btn`).forEach((btn) => {
      if (btn.dataset.lcfBound === "1") return;
      btn.dataset.lcfBound = "1";
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const panel = document.getElementById(ids.panel);
        if (
          panelCol === btn.dataset.col &&
          panel &&
          !panel.classList.contains("is-hidden")
        ) {
          closePanel();
          return;
        }
        openPanel(btn);
      });
    });
  }

  function initPanel() {
    const panel = document.getElementById(ids.panel);
    if (!panel || panel.dataset.lcfInit === "1") return;
    panel.dataset.lcfInit = "1";

    document.getElementById(ids.apply)?.addEventListener("click", applyPanel);
    document.getElementById(ids.reset)?.addEventListener("click", resetPanel);
    document.getElementById(ids.close)?.addEventListener("click", closePanel);
    document.getElementById(ids.search)?.addEventListener("input", (e) => {
      renderOptions(e.target.value);
    });
    document.getElementById(ids.selectAll)?.addEventListener("change", (e) => {
      const box = document.getElementById(ids.options);
      if (!box || !pending) return;
      const checked = e.target.checked;
      box.querySelectorAll("input[type=checkbox]").forEach((cb) => {
        cb.checked = checked;
        if (checked) pending.selected.add(cb.dataset.value);
        else pending.selected.delete(cb.dataset.value);
      });
      syncSelectAll();
    });

    document.addEventListener("click", (e) => {
      const p = document.getElementById(ids.panel);
      if (!p || p.classList.contains("is-hidden")) return;
      if (p.contains(e.target) || e.target.closest(`${headSelector} .list-filter-btn`)) return;
      closePanel();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closePanel();
    });
  }

  function setRows(rows) {
    rowsCache = rows || [];
  }

  function refresh() {
    emitChange();
    updateBtnStates();
  }

  function clearAll() {
    Object.keys(filters).forEach((k) => delete filters[k]);
    closePanel();
    refresh();
  }

  initPanel();

  return {
    setRows,
    bindHeader,
    refresh,
    clearAll,
    applyFilters,
    hasActiveFilters,
    updateBtnStates,
  };
};
