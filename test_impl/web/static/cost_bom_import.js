(function () {
  var previewItems = [];
  var lastCustomerResolved = "";
  var splitCountsCache = {};
  var fileInput = document.getElementById("bomImportFile");
  var parseBtn = document.getElementById("bomImportParseBtn");
  var uploadBtn = document.getElementById("bomImportUploadBtn");
  var body = document.getElementById("bomImportBody");
  var previewArea = document.getElementById("bomImportPreviewArea");
  var uploadCard = document.querySelector("#bomBatchPanel .upload-card");
  var msg = document.getElementById("bomImportMsg");
  var successEl = document.getElementById("bomImportSuccess");
  var statsEl = document.getElementById("bomImportStats");
  var resultEl = document.getElementById("bomImportResult");
  var batchCustomerInput = document.getElementById("bomImportBatchCustomer");
  var applyAllBtn = document.getElementById("bomImportApplyAllBtn");
  var applyBlockedBtn = document.getElementById("bomImportApplyBlockedBtn");

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escAttr(s) {
    return esc(s).replace(/'/g, "&#39;");
  }

  function setMsg(text, ok) {
    if (!msg) return;
    msg.textContent = text || "";
    msg.className = "msg" + (text ? (ok ? " ok" : " error") : "");
  }

  function setBusy(busy) {
    if (parseBtn) {
      parseBtn.disabled = busy;
      parseBtn.textContent = busy ? "解析中…" : "解析预览";
    }
    if (!busy) updateToolbar();
    else {
      if (uploadBtn) uploadBtn.disabled = true;
      if (applyAllBtn) applyAllBtn.disabled = true;
      if (applyBlockedBtn) applyBlockedBtn.disabled = true;
    }
  }

  function tierLabel(tier) {
    if (tier === "passed") return "通过";
    if (tier === "pending") return "待核";
    return "阻断";
  }

  function tierClass(tier) {
    if (tier === "passed") return "bom-badge-pass";
    if (tier === "pending") return "bom-badge-pending";
    return "bom-badge-block";
  }

  function sheetSplitCounts(items) {
    var counts = {};
    items.forEach(function (item) {
      var key = item.sheet_name || "";
      counts[key] = (counts[key] || 0) + 1;
    });
    return counts;
  }

  function isSingleCustomerName(name) {
    var text = String(name || "").trim();
    if (!text) return false;
    return text.indexOf("、") < 0 && !/等\d+个/.test(text);
  }

  function refreshStatsFromItems() {
    if (!statsEl) return;
    var passed = 0;
    var pending = 0;
    var blocked = 0;
    var duplicate = 0;
    previewItems.forEach(function (item) {
      if (item.tier === "passed") passed += 1;
      else if (item.tier === "pending") pending += 1;
      else blocked += 1;
      if (item.duplicate_part_no) duplicate += 1;
    });
    var html =
      '<span class="bom-stat"><em>' +
      previewItems.length +
      '</em>条</span>' +
      '<span class="bom-stat bom-stat-pass"><em>' +
      passed +
      '</em>通过</span>' +
      '<span class="bom-stat bom-stat-pending"><em>' +
      pending +
      '</em>待核</span>' +
      '<span class="bom-stat bom-stat-block"><em>' +
      blocked +
      "</em>阻断</span>";
    if (duplicate) {
      html +=
        '<span class="bom-stat bom-stat-dup"><em>' +
        duplicate +
        "</em>料号重复</span>";
    }
    statsEl.innerHTML = html;
  }

  function updateToolbar() {
    var importable = previewItems.filter(function (p) {
      return p.tier === "passed" || p.tier === "pending";
    }).length;
    if (uploadBtn) uploadBtn.disabled = importable === 0;
    if (applyAllBtn) applyAllBtn.disabled = !previewItems.length;
    if (applyBlockedBtn) applyBlockedBtn.disabled = !previewItems.length;
  }

  function applyBatchCustomerHint(data) {
    if (batchCustomerInput && isSingleCustomerName(data.customer_resolved)) {
      batchCustomerInput.value = data.customer_resolved;
      lastCustomerResolved = data.customer_resolved;
    }
  }

  function renderStats(data) {
    if (!statsEl) return;
    var html =
      '<span class="bom-stat"><em>' +
      (data.total || 0) +
      '</em>条</span>' +
      '<span class="bom-stat bom-stat-pass"><em>' +
      (data.passed || 0) +
      '</em>通过</span>' +
      '<span class="bom-stat bom-stat-pending"><em>' +
      (data.pending || 0) +
      '</em>待核</span>' +
      '<span class="bom-stat bom-stat-block"><em>' +
      (data.blocked || 0) +
      "</em>阻断</span>";
    if (data.duplicate_parts) {
      html +=
        '<span class="bom-stat bom-stat-dup"><em>' +
        data.duplicate_parts +
        "</em>料号重复</span>";
    }
    statsEl.innerHTML = html;
  }

  function clearSuccessBanner() {
    if (!successEl) return;
    successEl.innerHTML = "";
    successEl.className = "bom-import-success is-hidden";
  }

  function showSuccessBanner(data) {
    if (!successEl) return;
    var imported = data.imported || 0;
    var errors = data.errors || [];
    var ok = imported > 0 && !errors.length;
    var partial = imported > 0 && errors.length > 0;
    var cls = ok ? "ok" : partial ? "warn" : "error";
    var parts = ["成功 " + imported + " 条"];
    if (data.created) parts.push("新增 " + data.created);
    if (data.updated) parts.push("覆盖 " + data.updated);
    if (data.removed_duplicates) parts.push("去重 " + data.removed_duplicates);
    var headline = ok ? "批量上传成功" : partial ? "部分上传成功" : "上传未完成";
    var html =
      "<strong>" +
      esc(headline) +
      "</strong> " +
      esc(parts.join("，")) +
      (errors.length ? "；失败 " + errors.length + " 条" : "") +
      "。可继续选择新的 Excel 文件导入。";
    if (imported > 0) {
      var q = lastCustomerResolved || "";
      var queryUrl =
        "/cost/query" + (q ? "?q=" + encodeURIComponent(q) : "");
      html +=
        ' <a class="bom-import-query-link" href="' +
        esc(queryUrl) +
        '">前往 BOM 查询</a>';
    }
    successEl.innerHTML = html;
    successEl.className = "bom-import-success " + cls;
    successEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function resetToUploadScreen(data) {
    previewItems = [];
    splitCountsCache = {};
    if (body) body.innerHTML = "";
    if (statsEl) statsEl.innerHTML = "";
    clearImportResult();
    if (previewArea) previewArea.classList.add("is-hidden");
    if (uploadCard) uploadCard.classList.remove("is-hidden");
    if (fileInput) fileInput.value = "";
    if (batchCustomerInput) batchCustomerInput.value = "";
    if (uploadBtn) uploadBtn.disabled = true;
    setMsg("", true);
    if (data) showSuccessBanner(data);
    updateToolbar();
  }

  function clearImportResult() {
    if (!resultEl) return;
    resultEl.innerHTML = "";
    resultEl.className = "bom-import-result is-hidden";
  }

  function renderImportResult(data) {
    if (!resultEl) return;
    var imported = data.imported || 0;
    var errors = data.errors || [];
    var ok = imported > 0 && !errors.length;
    var partial = imported > 0 && errors.length > 0;
    var failed = imported === 0;
    var cls = ok
      ? "bom-import-result ok"
      : partial
        ? "bom-import-result warn"
        : "bom-import-result error";
    var parts = ["成功 " + imported + " 条"];
    if (data.created) parts.push("新增 " + data.created);
    if (data.updated) parts.push("覆盖 " + data.updated);
    if (data.removed_duplicates) parts.push("去重 " + data.removed_duplicates);
    var headline = failed
      ? "导入未写入任何记录"
      : partial
        ? "部分导入成功"
        : "导入成功";
    var html =
      "<strong>" +
      esc(headline) +
      "</strong> " +
      esc(parts.join("，")) +
      (errors.length ? "；失败 " + errors.length + " 条" : "");
    if (errors.length) {
      html +=
        '<ul class="bom-import-error-list">' +
        errors
          .slice(0, 5)
          .map(function (e) {
            return (
              "<li>第 " +
              (Number(e.index) + 1) +
              " 条：" +
              esc(e.error || "未知错误") +
              "</li>"
            );
          })
          .join("") +
        (errors.length > 5
          ? "<li>…还有 " + (errors.length - 5) + " 条失败</li>"
          : "") +
        "</ul>";
    }
    if (imported > 0) {
      var q = lastCustomerResolved || "";
      var queryUrl =
        "/cost/query" + (q ? "?q=" + encodeURIComponent(q) : "");
      html +=
        ' <a class="bom-import-query-link" href="' +
        esc(queryUrl) +
        '">前往 BOM 查询</a>';
    }
    resultEl.innerHTML = html;
    resultEl.className = cls;
    resultEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function rowInputClass(item) {
    if (item.tier === "blocked") return "is-manual-warn";
    if (item.tier === "passed") return "is-manual-ok";
    return "";
  }

  function fieldInput(idx, field, value, opts) {
    opts = opts || {};
    var cls = ("bom-import-field-input " + rowInputClass(previewItems[idx] || {})).trim();
    if (opts.mono) cls += " bom-field-mono";
    if (opts.duplicatePart) cls += " bom-part-duplicate";
    var list = opts.list ? ' list="' + opts.list + '"' : "";
    var ph = opts.placeholder ? ' placeholder="' + escAttr(opts.placeholder) + '"' : "";
    var ro = opts.readonly ? " readonly" : "";
    return (
      '<input type="text" class="' +
      cls +
      '" data-index="' +
      idx +
      '" data-field="' +
      escAttr(field) +
      '" value="' +
      escAttr(value || "") +
      '"' +
      list +
      ph +
      ro +
      ' autocomplete="off" />'
    );
  }

  function bindEllipsisTips(root) {
    if (!window.HoverTip) return;
    var scope = root || body;
    if (!scope) return;
    scope.querySelectorAll(".bom-import-issues, .bom-import-process-readonly").forEach(function (el) {
      var text = (el.getAttribute("data-full-text") || el.textContent || "").trim();
      if (!text || text === "—") return;
      el.dataset.hoverText = text;
      el.removeAttribute("title");
      window.HoverTip.bind(el);
    });
  }

  function bindPreviewCombos(root) {
    var IBL = window.InventoryBomLookup;
    if (!IBL || !root) return;
    var opts = IBL.STANDARD_COMBO_OPTS;
    root.querySelectorAll("tr[data-index]").forEach(function (tr) {
      var cust = tr.querySelector('[data-field="customer_name"]');
      var part = tr.querySelector('[data-field="product_part_no"]');
      var name = tr.querySelector('[data-field="product_name"]');
      if (cust && !cust.dataset.comboBound) {
        cust.dataset.comboBound = "1";
        IBL.bindCustomer({
          customerInput: cust,
          fetchSuggestions: IBL.fetchMasterCustomerSuggestions,
          openOnFocus: opts.openOnFocus,
          minChars: opts.minChars,
          showToggle: opts.showToggle,
        });
      }
      if (part && name && !part.dataset.comboBound) {
        part.dataset.comboBound = "1";
        name.dataset.comboBound = "1";
        IBL.bindPair({
          partInput: part,
          nameInput: name,
          customerInput: cust,
          openOnFocus: opts.openOnFocus,
          minChars: opts.minChars,
          showToggle: opts.showToggle,
          simpleList: opts.simpleList,
        });
      }
    });
  }

  function collectRowFromDom(idx) {
    var tr = body && body.querySelector('tr[data-index="' + idx + '"]');
    var item = previewItems[idx] || {};
    var p = item.parsed || {};
    var out = {
      index: idx,
      parsed: p,
      sheet_name: item.sheet_name || "",
      fields: {},
    };
    if (!tr) {
      out.fields.customer_name = p.customer_name || "";
      return out;
    }
    tr.querySelectorAll(".bom-import-field-input").forEach(function (input) {
      var field = input.getAttribute("data-field");
      if (!field) return;
      var val = input.value.trim();
      if (field === "sheet_name") {
        out.sheet_name = val;
      } else {
        out.fields[field] = val;
      }
    });
    out.customer_name = out.fields.customer_name || "";
    return out;
  }

  function renderPreviewRow(item, idx) {
    var p = item.parsed || {};
    var issues = (item.issues || []).join("；") || "—";
    var processText = item.process_display || "—";
    var isDup = !!item.duplicate_part_no;
    var rowClass =
      "bom-tier-" + esc(item.tier) + (isDup ? " bom-duplicate-part" : "");
    var splitBadge =
      splitCountsCache[item.sheet_name] > 1
        ? ' <span class="bom-split-tag">拆分</span>'
        : "";
    var dupBadge = isDup ? ' <span class="bom-dup-tag">料号重复</span>' : "";
    var weight = p.unit_weight_g;
    if (weight === undefined || weight === null || weight === "") weight = "";
    return (
      '<tr class="' +
      rowClass +
      '" data-index="' +
      idx +
      '">' +
      '<td class="list-td-text">' +
      fieldInput(idx, "sheet_name", item.sheet_name || "", { placeholder: "Sheet" }) +
      splitBadge +
      "</td>" +
      '<td class="list-td-text">' +
      fieldInput(idx, "customer_name", p.customer_name || "", {
        placeholder: "客户",
      }) +
      "</td>" +
      '<td class="list-td-mono">' +
      fieldInput(idx, "product_part_no", p.product_part_no || "", {
        mono: true,
        duplicatePart: isDup,
        placeholder: "料号",
      }) +
      dupBadge +
      "</td>" +
      '<td class="list-td-text">' +
      fieldInput(idx, "product_name", p.product_name || "", { placeholder: "产品名称" }) +
      "</td>" +
      "<td>" +
      fieldInput(idx, "unit_weight_g", weight, { placeholder: "g" }) +
      "</td>" +
      '<td class="list-td-text bom-process-cell">' +
      '<span class="bom-import-process-readonly" data-full-text="' +
      escAttr(processText) +
      '">' +
      esc(processText) +
      "</span>" +
      "</td>" +
      '<td class="bom-tier-cell"><span class="bom-badge ' +
      tierClass(item.tier) +
      '">' +
      esc(tierLabel(item.tier)) +
      "</span></td>" +
      '<td class="bom-import-issues list-td-text" data-full-text="' +
      escAttr(issues) +
      '">' +
      esc(issues) +
      "</td>" +
      "</tr>"
    );
  }

  function renderPreviewTable() {
    if (!body) return;
    if (!previewItems.length) {
      body.innerHTML = '<tr><td colspan="8">未解析到有效 BOM sheet</td></tr>';
      return;
    }
    body.innerHTML = previewItems
      .map(function (item, idx) {
        return renderPreviewRow(item, idx);
      })
      .join("");
    bindEllipsisTips(body);
    bindPreviewCombos(body);
  }

  function renderPreview(data) {
    previewItems = (data.items || []).map(function (item, idx) {
      var copy = Object.assign({}, item);
      copy.index = idx;
      return copy;
    });
    splitCountsCache = sheetSplitCounts(previewItems);
    if (isSingleCustomerName(data.customer_resolved)) {
      lastCustomerResolved = data.customer_resolved;
    }

    applyBatchCustomerHint(data);
    renderStats(data);
    refreshStatsFromItems();

    renderPreviewTable();
    if (previewArea) previewArea.classList.remove("is-hidden");
    if (uploadCard) uploadCard.classList.add("is-hidden");
    updateToolbar();
  }

  function mergeRevalidatedItem(idx, updated, extra) {
    if (!previewItems[idx] || !updated) return;
    previewItems[idx].tier = updated.tier;
    previewItems[idx].issues = updated.issues || [];
    previewItems[idx].parsed = updated.parsed || previewItems[idx].parsed;
    previewItems[idx].payload = updated.payload || previewItems[idx].payload;
    previewItems[idx].process_display =
      updated.process_display || previewItems[idx].process_display;
    if (updated.sheet_name) previewItems[idx].sheet_name = updated.sheet_name;
    if (extra && extra.sheet_name) previewItems[idx].sheet_name = extra.sheet_name;
    if (updated.duplicate_part_no !== undefined) {
      previewItems[idx].duplicate_part_no = !!updated.duplicate_part_no;
    }
  }

  async function syncDuplicateHints() {
    if (!previewItems.length) return;
    var payloadItems = previewItems.map(function (item, idx) {
      var row = collectRowFromDom(idx);
      var parsed = Object.assign({}, item.parsed || {}, row.fields || {});
      return {
        index: idx,
        parsed: parsed,
        tier: item.tier,
        issues: item.issues || [],
        duplicate_part_no: !!item.duplicate_part_no,
      };
    });
    var res = await fetch("/api/cost/bom-import/sync-duplicates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ items: payloadItems }),
    });
    var data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "重复料号同步失败");
    }
    (data.items || []).forEach(function (row) {
      var idx = Number(row.index);
      if (Number.isNaN(idx) || !previewItems[idx]) return;
      previewItems[idx].tier = row.tier;
      previewItems[idx].issues = row.issues || [];
      previewItems[idx].duplicate_part_no = !!row.duplicate_part_no;
      updatePreviewRowDom(idx);
    });
    bindEllipsisTips(body);
    bindPreviewCombos(body);
    refreshStatsFromItems();
  }

  function updatePreviewRowDom(idx) {
    if (!body) return;
    var tr = body.querySelector('tr[data-index="' + idx + '"]');
    if (!tr) return;
    tr.outerHTML = renderPreviewRow(previewItems[idx], idx);
    var newTr = body.querySelector('tr[data-index="' + idx + '"]');
    if (newTr) bindPreviewCombos(newTr);
  }

  async function revalidateItems(indexes, options) {
    options = options || {};
    if (!indexes.length) return;
    var payloadItems = indexes.map(function (idx) {
      return collectRowFromDom(idx);
    });
    var res = await fetch("/api/cost/bom-import/revalidate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        items: payloadItems,
        check_existing_db: !!options.checkExistingDb,
      }),
    });
    var data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "校验失败");
    }
    (data.items || []).forEach(function (updated) {
      var idx = Number(updated.index);
      if (Number.isNaN(idx)) return;
      mergeRevalidatedItem(idx, updated, payloadItems[idx]);
      updatePreviewRowDom(idx);
    });
    await syncDuplicateHints();
    bindEllipsisTips(body);
    bindPreviewCombos(body);
    refreshStatsFromItems();
    updateToolbar();
    return data;
  }

  async function applyBatchCustomer(onlyBlockedOrPending) {
    var name = batchCustomerInput && batchCustomerInput.value.trim();
    if (!name) {
      setMsg("请先在「统一客户」中填写或选择客户全称", false);
      return;
    }
    var indexes = previewItems
      .map(function (item, idx) {
        return idx;
      })
      .filter(function (idx) {
        if (!onlyBlockedOrPending) return true;
        var tier = previewItems[idx].tier;
        return tier === "blocked" || tier === "pending";
      });
    if (!indexes.length) {
      setMsg("没有需要应用的客户行", false);
      return;
    }
    indexes.forEach(function (idx) {
      var input =
        body &&
        body.querySelector(
          '.bom-import-field-input[data-index="' + idx + '"][data-field="customer_name"]'
        );
      if (input) input.value = name;
    });
    setBusy(true);
    try {
      await revalidateItems(indexes);
      lastCustomerResolved = name;
      setMsg("已应用客户「" + name + "」并重新校验 " + indexes.length + " 条", true);
    } catch (err) {
      setMsg(String(err), false);
    } finally {
      setBusy(false);
    }
  }

  async function parseFile(options) {
    options = options || {};
    var file = fileInput && fileInput.files && fileInput.files[0];
    if (!file) {
      if (!options.silent) setMsg("请先选择 Excel 文件", false);
      return false;
    }
    setBusy(true);
    if (!options.silent) {
      clearImportResult();
      clearSuccessBanner();
      setMsg("正在解析…", true);
    }
    var form = new FormData();
    form.append("file", file);
    try {
      var res = await fetch("/api/cost/bom-import/parse", {
        method: "POST",
        body: form,
        credentials: "same-origin",
      });
      var data = await res.json();
      if (!res.ok) {
        if (!options.silent) setMsg(data.error || "解析失败", false);
        return false;
      }
      renderPreview(data);
      if (!options.silent) setMsg("解析完成，请核对客户后导入", true);
      return true;
    } catch (err) {
      if (!options.silent) setMsg(String(err), false);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function commitImport(tiers) {
    var allowed = {};
    tiers.forEach(function (t) {
      allowed[t] = true;
    });
    var importable = previewItems.filter(function (p) {
      return allowed[p.tier];
    }).length;
    if (!importable) {
      setMsg("没有符合档位的记录", false);
      return;
    }
    setBusy(true);
    setMsg("正在确认客户并导入…", true);
    try {
      var allIndexes = previewItems.map(function (_, idx) {
        return idx;
      });
      await revalidateItems(allIndexes, { checkExistingDb: true });
      var items = previewItems.filter(function (p) {
        return allowed[p.tier];
      });
      if (!items.length) {
        setMsg("客户确认后没有可导入的记录，请检查阻断项", false);
        return;
      }
      var res = await fetch("/api/cost/bom-import/commit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          items: items,
          skip_supplier_check: true,
          overwrite: true,
        }),
      });
      var data = await res.json();
      if (!res.ok) {
        setMsg(data.error || "导入失败", false);
        return;
      }
      if ((data.imported || 0) > 0) {
        resetToUploadScreen(data);
      } else {
        renderImportResult(data);
        setMsg(
          data.errors && data.errors.length
            ? "导入失败，请查看下方错误说明"
            : "导入未写入任何记录",
          false
        );
      }
    } catch (err) {
      setMsg(String(err), false);
    } finally {
      setBusy(false);
    }
  }

  body?.addEventListener("change", function (e) {
    var input = e.target;
    if (!input.classList || !input.classList.contains("bom-import-field-input")) return;
    if (input.hasAttribute("readonly")) return;
    var idx = Number(input.getAttribute("data-index"));
    if (Number.isNaN(idx)) return;
    revalidateItems([idx])
      .then(function () {
        setMsg("已更新第 " + (idx + 1) + " 条并重新校验", true);
      })
      .catch(function (err) {
        setMsg(String(err), false);
      });
  });

  parseBtn?.addEventListener("click", parseFile);
  uploadBtn?.addEventListener("click", function () {
    commitImport(["passed", "pending"]);
  });
  applyAllBtn?.addEventListener("click", function () {
    applyBatchCustomer(false);
  });
  applyBlockedBtn?.addEventListener("click", function () {
    applyBatchCustomer(true);
  });
})();
