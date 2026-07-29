/** 库存模块：料号 / 品名 / 客户 BOM 联想与互填 */
window.InventoryBomLookup = (function () {
  function esc(t) {
    return String(t ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function debounce(fn, ms) {
    let timer = null;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  function setHint(el, text, kind) {
    if (!el) return;
    if (!text) {
      el.hidden = true;
      el.textContent = "";
      el.className = "field-hint inv-bom-hint";
      return;
    }
    el.hidden = false;
    el.textContent = text;
    el.className = "field-hint inv-bom-hint" + (kind ? ` ${kind}` : "");
  }

  async function fetchSuggestions(q, limit) {
    const lim = limit || 15;
    const res = await fetch(
      `/api/cost/part-numbers?q=${encodeURIComponent((q || "").trim())}&limit=${lim}`
    );
    const data = await res.json();
    return data.items || [];
  }

  async function fetchCustomerSuggestions(q, limit) {
    const lim = limit || 15;
    const res = await fetch(
      `/api/cost/customers?q=${encodeURIComponent((q || "").trim())}&limit=${lim}`
    );
    const data = await res.json();
    return data.items || [];
  }

  async function fetchMasterCustomerSuggestions(q, limit) {
    const lim = limit || 30;
    const res = await fetch(
      `/api/master/customers?q=${encodeURIComponent(q || "")}&limit=${lim}`
    );
    const data = await res.json();
    return data.items || [];
  }

  const STANDARD_COMBO_OPTS = {
    openOnFocus: true,
    minChars: 0,
    showToggle: true,
    simpleList: true,
  };

  let suppressSuggestDepth = 0;

  function withSuppressSuggest(fn) {
    suppressSuggestDepth += 1;
    try {
      return fn();
    } finally {
      suppressSuggestDepth -= 1;
    }
  }

  function isSuggestSuppressed() {
    return suppressSuggestDepth > 0;
  }

  function useInnerSearch(opts, withSearch) {
    if (!withSearch) return false;
    if (opts.simpleList) return false;
    return opts.innerSearch !== false;
  }

  function comboOptsFrom(raw) {
    if (typeof raw === "function") return { fetchFn: raw };
    return raw || {};
  }

  function useDropdownSearch(opts) {
    return !!(opts.showToggle || opts.openOnFocus);
  }

  function ensureCombo(input, opts = {}) {
    if (!input) return null;
    let combo = input.closest(".inv-bom-combo");
    if (!combo) {
      combo = document.createElement("div");
      combo.className = "inv-bom-combo";
      input.parentNode.insertBefore(combo, input);
      combo.appendChild(input);
      const list = document.createElement("ul");
      list.className = "inv-bom-suggest";
      list.hidden = true;
      combo.appendChild(list);
    }
    if (opts.showToggle) {
      combo.classList.add("inv-bom-combo--select");
      if (!combo.querySelector(".inv-bom-combo-toggle")) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "inv-bom-combo-toggle";
        btn.setAttribute("aria-label", "展开选项");
        btn.tabIndex = -1;
        const list = combo.querySelector(".inv-bom-suggest");
        combo.insertBefore(btn, list);
      }
    }
    return combo;
  }

  function ensureSuggestSearch(combo) {
    const list = combo?.querySelector(".inv-bom-suggest");
    if (!list) return null;
    let row = list.querySelector(".inv-bom-suggest-search-row");
    if (!row) {
      row = document.createElement("li");
      row.className = "inv-bom-suggest-search-row";
      row.innerHTML =
        '<input type="text" class="inv-bom-suggest-search" placeholder="输入关键字筛选…" autocomplete="off" spellcheck="false" />';
      list.insertBefore(row, list.firstChild);
    }
    return row.querySelector(".inv-bom-suggest-search");
  }

  function clearSuggestItems(list) {
    list.querySelectorAll(".inv-bom-suggest-item, .inv-bom-suggest-empty").forEach((el) => el.remove());
  }

  function getComboQuery(combo, externalInput) {
    const search = combo?.querySelector(".inv-bom-suggest-search");
    if (search) return (search.value || "").trim();
    return (externalInput?.value || "").trim();
  }

  function syncSearchFromExternal(combo, externalInput) {
    const search = combo?.querySelector(".inv-bom-suggest-search");
    if (search && externalInput) search.value = externalInput.value;
  }

  function focusSuggestSearch(combo) {
    window.setTimeout(() => {
      const list = combo?.querySelector(".inv-bom-suggest");
      const search = combo?.querySelector(".inv-bom-suggest-search");
      if (search && list && !list.hidden) {
        search.focus();
      }
    }, 0);
  }

  function wireSuggestSearch(combo, externalInput, loadSuggestions, itemSelector) {
    const search = ensureSuggestSearch(combo);
    if (!search || search.dataset.bound) return;
    search.dataset.bound = "1";
    search.addEventListener("input", () => {
      if (externalInput) externalInput.value = search.value;
      loadSuggestions(false);
    });
    search.addEventListener("keydown", (ev) => {
      ev.stopPropagation();
      if (ev.key === "Escape") {
        hideAllLists();
      } else if (ev.key === "Enter") {
        ev.preventDefault();
        const first = combo.querySelector(itemSelector);
        if (first) first.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      }
    });
    search.addEventListener("mousedown", (ev) => ev.stopPropagation());
    search.addEventListener("click", (ev) => ev.stopPropagation());
  }

  function wireComboToggle(combo, input, loadSuggestions) {
    const toggle = combo?.querySelector(".inv-bom-combo-toggle");
    if (!toggle || toggle.dataset.bound) return;
    toggle.dataset.bound = "1";
    toggle.addEventListener("mousedown", (ev) => {
      ev.preventDefault();
      const list = combo.querySelector(".inv-bom-suggest");
      if (list && !list.hidden) {
        list.hidden = true;
        return;
      }
      syncSearchFromExternal(combo, input);
      loadSuggestions(true);
    });
  }

  function hideAllLists(except) {
    document.querySelectorAll(".inv-bom-suggest").forEach((ul) => {
      if (except && ul === except) return;
      ul.hidden = true;
    });
  }

  function renderList(combo, items, mode, withSearch, simpleList, innerSearch) {
    const list = combo.querySelector(".inv-bom-suggest");
    if (!list) return;
    if (innerSearch) ensureSuggestSearch(combo);
    clearSuggestItems(list);
    if (!items.length) {
      const empty = document.createElement("li");
      empty.className = "inv-bom-suggest-empty";
      empty.textContent = "BOM 中无匹配";
      list.appendChild(empty);
    } else {
      items.forEach((item) => {
        const part = item.product_part_no || "";
        const name = item.product_name || "";
        const cust = item.customer_name || "";
        const li = document.createElement("li");
        li.className = "inv-bom-suggest-item";
        li.tabIndex = -1;
        li.dataset.part = part;
        li.dataset.name = name;
        li.dataset.customer = cust;
        if (simpleList) {
          if (mode === "name") {
            li.innerHTML = `<span class="inv-bom-suggest-name-only">${esc(name || part)}</span>`;
          } else {
            li.innerHTML = `<span class="inv-bom-suggest-part-only">${esc(part || name)}</span>`;
          }
        } else {
          const meta = [cust, item.unit_weight_g ? `${item.unit_weight_g}g` : ""]
            .filter(Boolean)
            .join(" · ");
          const primary = mode === "name" ? name || part : part || name;
          const secondary = mode === "name" ? part : name;
          const primaryCls =
            mode === "name" ? "inv-bom-suggest-secondary" : "inv-bom-suggest-primary";
          const secondaryCls =
            mode === "name" ? "inv-bom-suggest-primary" : "inv-bom-suggest-secondary";
          li.innerHTML = `<span class="${primaryCls}">${esc(primary)}</span>${
            secondary ? `<span class="${secondaryCls}">${esc(secondary)}</span>` : ""
          }${meta ? `<span class="inv-bom-suggest-meta">${esc(meta)}</span>` : ""}`;
        }
        list.appendChild(li);
      });
    }
    list.hidden = false;
  }

  function renderCustomerList(combo, items, withSearch) {
    const list = combo.querySelector(".inv-bom-suggest");
    if (!list) return;
    if (withSearch) ensureSuggestSearch(combo);
    clearSuggestItems(list);
    if (!items.length) {
      const empty = document.createElement("li");
      empty.className = "inv-bom-suggest-empty";
      empty.textContent = "无匹配客户";
      list.appendChild(empty);
    } else {
      items.forEach((name) => {
        const li = document.createElement("li");
        li.className = "inv-bom-suggest-item inv-bom-suggest-customer";
        li.tabIndex = -1;
        li.dataset.customer = name;
        li.innerHTML = `<span class="inv-bom-suggest-primary">${esc(name)}</span>`;
        list.appendChild(li);
      });
    }
    list.hidden = false;
  }

  function renderKeywordList(combo, items, withSearch) {
    const list = combo.querySelector(".inv-bom-suggest");
    if (!list) return;
    if (withSearch) ensureSuggestSearch(combo);
    clearSuggestItems(list);
    if (!items.length) {
      const empty = document.createElement("li");
      empty.className = "inv-bom-suggest-empty";
      empty.textContent = "BOM 中无匹配";
      list.appendChild(empty);
    } else {
      items.forEach((item) => {
        const part = item.product_part_no || "";
        const name = item.product_name || "";
        const cust = item.customer_name || "";
        const fill = part || name;
        const li = document.createElement("li");
        li.className = "inv-bom-suggest-item";
        li.tabIndex = -1;
        li.dataset.fill = fill;
        li.dataset.part = part;
        li.dataset.name = name;
        li.dataset.customer = cust;
        li.innerHTML = `<span class="inv-bom-suggest-primary">${esc(part || name)}</span>${
          name && part ? `<span class="inv-bom-suggest-secondary">${esc(name)}</span>` : ""
        }${cust ? `<span class="inv-bom-suggest-meta">${esc(cust)}</span>` : ""}`;
        list.appendChild(li);
      });
    }
    list.hidden = false;
  }

  function applyItem(partInput, nameInput, customerInput, part, name, customer, hintEl, onSelect) {
    withSuppressSuggest(() => {
      if (partInput) partInput.value = part || "";
      if (nameInput) nameInput.value = name || "";
      if (customerInput && customer) customerInput.value = customer;
    });
    hideAllLists();
    const bits = [part, name].filter(Boolean).join(" · ");
    if (part) {
      setHint(hintEl, customer ? `已选：${bits} · ${customer}` : bits ? `已选：${bits}` : `已选料号 ${part}`, "ok");
    } else {
      setHint(hintEl, "", "");
    }
    if (onSelect) onSelect({ part: part || "", name: name || "", customer: customer || "" });
  }

  function bindCombo(combo, partInput, nameInput, customerInput, hintEl, mode, onSelect, comboOpts) {
    const input = mode === "name" ? nameInput : partInput;
    if (!input || !combo) return;
    const opts = comboOptsFrom(comboOpts);
    const minChars = opts.minChars != null ? opts.minChars : 1;
    const openOnFocus = !!opts.openOnFocus;
    const withSearch = useDropdownSearch(opts);
    const simpleList = !!opts.simpleList;
    const innerSearch = useInnerSearch(opts, withSearch);

    async function loadSuggestions(focusSearch) {
      if (isSuggestSuppressed()) return;
      const q = getComboQuery(combo, input);
      if (minChars > 0 && q.length < minChars) {
        hideAllLists();
        return;
      }
      const items = await fetchSuggestions(q, minChars === 0 ? 30 : 15);
      renderList(combo, items, mode, withSearch, simpleList, innerSearch);
      if (focusSearch && innerSearch) focusSuggestSearch(combo);
    }

    const runSuggest = debounce(() => loadSuggestions(false), 180);

    if (innerSearch) {
      wireSuggestSearch(combo, input, loadSuggestions, ".inv-bom-suggest-item[data-part]");
    }

    input.addEventListener("focus", () => {
      if (isSuggestSuppressed()) return;
      if (openOnFocus || input.value.trim()) {
        syncSearchFromExternal(combo, input);
        loadSuggestions(innerSearch);
      }
    });
    input.addEventListener("input", () => {
      if (isSuggestSuppressed()) return;
      if (mode === "part" && nameInput) nameInput.dataset.userEdited = "";
      if (mode === "name" && partInput) partInput.dataset.userEdited = "";
      syncSearchFromExternal(combo, input);
      runSuggest();
      if (innerSearch) {
        const list = combo.querySelector(".inv-bom-suggest");
        if (list?.hidden) loadSuggestions(false);
      }
    });
    wireComboToggle(combo, input, loadSuggestions);
    input.addEventListener("keydown", (ev) => {
      const list = combo.querySelector(".inv-bom-suggest");
      if (ev.key === "ArrowDown" && (!list || list.hidden)) {
        ev.preventDefault();
        syncSearchFromExternal(combo, input);
        loadSuggestions(innerSearch);
        return;
      }
      if (!list || list.hidden) return;
      if (ev.key === "Escape") {
        list.hidden = true;
      } else if (ev.key === "Enter") {
        const first = list.querySelector(".inv-bom-suggest-item[data-part]");
        if (first) {
          ev.preventDefault();
          applyItem(
            partInput,
            nameInput,
            customerInput,
            first.dataset.part,
            first.dataset.name,
            first.dataset.customer,
            hintEl,
            onSelect
          );
        }
      }
    });

    const list = combo.querySelector(".inv-bom-suggest");
    list?.addEventListener("mousedown", (ev) => {
      if (ev.target.closest(".inv-bom-suggest-search-row")) return;
      const row = ev.target.closest(".inv-bom-suggest-item[data-part]");
      if (!row) return;
      ev.preventDefault();
      applyItem(
        partInput,
        nameInput,
        customerInput,
        row.dataset.part,
        row.dataset.name,
        row.dataset.customer,
        hintEl,
        onSelect
      );
    });

    combo.addEventListener("click", (ev) => ev.stopPropagation());
  }

  function bindCustomerCombo(combo, customerInput, rawOpts) {
    if (!customerInput || !combo) return;
    const opts = comboOptsFrom(rawOpts);
    const suggest = opts.fetchFn || opts.fetchSuggestions || fetchCustomerSuggestions;
    const minChars = opts.minChars != null ? opts.minChars : 1;
    const openOnFocus = !!opts.openOnFocus;
    const withSearch = useDropdownSearch(opts);
    const innerSearch = useInnerSearch(opts, withSearch);

    function applyPick(value) {
      const picked = value || "";
      withSuppressSuggest(() => {
        if (typeof opts.onSelect === "function") {
          opts.onSelect(picked);
          customerInput.value = "";
        } else {
          customerInput.value = picked;
        }
      });
      hideAllLists();
    }

    async function loadSuggestions(focusSearch) {
      if (isSuggestSuppressed()) return;
      const q = getComboQuery(combo, customerInput);
      if (minChars > 0 && q.length < minChars) {
        hideAllLists();
        return;
      }
      const items = await suggest(q);
      renderCustomerList(combo, items, innerSearch);
      if (focusSearch && innerSearch) focusSuggestSearch(combo);
    }

    const runSuggest = debounce(() => loadSuggestions(false), 180);

    if (innerSearch) {
      wireSuggestSearch(combo, customerInput, loadSuggestions, ".inv-bom-suggest-item[data-customer]");
    }

    customerInput.addEventListener("focus", () => {
      if (isSuggestSuppressed()) return;
      if (openOnFocus || customerInput.value.trim()) {
        syncSearchFromExternal(combo, customerInput);
        loadSuggestions(innerSearch);
      }
    });
    customerInput.addEventListener("input", () => {
      if (isSuggestSuppressed()) return;
      syncSearchFromExternal(combo, customerInput);
      runSuggest();
      if (innerSearch) {
        const list = combo.querySelector(".inv-bom-suggest");
        if (list?.hidden) loadSuggestions(false);
      }
    });
    wireComboToggle(combo, customerInput, loadSuggestions);
    customerInput.addEventListener("keydown", (ev) => {
      const list = combo.querySelector(".inv-bom-suggest");
      if (ev.key === "ArrowDown" && (!list || list.hidden)) {
        ev.preventDefault();
        syncSearchFromExternal(combo, customerInput);
        loadSuggestions(innerSearch);
        return;
      }
      if (!list || list.hidden) return;
      if (ev.key === "Escape") {
        list.hidden = true;
      } else if (ev.key === "Enter") {
        const first = list.querySelector(".inv-bom-suggest-item[data-customer]");
        if (first) {
          ev.preventDefault();
          applyPick(first.dataset.customer || "");
        }
      }
    });

    const list = combo.querySelector(".inv-bom-suggest");
    list?.addEventListener("mousedown", (ev) => {
      if (ev.target.closest(".inv-bom-suggest-search-row")) return;
      const row = ev.target.closest(".inv-bom-suggest-item[data-customer]");
      if (!row) return;
      ev.preventDefault();
      applyPick(row.dataset.customer || "");
    });

    combo.addEventListener("click", (ev) => ev.stopPropagation());
  }

  function bindKeywordCombo(combo, keywordInput, rawOpts) {
    if (!keywordInput || !combo) return;
    const opts = comboOptsFrom(rawOpts);
    const minChars = opts.minChars != null ? opts.minChars : 1;
    const openOnFocus = !!opts.openOnFocus;
    const withSearch = useDropdownSearch(opts);

    async function loadSuggestions(focusSearch) {
      if (isSuggestSuppressed()) return;
      const q = getComboQuery(combo, keywordInput);
      if (minChars > 0 && q.length < minChars) {
        hideAllLists();
        return;
      }
      const items = await fetchSuggestions(q, minChars === 0 ? 30 : 15);
      renderKeywordList(combo, items, withSearch);
      if (focusSearch && withSearch) focusSuggestSearch(combo);
    }

    const runSuggest = debounce(() => loadSuggestions(false), 220);

    if (withSearch) {
      wireSuggestSearch(combo, keywordInput, loadSuggestions, ".inv-bom-suggest-item[data-fill]");
    }

    keywordInput.addEventListener("focus", () => {
      if (openOnFocus || keywordInput.value.trim()) {
        syncSearchFromExternal(combo, keywordInput);
        loadSuggestions(withSearch);
      }
    });
    keywordInput.addEventListener("input", () => {
      syncSearchFromExternal(combo, keywordInput);
      runSuggest();
      if (withSearch) {
        const list = combo.querySelector(".inv-bom-suggest");
        if (list?.hidden) loadSuggestions(false);
      }
    });
    wireComboToggle(combo, keywordInput, loadSuggestions);
    keywordInput.addEventListener("keydown", (ev) => {
      const list = combo.querySelector(".inv-bom-suggest");
      if (ev.key === "ArrowDown" && (!list || list.hidden)) {
        ev.preventDefault();
        syncSearchFromExternal(combo, keywordInput);
        loadSuggestions(withSearch);
        return;
      }
      if (!list || list.hidden) return;
      if (ev.key === "Escape") {
        list.hidden = true;
      } else if (ev.key === "Enter") {
        const first = list.querySelector(".inv-bom-suggest-item[data-fill]");
        if (first) {
          ev.preventDefault();
          keywordInput.value = first.dataset.fill || "";
          hideAllLists();
        }
      }
    });

    const list = combo.querySelector(".inv-bom-suggest");
    list?.addEventListener("mousedown", (ev) => {
      if (ev.target.closest(".inv-bom-suggest-search-row")) return;
      const row = ev.target.closest(".inv-bom-suggest-item[data-fill]");
      if (!row) return;
      ev.preventDefault();
      keywordInput.value = row.dataset.fill || "";
      hideAllLists();
    });

    combo.addEventListener("click", (ev) => ev.stopPropagation());
  }

  async function lookupByPartNo(partInput, nameInput, hintEl, customerInput) {
    const part = partInput?.value.trim() || "";
    if (part.length < 1) return "";
    const res = await fetch(
      `/api/bom/lookup?${new URLSearchParams({ customer_part_no: part })}`
    );
    const data = await res.json();
    if (!res.ok) {
      setHint(hintEl, data.error || "料号未在 BOM 建档", "error");
      return part;
    }
    const name = data.product_name || data.product_spec || "";
    const customer = data.customer_name || "";
    withSuppressSuggest(() => {
      if (nameInput && name) nameInput.value = name;
      if (customerInput && customer) customerInput.value = customer;
    });
    hideAllLists();
    const hintBits = [part, name, customer].filter(Boolean).join(" · ");
    setHint(hintEl, `BOM：${hintBits}`, "ok");
    return part;
  }

  async function lookupByProductName(partInput, nameInput, hintEl, customerInput) {
    const name = nameInput?.value.trim() || "";
    if (name.length < 1) return "";
    const res = await fetch(
      `/api/master/lookup?${new URLSearchParams({ product_spec: name })}`
    );
    const data = await res.json();
    const part = (data.customer_part_no || "").trim();
    if (!part) {
      setHint(hintEl, "品名未在 BOM 中找到对应料号", "error");
      return "";
    }
    const bomName = data.product_spec || data.product_name || name;
    const customer = data.customer_name || "";
    withSuppressSuggest(() => {
      if (partInput) partInput.value = part;
      if (nameInput && bomName) nameInput.value = bomName;
      if (customerInput && customer) customerInput.value = customer;
    });
    hideAllLists();
    const hintBits = [part, bomName, customer].filter(Boolean).join(" · ");
    setHint(hintEl, `BOM：${hintBits}`, "ok");
    return part;
  }

  function ensureDocClickHide() {
    if (document.documentElement.dataset.invBomDocBound) return;
    document.documentElement.dataset.invBomDocBound = "1";
    document.addEventListener("click", () => hideAllLists());
  }

  /**
   * @param {{ partInput: HTMLInputElement, nameInput: HTMLInputElement, customerInput?: HTMLInputElement, hintEl?: HTMLElement, onSelect?: Function, openOnFocus?: boolean, minChars?: number, showToggle?: boolean }} opts
   */
  function bindPair(opts) {
    const partInput = opts.partInput;
    const nameInput = opts.nameInput;
    const customerInput = opts.customerInput || null;
    const hintEl = opts.hintEl || null;
    const onSelect = opts.onSelect || null;
    if (!partInput || !nameInput) return;

    const comboOpts = {
      minChars: opts.minChars != null ? opts.minChars : 1,
      openOnFocus: !!opts.openOnFocus,
      showToggle: !!opts.showToggle,
      simpleList: !!opts.simpleList,
    };
    const partCombo = ensureCombo(partInput, comboOpts);
    const nameCombo = ensureCombo(nameInput, comboOpts);
    bindCombo(partCombo, partInput, nameInput, customerInput, hintEl, "part", onSelect, comboOpts);
    bindCombo(nameCombo, partInput, nameInput, customerInput, hintEl, "name", onSelect, comboOpts);

    partInput.addEventListener("blur", () => {
      window.setTimeout(() => {
        if (partInput.value.trim()) lookupByPartNo(partInput, nameInput, hintEl, customerInput);
      }, 180);
    });
    nameInput.addEventListener("blur", () => {
      window.setTimeout(() => {
        if (!partInput.value.trim() && nameInput.value.trim()) {
          lookupByProductName(partInput, nameInput, hintEl, customerInput);
        }
      }, 180);
    });

    ensureDocClickHide();
  }

  /** @param {{ customerInput: HTMLInputElement, fetchSuggestions?: Function, openOnFocus?: boolean, minChars?: number, showToggle?: boolean }} opts */
  function bindCustomer(opts) {
    const customerInput = opts.customerInput;
    if (!customerInput) return;
    const comboOpts = {
      minChars: opts.minChars != null ? opts.minChars : 1,
      openOnFocus: !!opts.openOnFocus,
      showToggle: !!opts.showToggle,
      simpleList: !!opts.simpleList,
      fetchFn: opts.fetchSuggestions,
      fetchSuggestions: opts.fetchSuggestions,
      onSelect: opts.onSelect,
    };
    const combo = ensureCombo(customerInput, comboOpts);
    bindCustomerCombo(combo, customerInput, comboOpts);
    ensureDocClickHide();
  }

  /** @param {{ keywordInput: HTMLInputElement, openOnFocus?: boolean, minChars?: number, showToggle?: boolean }} opts */
  function bindKeyword(opts) {
    const keywordInput = opts.keywordInput;
    if (!keywordInput) return;
    const comboOpts = {
      minChars: opts.minChars != null ? opts.minChars : 1,
      openOnFocus: !!opts.openOnFocus,
      showToggle: !!opts.showToggle,
    };
    const combo = ensureCombo(keywordInput, comboOpts);
    bindKeywordCombo(combo, keywordInput, comboOpts);
    ensureDocClickHide();
  }

  /** 仅料号字段（筛选栏等无品名框场景） */
  function bindPartOnly(opts) {
    const partInput = opts.partInput;
    if (!partInput) return;
    const comboOpts = {
      minChars: opts.minChars != null ? opts.minChars : 1,
      openOnFocus: !!opts.openOnFocus,
      showToggle: !!opts.showToggle,
      simpleList: opts.simpleList != null ? !!opts.simpleList : true,
    };
    const combo = ensureCombo(partInput, comboOpts);
    bindCombo(
      combo,
      partInput,
      opts.nameInput || null,
      opts.customerInput || null,
      opts.hintEl || null,
      "part",
      opts.onSelect || null,
      comboOpts
    );
    ensureDocClickHide();
  }

  function bindMaterialList(input, materials, rawOpts) {
    if (!input) return;
    const list = materials || [];
    const comboOpts = Object.assign({}, STANDARD_COMBO_OPTS, rawOpts || {});
    bindCustomer({
      customerInput: input,
      fetchSuggestions: (q) => {
        const query = (q || "").trim().toLowerCase();
        return Promise.resolve(
          list.filter((m) => !query || String(m).toLowerCase().includes(query)).slice(0, 30)
        );
      },
      openOnFocus: comboOpts.openOnFocus,
      minChars: comboOpts.minChars,
      showToggle: comboOpts.showToggle,
    });
  }

  /** 提交前解析出 BOM 料号（优先料号框，否则按品名反查） */
  async function resolvePartNo(partInput, nameInput, hintEl, customerInput) {
    const part = partInput?.value.trim() || "";
    if (part) return lookupByPartNo(partInput, nameInput, hintEl, customerInput);
    const name = nameInput?.value.trim() || "";
    if (!name) {
      setHint(hintEl, "", "");
      return "";
    }
    let resolved = await lookupByProductName(partInput, nameInput, hintEl, customerInput);
    if (resolved) return resolved;
    const items = await fetchSuggestions(name);
    if (items.length === 1) {
      applyItem(
        partInput,
        nameInput,
        customerInput,
        items[0].product_part_no,
        items[0].product_name,
        items[0].customer_name,
        hintEl
      );
      return items[0].product_part_no || "";
    }
    if (items.length > 1) {
      setHint(hintEl, "有多条 BOM 匹配，请从下拉列表点选", "error");
    }
    return "";
  }

  function closeAllCombos() {
    hideAllLists();
    const active = document.activeElement;
    if (active && active.closest && active.closest(".inv-bom-combo")) {
      active.blur();
    }
  }

  return {
    STANDARD_COMBO_OPTS,
    fetchMasterCustomerSuggestions,
    bindPair,
    bindCustomer,
    bindKeyword,
    bindPartOnly,
    bindMaterialList,
    resolvePartNo,
    lookupByPartNo,
    lookupByProductName,
    closeAllCombos,
  };
})();
