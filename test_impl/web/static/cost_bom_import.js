(function () {
  var previewItems = [];
  var fileInput = document.getElementById("bomImportFile");
  var parseBtn = document.getElementById("bomImportParseBtn");
  var passedBtn = document.getElementById("bomImportPassedBtn");
  var pendingBtn = document.getElementById("bomImportPendingBtn");
  var body = document.getElementById("bomImportBody");
  var previewArea = document.getElementById("bomImportPreviewArea");
  var summary = document.getElementById("bomImportSummary");
  var msg = document.getElementById("bomImportMsg");
  var customerEl = document.getElementById("bomImportCustomer");
  var statsEl = document.getElementById("bomImportStats");

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
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
      if (passedBtn) passedBtn.disabled = true;
      if (pendingBtn) pendingBtn.disabled = true;
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

  function updateToolbar() {
    var passed = previewItems.filter(function (p) {
      return p.tier === "passed";
    }).length;
    var importable = previewItems.filter(function (p) {
      return p.tier === "passed" || p.tier === "pending";
    }).length;
    if (passedBtn) passedBtn.disabled = passed === 0;
    if (pendingBtn) pendingBtn.disabled = importable === 0;
  }

  function renderCustomer(data) {
    if (!customerEl) return;
    if (data.customer_resolved) {
      customerEl.className = "verify-summary verify-ok";
      customerEl.innerHTML =
        "<strong>客户匹配</strong> 文件名「" +
        esc(data.customer_hint || "") +
        "」→ " +
        esc(data.customer_resolved);
      return;
    }
    if (data.customer_error) {
      customerEl.className = "verify-summary verify-warn";
      customerEl.innerHTML = "<strong>客户未匹配</strong> " + esc(data.customer_error);
      return;
    }
    customerEl.className = "verify-summary";
    customerEl.textContent = "";
  }

  function renderStats(data) {
    if (!statsEl) return;
    statsEl.innerHTML =
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
  }

  function renderPreview(data) {
    previewItems = data.items || [];
    var splitCounts = sheetSplitCounts(previewItems);

    renderCustomer(data);
    renderStats(data);

    if (summary) {
      var splitSheets = Object.keys(splitCounts).filter(function (k) {
        return splitCounts[k] > 1;
      }).length;
      var splitHint =
        splitSheets > 0
          ? " 其中 " + splitSheets + " 个 Sheet 已拆成多条。"
          : "";
      summary.textContent =
        "请核对「产品料号」是否为 Excel 料号栏。" +
        splitHint +
        (data.blocked > 0
          ? " 阻断项需修正后再导入。"
          : " 建议使用「导入通过+待核」一次性写入。");
    }

    if (!body) return;
    if (!previewItems.length) {
      body.innerHTML = '<tr><td colspan="8">未解析到有效 BOM sheet</td></tr>';
      if (previewArea) previewArea.classList.remove("is-hidden");
      updateToolbar();
      return;
    }

    body.innerHTML = previewItems
      .map(function (item) {
        var p = item.parsed || {};
        var issues = (item.issues || []).join("；");
        var sheet = esc(item.sheet_name);
        var splitBadge =
          splitCounts[item.sheet_name] > 1
            ? ' <span class="bom-split-tag">拆分</span>'
            : "";
        return (
          '<tr class="bom-tier-' +
          esc(item.tier) +
          '">' +
          "<td>" +
          sheet +
          splitBadge +
          "</td>" +
          "<td>" +
          esc(p.customer_name) +
          "</td>" +
          '<td class="bom-part-cell"><code>' +
          esc(p.product_part_no) +
          "</code></td>" +
          "<td>" +
          esc(p.product_name) +
          "</td>" +
          "<td>" +
          esc(p.unit_weight_g || "—") +
          "</td>" +
          '<td class="bom-process-cell">' +
          esc(item.process_display || "—") +
          "</td>" +
          '<td><span class="bom-badge ' +
          tierClass(item.tier) +
          '">' +
          esc(tierLabel(item.tier)) +
          "</span></td>" +
          '<td class="bom-import-issues">' +
          esc(issues || "—") +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
    if (previewArea) previewArea.classList.remove("is-hidden");
    updateToolbar();
  }

  async function parseFile() {
    var file = fileInput && fileInput.files && fileInput.files[0];
    if (!file) {
      setMsg("请先选择 Excel 文件", false);
      return;
    }
    setBusy(true);
    setMsg("正在解析…", true);
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
        setMsg(data.error || "解析失败", false);
        return;
      }
      renderPreview(data);
      setMsg("解析完成，请核对后导入", true);
    } catch (err) {
      setMsg(String(err), false);
    } finally {
      setBusy(false);
    }
  }

  async function commitImport(tiers) {
    var allowed = {};
    tiers.forEach(function (t) {
      allowed[t] = true;
    });
    var items = previewItems.filter(function (p) {
      return allowed[p.tier];
    });
    if (!items.length) {
      setMsg("没有符合档位的记录", false);
      return;
    }
    setBusy(true);
    setMsg("正在导入 " + items.length + " 条…", true);
    try {
      var res = await fetch("/api/cost/bom-import/commit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          items: items,
          skip_supplier_check: true,
        }),
      });
      var data = await res.json();
      if (!res.ok) {
        setMsg(data.error || "导入失败", false);
        return;
      }
      var errText =
        data.errors && data.errors.length
          ? "；失败 " + data.errors.length + " 条"
          : "";
      setMsg(
        "成功导入 " + (data.imported || 0) + " 条" + errText,
        !data.errors || !data.errors.length
      );
      if (data.imported > 0) {
        await parseFile();
      }
    } catch (err) {
      setMsg(String(err), false);
    } finally {
      setBusy(false);
    }
  }

  parseBtn?.addEventListener("click", parseFile);
  passedBtn?.addEventListener("click", function () {
    commitImport(["passed"]);
  });
  pendingBtn?.addEventListener("click", function () {
    commitImport(["passed", "pending"]);
  });
})();
