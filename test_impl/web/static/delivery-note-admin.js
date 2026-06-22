/** 送货单维护：统一版式 + 客户一览行内上传专用 Excel */
(function () {
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showMsg(el, text, ok) {
    if (!el) return;
    el.textContent = text;
    el.className = "msg dn-msg " + (ok ? "ok" : "error");
  }

  function setStatus(text) {
    const el = document.getElementById("dnPreviewStatus");
    if (el) el.textContent = text || "";
  }

  async function parseJsonResponse(res) {
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (!ct.includes("application/json")) {
      if (res.status === 404) {
        throw new Error("接口不存在（404）。请关闭旧网页窗口后，双击「一键启动网页.bat」重启服务，再 Ctrl+F5 刷新。");
      }
      throw new Error(
        "服务器返回了网页而不是数据（可能未重启）。请重启「一键启动网页.bat」后 Ctrl+F5 刷新。HTTP " +
          res.status
      );
    }
    return res.json();
  }

  function rowsFromConfig(data) {
    return data.customer_rows || [];
  }

  function templateCellHtml(row) {
    const customer = esc(row.customer);
    const isStd = row.is_wkt_standard !== false && !row.is_custom_excel;
    let tag;
    if (isStd) {
      tag = '<span class="dn-tpl-tag dn-tpl-tag--std">统一</span>';
    } else if (row.template_missing) {
      tag = '<span class="dn-tpl-tag dn-tpl-tag--warn">待上传</span>';
    } else {
      const fn = esc(row.template_file || "专用");
      tag = `<span class="dn-tpl-tag dn-tpl-tag--custom" title="${fn}">专用</span>`;
    }
    const resetBtn =
      row.is_custom_excel && !row.is_wkt_standard
        ? `<button type="button" class="btn btn-sm btn-link dn-reset-tpl-btn" data-customer="${customer}">恢复统一</button>`
        : "";
    return `<div class="dn-tpl-cell">
      ${tag}
      <label class="btn btn-sm btn-outline dn-upload-inline" title="上传该客户专用 Excel（.xlsx）">
        上传<input type="file" class="dn-row-upload-input" accept=".xlsx,.xlsm" data-customer="${customer}" hidden />
      </label>
      ${resetBtn}
    </div>`;
  }

  async function uploadTemplateForCustomer(customer, file) {
    const msg = document.getElementById("dnUploadMsg");
    if (!customer || !file) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("customer", customer);
    showMsg(msg, "正在上传…", true);
    const res = await fetch("/api/delivery-templates/upload", { method: "POST", body: fd });
    const data = await parseJsonResponse(res);
    if (!res.ok) {
      showMsg(msg, data.error || "上传失败", false);
      return;
    }
    showMsg(msg, "✓ 已上传并绑定：" + customer + " · " + data.filename, true);
    await loadDeliveryNoteAdmin();
    loadDeliveryNotePreview(customer);
  }

  async function resetTemplateForCustomer(customer) {
    const msg = document.getElementById("dnUploadMsg");
    if (!customer) return;
    if (!confirm("确定恢复为威可特统一送货单？")) return;
    const res = await fetch("/api/delivery-templates/mapping", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer }),
    });
    const data = await parseJsonResponse(res);
    showMsg(msg, res.ok ? "✓ 已恢复统一模板" : data.error || "操作失败", res.ok);
    if (res.ok) {
      await loadDeliveryNoteAdmin();
      loadDeliveryNotePreview(customer);
    }
  }

  async function loadCustomerInfoFields(customer) {
    const addr = document.getElementById("dnReceiverAddress");
    const contact = document.getElementById("dnReceiverContact");
    const prefix = document.getElementById("dnDocPrefix");
    if (!customer) {
      if (addr) addr.value = "";
      if (contact) contact.value = "";
      if (prefix) prefix.value = "";
      return;
    }
    const res = await fetch(
      "/api/delivery-templates/customer-info?customer=" + encodeURIComponent(customer)
    );
    const data = await parseJsonResponse(res);
    const info = res.ok ? data.info || {} : {};
    if (addr) addr.value = info.receiver_address || "";
    if (contact) contact.value = info.receiver_contact || "";
    if (prefix) prefix.value = info.doc_no_prefix || "";
  }

  function bindCustomerTableEvents() {
    const tbody = document.getElementById("dnCustomerBody");
    if (!tbody || tbody.dataset.bound) return;
    tbody.dataset.bound = "1";

    tbody.addEventListener("change", (e) => {
      const input = e.target.closest(".dn-row-upload-input");
      if (!input?.files?.[0]) return;
      const customer = input.dataset.customer || "";
      uploadTemplateForCustomer(customer, input.files[0]).finally(() => {
        input.value = "";
      });
    });

    tbody.addEventListener("click", (e) => {
      const resetBtn = e.target.closest(".dn-reset-tpl-btn");
      if (resetBtn) {
        e.preventDefault();
        resetTemplateForCustomer(resetBtn.dataset.customer || "");
        return;
      }
      const editBtn = e.target.closest(".dn-edit-btn");
      if (editBtn) {
        const customer = editBtn.dataset.customer || "";
        const cust = document.getElementById("dnMapCustomer");
        if (cust) cust.value = customer;
        loadCustomerInfoFields(customer);
        document.getElementById("dnInfoForm")?.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      const previewBtn = e.target.closest(".dn-preview-row-btn");
      if (previewBtn) {
        const customer = previewBtn.dataset.customer || "";
        const cust = document.getElementById("dnMapCustomer");
        if (cust) cust.value = customer;
        loadDeliveryNotePreview(customer);
      }
    });
  }

  function renderCustomerTable(data) {
    const tbody = document.getElementById("dnCustomerBody");
    if (!tbody) return;
    const rows = rowsFromConfig(data);
    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="6" class="empty-cell">暂无客户。请先在「订单录入」创建客户。</td></tr>';
      return;
    }
    tbody.innerHTML = rows
      .map((row) => {
        const addr = esc(row.receiver_address || "—");
        const contact = esc(row.receiver_contact || "—");
        const prefix = esc(row.doc_no_prefix || "WKT");
        return `<tr data-customer="${esc(row.customer)}">
              <td>${esc(row.customer)}</td>
              <td>${addr}</td>
              <td>${contact}</td>
              <td>${prefix}</td>
              <td>${templateCellHtml(row)}</td>
              <td>
                <button type="button" class="btn btn-sm btn-outline dn-edit-btn" data-customer="${esc(row.customer)}">编辑</button>
                <button type="button" class="btn btn-sm btn-primary dn-preview-row-btn" data-customer="${esc(row.customer)}">预览</button>
              </td>
            </tr>`;
      })
      .join("");
  }

  async function fillDnCustomerSelect(data, keepValue) {
    const sel = document.getElementById("dnMapCustomer");
    if (!sel) return;
    const prev = keepValue != null ? keepValue : sel.value;
    const names = new Set();
    try {
      const mres = await fetch("/api/master");
      const master = await mres.json();
      (master.customers || []).forEach((c) => {
        const n = typeof c === "string" ? c : c?.name;
        if (n && String(n).trim()) names.add(String(n).trim());
      });
    } catch {
      /* ignore */
    }
    rowsFromConfig(data).forEach((r) => {
      if (r.customer) names.add(String(r.customer).trim());
    });
    const sorted = [...names].sort((a, b) => a.localeCompare(b, "zh"));
    sel.innerHTML =
      '<option value="">请选择客户</option>' +
      sorted.map((n) => `<option value="${esc(n)}">${esc(n)}</option>`).join("");
    if (prev && sorted.includes(prev)) sel.value = prev;
  }

  async function loadDeliveryNotePreview(customer) {
    const empty = document.getElementById("dnPreviewEmpty");
    const frame = document.getElementById("dnPreviewFrame");
    const actions = document.getElementById("dnPreviewActions");
    const label = document.getElementById("dnPreviewTemplateLabel");
    const openTab = document.getElementById("dnPreviewOpenTab");
    const download = document.getElementById("dnPreviewDownload");

    customer = String(customer || "").trim();
    if (!customer) {
      setStatus("");
      empty?.classList.remove("is-hidden");
      frame?.classList.add("is-hidden");
      actions?.classList.add("is-hidden");
      if (frame) frame.src = "about:blank";
      return;
    }

    setStatus("正在生成预览…");
    empty?.classList.add("is-hidden");
    actions?.classList.add("is-hidden");
    frame?.classList.add("is-hidden");

    try {
      const res = await fetch(
        "/api/delivery-templates/preview?customer=" + encodeURIComponent(customer)
      );
      const data = await parseJsonResponse(res);
      if (!res.ok) {
        setStatus("");
        empty?.classList.remove("is-hidden");
        if (empty) empty.textContent = data.error || "无法预览，请重启网页服务后重试";
        alert(data.error || "无法预览");
        return;
      }

      actions?.classList.remove("is-hidden");
      const tplLabel = data.template_label || (data.is_wkt_standard ? "威可特统一送货单" : "专用 Excel 模板");
      if (label) label.textContent = `${customer} · ${tplLabel}`;

      if (download && data.preview_download_url) {
        download.href = data.preview_download_url;
        download.classList.remove("is-hidden");
        download.textContent = data.is_wkt_standard ? "下载 Excel 示例" : "下载专用模板示例";
      }

      if (data.is_wkt_standard && data.preview_html_url) {
        if (openTab) {
          openTab.href = data.preview_html_url;
          openTab.classList.remove("is-hidden");
        }
        if (frame) {
          frame.classList.remove("is-hidden");
          frame.src = data.preview_html_url + "&embed=1";
        }
      } else {
        if (openTab) openTab.classList.add("is-hidden");
        if (frame) {
          frame.classList.add("is-hidden");
          frame.src = "about:blank";
        }
      }

      setStatus(data.template_missing ? "专用模板文件待上传" : "✓ 已加载送货单预览（示例数据）");
      document.getElementById("dnPreviewSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      setStatus("");
      empty?.classList.remove("is-hidden");
      if (empty) empty.textContent = "预览失败：" + (err.message || "网络错误");
      alert("预览失败：" + (err.message || "请检查网页服务是否已重启"));
    }
  }

  async function loadDeliveryNoteAdmin() {
    const selBefore = document.getElementById("dnMapCustomer")?.value;
    const res = await fetch("/api/delivery-templates");
    const data = await parseJsonResponse(res);
    await fillDnCustomerSelect(data, selBefore);
    const help = document.getElementById("dnPlaceholderHelp");
    if (help) {
      const lines = [...(data.placeholder_help || []), ...(data.custom_placeholder_help || [])];
      help.innerHTML = lines.map((h) => `<div>${esc(h)}</div>`).join("");
    }
    const sup = document.getElementById("dnSupplierInfo");
    if (sup && data.supplier) {
      const s = data.supplier;
      sup.textContent = `供应商：${s.supplier_name || ""} · ${s.supplier_address || ""} · ${s.supplier_phone || ""}`;
    }
    renderCustomerTable(data);
    if (selBefore) await loadCustomerInfoFields(selBefore);
  }

  function bindDeliveryNoteAdmin() {
    bindCustomerTableEvents();

    const infoForm = document.getElementById("dnInfoForm");
    if (infoForm && !infoForm.dataset.bound) {
      infoForm.dataset.bound = "1";
      infoForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const msg = document.getElementById("dnMapMsg");
        const customer = document.getElementById("dnMapCustomer")?.value.trim();
        if (!customer) {
          showMsg(msg, "请选择客户", false);
          return;
        }
        const info = {
          receiver_address: document.getElementById("dnReceiverAddress")?.value.trim() || "",
          receiver_contact: document.getElementById("dnReceiverContact")?.value.trim() || "",
          doc_no_prefix: document.getElementById("dnDocPrefix")?.value.trim() || "",
        };
        const res = await fetch("/api/delivery-templates/customer-info", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ customer, info }),
        });
        const data = await res.json();
        showMsg(msg, res.ok ? "✓ 已保存收货信息" : data.error || "保存失败", res.ok);
        if (res.ok) {
          await loadDeliveryNoteAdmin();
          loadDeliveryNotePreview(customer);
        }
      });
    }
    const refreshBtn = document.getElementById("dnRefreshBtn");
    if (refreshBtn && !refreshBtn.dataset.bound) {
      refreshBtn.dataset.bound = "1";
      refreshBtn.addEventListener("click", () => loadDeliveryNoteAdmin());
    }
    const previewBtn = document.getElementById("dnPreviewBtn");
    if (previewBtn && !previewBtn.dataset.bound) {
      previewBtn.dataset.bound = "1";
      previewBtn.addEventListener("click", () => {
        const customer = document.getElementById("dnMapCustomer")?.value.trim();
        if (!customer) {
          alert("请先选择客户");
          return;
        }
        loadDeliveryNotePreview(customer);
      });
    }
    const custSel = document.getElementById("dnMapCustomer");
    if (custSel && !custSel.dataset.infoBound) {
      custSel.dataset.infoBound = "1";
      custSel.addEventListener("change", () => {
        loadCustomerInfoFields(custSel.value.trim());
      });
    }
  }

  window.loadDeliveryNoteAdmin = loadDeliveryNoteAdmin;
  window.bindDeliveryNoteAdmin = bindDeliveryNoteAdmin;
  window.loadDeliveryNotePreview = loadDeliveryNotePreview;
})();
