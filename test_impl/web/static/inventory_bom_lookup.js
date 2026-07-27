/** 库存模块：料号 / 品名 / 客户 BOM 联想与互填 */
window.InventoryBomLookup = (function () {
  let suggestTimer = null;

  function esc(t) {
    return String(t ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function debounce(fn, ms) {
    return function (...args) {
      clearTimeout(suggestTimer);
      suggestTimer = setTimeout(() => fn.apply(this, args), ms);
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

  async function fetchSuggestions(q) {
    const query = (q || "").trim();
    if (query.length < 1) return [];
    const res = await fetch(
      `/api/cost/part-numbers?q=${encodeURIComponent(query)}&limit=15`
    );
    const data = await res.json();
    return data.items || [];
  }

  async function fetchCustomerSuggestions(q) {
    const query = (q || "").trim();
    if (query.length < 1) return [];
    const res = await fetch(
      `/api/cost/customers?q=${encodeURIComponent(query)}&limit=15`
    );
    const data = await res.json();
    return data.items || [];
  }

  function ensureCombo(input) {
    if (!input || input.closest(".inv-bom-combo")) return input?.closest(".inv-bom-combo");
    const wrap = document.createElement("div");
    wrap.className = "inv-bom-combo";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    const list = document.createElement("ul");
    list.className = "inv-bom-suggest";
    list.hidden = true;
    wrap.appendChild(list);
    return wrap;
  }

  function hideAllLists(except) {
    document.querySelectorAll(".inv-bom-suggest").forEach((ul) => {
      if (except && ul === except) return;
      ul.hidden = true;
    });
  }

  function renderList(combo, items, mode) {
    const list = combo.querySelector(".inv-bom-suggest");
    if (!list) return;
    if (!items.length) {
      list.innerHTML = '<li class="inv-bom-suggest-empty">BOM 中无匹配</li>';
      list.hidden = false;
      return;
    }
    list.innerHTML = items
      .map((item) => {
        const part = item.product_part_no || "";
        const name = item.product_name || "";
        const cust = item.customer_name || "";
        const meta = [cust, item.unit_weight_g ? `${item.unit_weight_g}g` : ""]
          .filter(Boolean)
          .join(" · ");
        const primary = mode === "name" ? name || part : part || name;
        const secondary = mode === "name" ? part : name;
        const primaryCls =
          mode === "name" ? "inv-bom-suggest-secondary" : "inv-bom-suggest-primary";
        const secondaryCls =
          mode === "name" ? "inv-bom-suggest-primary" : "inv-bom-suggest-secondary";
        return `<li class="inv-bom-suggest-item" tabindex="-1"
          data-part="${esc(part)}" data-name="${esc(name)}" data-customer="${esc(cust)}">
          <span class="${primaryCls}">${esc(primary)}</span>
          ${secondary ? `<span class="${secondaryCls}">${esc(secondary)}</span>` : ""}
          ${meta ? `<span class="inv-bom-suggest-meta">${esc(meta)}</span>` : ""}
        </li>`;
      })
      .join("");
    list.hidden = false;
  }

  function renderCustomerList(combo, items) {
    const list = combo.querySelector(".inv-bom-suggest");
    if (!list) return;
    if (!items.length) {
      list.innerHTML = '<li class="inv-bom-suggest-empty">无匹配客户</li>';
      list.hidden = false;
      return;
    }
    list.innerHTML = items
      .map(
        (name) =>
          `<li class="inv-bom-suggest-item inv-bom-suggest-customer" tabindex="-1" data-customer="${esc(name)}">
            <span class="inv-bom-suggest-primary">${esc(name)}</span>
          </li>`
      )
      .join("");
    list.hidden = false;
  }

  function renderKeywordList(combo, items) {
    const list = combo.querySelector(".inv-bom-suggest");
    if (!list) return;
    if (!items.length) {
      list.innerHTML = '<li class="inv-bom-suggest-empty">BOM 中无匹配</li>';
      list.hidden = false;
      return;
    }
    list.innerHTML = items
      .map((item) => {
        const part = item.product_part_no || "";
        const name = item.product_name || "";
        const cust = item.customer_name || "";
        const fill = part || name;
        return `<li class="inv-bom-suggest-item" tabindex="-1" data-fill="${esc(fill)}">
          <span class="inv-bom-suggest-primary">${esc(part)}</span>
          ${name ? `<span class="inv-bom-suggest-secondary">${esc(name)}</span>` : ""}
          ${cust ? `<span class="inv-bom-suggest-meta">${esc(cust)}</span>` : ""}
        </li>`;
      })
      .join("");
    list.hidden = false;
  }

  function applyItem(partInput, nameInput, customerInput, part, name, customer, hintEl) {
    if (partInput) partInput.value = part || "";
    if (nameInput) nameInput.value = name || "";
    if (customerInput && customer) customerInput.value = customer;
    hideAllLists();
    const bits = [part, name].filter(Boolean).join(" · ");
    if (part) {
      setHint(hintEl, customer ? `已选：${bits} · ${customer}` : bits ? `已选：${bits}` : `已选料号 ${part}`, "ok");
    } else {
      setHint(hintEl, "", "");
    }
  }

  function bindCombo(combo, partInput, nameInput, customerInput, hintEl, mode) {
    const input = mode === "name" ? nameInput : partInput;
    if (!input || !combo) return;

    const runSuggest = debounce(async () => {
      const q = input.value.trim();
      if (q.length < 1) {
        hideAllLists();
        return;
      }
      const items = await fetchSuggestions(q);
      renderList(combo, items, mode);
    }, 220);

    input.addEventListener("focus", () => {
      if (input.value.trim()) runSuggest();
    });
    input.addEventListener("input", () => {
      if (mode === "part" && nameInput) nameInput.dataset.userEdited = "";
      if (mode === "name" && partInput) partInput.dataset.userEdited = "";
      runSuggest();
    });
    input.addEventListener("keydown", (ev) => {
      const list = combo.querySelector(".inv-bom-suggest");
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
            hintEl
          );
        }
      }
    });

    const list = combo.querySelector(".inv-bom-suggest");
    list?.addEventListener("mousedown", (ev) => {
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
        hintEl
      );
    });

    combo.addEventListener("click", (ev) => ev.stopPropagation());
  }

  function bindCustomerCombo(combo, customerInput) {
    if (!customerInput || !combo) return;

    const runSuggest = debounce(async () => {
      const q = customerInput.value.trim();
      if (q.length < 1) {
        hideAllLists();
        return;
      }
      const items = await fetchCustomerSuggestions(q);
      renderCustomerList(combo, items);
    }, 220);

    customerInput.addEventListener("focus", () => {
      if (customerInput.value.trim()) runSuggest();
    });
    customerInput.addEventListener("input", runSuggest);
    customerInput.addEventListener("keydown", (ev) => {
      const list = combo.querySelector(".inv-bom-suggest");
      if (!list || list.hidden) return;
      if (ev.key === "Escape") {
        list.hidden = true;
      } else if (ev.key === "Enter") {
        const first = list.querySelector(".inv-bom-suggest-item[data-customer]");
        if (first) {
          ev.preventDefault();
          customerInput.value = first.dataset.customer || "";
          hideAllLists();
        }
      }
    });

    const list = combo.querySelector(".inv-bom-suggest");
    list?.addEventListener("mousedown", (ev) => {
      const row = ev.target.closest(".inv-bom-suggest-item[data-customer]");
      if (!row) return;
      ev.preventDefault();
      customerInput.value = row.dataset.customer || "";
      hideAllLists();
    });

    combo.addEventListener("click", (ev) => ev.stopPropagation());
  }

  function bindKeywordCombo(combo, keywordInput) {
    if (!keywordInput || !combo) return;

    const runSuggest = debounce(async () => {
      const q = keywordInput.value.trim();
      if (q.length < 1) {
        hideAllLists();
        return;
      }
      const items = await fetchSuggestions(q);
      renderKeywordList(combo, items);
    }, 220);

    keywordInput.addEventListener("focus", () => {
      if (keywordInput.value.trim()) runSuggest();
    });
    keywordInput.addEventListener("input", runSuggest);
    keywordInput.addEventListener("keydown", (ev) => {
      const list = combo.querySelector(".inv-bom-suggest");
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
    if (nameInput && name) nameInput.value = name;
    if (customerInput && customer) customerInput.value = customer;
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
    if (partInput) partInput.value = part;
    const bomName = data.product_spec || data.product_name || name;
    const customer = data.customer_name || "";
    if (nameInput && bomName) nameInput.value = bomName;
    if (customerInput && customer) customerInput.value = customer;
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
   * @param {{ partInput: HTMLInputElement, nameInput: HTMLInputElement, customerInput?: HTMLInputElement, hintEl?: HTMLElement }} opts
   */
  function bindPair(opts) {
    const partInput = opts.partInput;
    const nameInput = opts.nameInput;
    const customerInput = opts.customerInput || null;
    const hintEl = opts.hintEl || null;
    if (!partInput || !nameInput) return;

    const partCombo = ensureCombo(partInput);
    const nameCombo = ensureCombo(nameInput);
    bindCombo(partCombo, partInput, nameInput, customerInput, hintEl, "part");
    bindCombo(nameCombo, partInput, nameInput, customerInput, hintEl, "name");

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

  /** @param {{ customerInput: HTMLInputElement }} opts */
  function bindCustomer(opts) {
    const customerInput = opts.customerInput;
    if (!customerInput) return;
    const combo = ensureCombo(customerInput);
    bindCustomerCombo(combo, customerInput);
    ensureDocClickHide();
  }

  /** @param {{ keywordInput: HTMLInputElement }} opts */
  function bindKeyword(opts) {
    const keywordInput = opts.keywordInput;
    if (!keywordInput) return;
    const combo = ensureCombo(keywordInput);
    bindKeywordCombo(combo, keywordInput);
    ensureDocClickHide();
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

  return {
    bindPair,
    bindCustomer,
    bindKeyword,
    resolvePartNo,
    lookupByPartNo,
    lookupByProductName,
  };
})();
