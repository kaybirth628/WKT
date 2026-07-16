/** 客户信息维护：客户档案 + 可选送货单（威可特统一 / 专用模板） */
(function () {
  let profileMap = {};
  let templateFiles = [];

  const RECONCILIATION_PERIOD_OPTIONS = [
    { value: "calendar_month", label: "自然月（1日～月末）" },
    { value: "month_21_20", label: "21日～次月20日" },
    { value: "month_26_25", label: "26日～次月25日" },
    { value: "month_22_21", label: "22日～次月21日" },
    { value: "month_16_15", label: "16日～次月15日" },
  ];

  function reconciliationPeriodLabel(value) {
    const hit = RECONCILIATION_PERIOD_OPTIONS.find((o) => o.value === value);
    return hit ? hit.label : value ? value : "未设置";
  }

  function reconciliationPeriodSelectHtml(value, options) {
    const opts = options || {};
    const disabled = opts.disabled ? " disabled" : "";
    const selectClass = opts.selectClass || "dn-inline-select";
    const placeholder = opts.placeholder !== false;
    const items = RECONCILIATION_PERIOD_OPTIONS.map(
      (o) =>
        `<option value="${o.value}"${value === o.value ? " selected" : ""}>${esc(o.label)}</option>`
    ).join("");
    return (
      `<select class="${selectClass}" data-field="reconciliation_period"${disabled}>` +
      (placeholder ? '<option value="">请选择对账周期</option>' : "") +
      items +
      `</select>`
    );
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function attrEsc(s) {
    return esc(s).replace(/'/g, "&#39;");
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

  function splitContactPhone(contact, phone) {
    contact = String(contact || "").trim();
    phone = String(phone || "").trim();
    if (phone) return { contact, phone };
    const m = contact.match(/(\d{7,})/);
    if (!m) return { contact, phone };
    return {
      contact: contact.slice(0, m.index).trim().replace(/[,，、]\s*$/, ""),
      phone: m[1],
    };
  }

  function deliveryEnabled(row) {
    if (typeof row.delivery_enabled === "boolean") return row.delivery_enabled;
    const p = profileMap[row.customer] || {};
    const val = String(row.delivery_enabled ?? p.delivery_enabled ?? "1").trim().toLowerCase();
    if (!val || val === "1" || val === "true" || val === "yes") return true;
    if (val === "0" || val === "false" || val === "no") return false;
    return true;
  }

  function deliveryModeFromRow(row) {
    if (!deliveryEnabled(row)) return "off";
    if (row.is_custom_excel) return "custom";
    return "wkt";
  }

  function deliveryDisplayLabel(mode, customFile) {
    if (mode === "off") return "不使用";
    if (mode === "wkt") return "威可特统一模板";
    return "专用";
  }

  function syncDeliveryDisplayStyle(display, mode) {
    if (!display) return;
    display.classList.toggle("is-custom", mode === "custom");
  }

  function updateDeliveryDisplay(tr) {
    const modeSel = tr.querySelector('[data-field="delivery_mode"]');
    const customSel = tr.querySelector('[data-field="custom_template"]');
    const display = tr.querySelector(".dn-delivery-display");
    if (!display || !modeSel) return;
    const mode = modeSel.value;
    display.textContent = deliveryDisplayLabel(mode, customSel?.value.trim() || "");
    syncDeliveryDisplayStyle(display, mode);
  }

  function customTemplateOptions(selected) {
    const files = templateFiles.length ? templateFiles : [];
    const opts = files
      .map((f) => `<option value="${attrEsc(f)}"${f === selected ? " selected" : ""}>${esc(f)}</option>`)
      .join("");
    const empty = files.length
      ? ""
      : '<option value="" disabled selected>（files/ 下暂无 .xlsx）</option>';
    return empty + opts;
  }

  function rowProfile(row) {
    const p = profileMap[row.customer] || {};
    const split = splitContactPhone(
      row.receiver_contact || p.contact || "",
      row.receiver_phone || p.phone || ""
    );
    return {
      address: row.address || row.receiver_address || p.address || "",
      contact: split.contact,
      phone: split.phone,
      email: row.email || p.email || "",
      payment_terms: row.payment_terms || p.payment_terms || "",
      reconciliation_period: row.reconciliation_period || p.reconciliation_period || "",
    };
  }

  function rowsFromConfig(data) {
    let rows = data.customer_rows || [];
    if (!rows.length && data.mapping && typeof data.mapping === "object") {
      rows = Object.keys(data.mapping)
        .sort((a, b) => a.localeCompare(b, "zh"))
        .map((customer) => ({ customer }));
    }
    return rows;
  }

  function readRowInputs(tr) {
    const val = (field) => tr.querySelector(`[data-field="${field}"]`)?.value.trim() || "";
    const address = val("address");
    const contact = val("contact");
    const phone = val("phone");
    const mode = tr.querySelector('[data-field="delivery_mode"]')?.value || "wkt";
    const customTpl = tr.querySelector('[data-field="custom_template"]')?.value.trim() || "";
    return {
      address,
      contact,
      phone,
      email: val("email"),
      payment_terms: val("payment_terms"),
      reconciliation_period: val("reconciliation_period"),
      delivery_enabled: mode === "off" ? "0" : "1",
      delivery_mode: mode,
      custom_template: customTpl,
      receiver_address: address,
      receiver_contact: contact,
      receiver_phone: phone,
    };
  }

  async function uploadCustomTemplate(customer, file) {
    const fd = new FormData();
    fd.append("customer", customer);
    fd.append("file", file);
    const res = await fetch("/api/delivery-templates/upload-for-customer", { method: "POST", body: fd });
    const data = await parseJsonResponse(res);
    if (!res.ok) throw new Error(data.error || "模板上传失败");
    return data.filename;
  }

  async function saveDeliveryTemplate(customer, mode, customFile) {
    if (mode === "off") return;
    if (mode === "wkt") {
      const res = await fetch("/api/delivery-templates/mapping", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer }),
      });
      const data = await parseJsonResponse(res);
      if (!res.ok) throw new Error(data.error || "送货单模板保存失败");
      return;
    }
    if (mode === "custom") {
      if (!customFile) throw new Error("请上传专用 Excel 模板");
      const res = await fetch("/api/delivery-templates/mapping", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer, template: customFile }),
      });
      const data = await parseJsonResponse(res);
      if (!res.ok) throw new Error(data.error || "专用模板保存失败");
    }
  }

  async function saveCustomerRow(customer, inputs) {
    const profileRes = await fetch("/api/customer-profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer,
        profile: {
          address: inputs.address,
          contact: inputs.contact,
          phone: inputs.phone,
          email: inputs.email,
          payment_terms: inputs.payment_terms,
          reconciliation_period: inputs.reconciliation_period,
          delivery_enabled: inputs.delivery_enabled,
        },
      }),
    });
    const profileData = await parseJsonResponse(profileRes);
    if (!profileRes.ok) throw new Error(profileData.error || "客户档案保存失败");

    await saveDeliveryTemplate(customer, inputs.delivery_mode, inputs.custom_template);

    if (inputs.delivery_mode !== "off") {
      const deliveryRes = await fetch("/api/delivery-templates/customer-info", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer,
          info: {
            receiver_address: inputs.receiver_address,
            receiver_contact: inputs.receiver_contact,
            receiver_phone: inputs.receiver_phone,
          },
        }),
      });
      const deliveryData = await parseJsonResponse(deliveryRes);
      if (!deliveryRes.ok) throw new Error(deliveryData.error || "送货信息保存失败");
    }
  }

  async function deleteCustomerRow(customer) {
    const res = await fetch("/api/customer-profiles/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer }),
    });
    const data = await parseJsonResponse(res);
    if (!res.ok) throw new Error(data.error || "删除失败");
  }

  function rowEditableFields(tr) {
    return tr.querySelectorAll("[data-field]:not([data-field='template_upload'])");
  }

  function storeRowSnapshot(tr) {
    const snap = {};
    rowEditableFields(tr).forEach((el) => {
      snap[el.dataset.field || ""] = el.value;
    });
    tr.dataset.snapshot = JSON.stringify(snap);
  }

  function restoreRowSnapshot(tr) {
    try {
      const snap = JSON.parse(tr.dataset.snapshot || "{}");
      rowEditableFields(tr).forEach((el) => {
        const key = el.dataset.field || "";
        if (Object.prototype.hasOwnProperty.call(snap, key)) {
          el.value = snap[key];
        }
      });
    } catch {
      /* ignore */
    }
    syncRowDeliveryUi(tr);
    syncRowPeriodUi(tr);
  }

  function syncRowDeliveryUi(tr) {
    const modeSel = tr.querySelector('[data-field="delivery_mode"]');
    const customSel = tr.querySelector('[data-field="custom_template"]');
    const uploadWrap = tr.querySelector("[data-role='custom-upload']");
    const previewBtn = tr.querySelector(".dn-preview-row-btn");
    if (!modeSel) return;
    const mode = modeSel.value;
    if (customSel) {
      customSel.classList.toggle("is-hidden", true);
    }
    if (uploadWrap) {
      uploadWrap.classList.toggle("is-hidden", mode !== "custom");
    }
    if (previewBtn) {
      previewBtn.disabled = mode === "off";
      previewBtn.title = mode === "off" ? "该客户未启用送货单" : "";
    }
    updateDeliveryDisplay(tr);
  }

  function syncRowPeriodUi(tr) {
    const sel = tr.querySelector('[data-field="reconciliation_period"]');
    const display = tr.querySelector(".dn-period-display");
    if (display && sel) {
      display.textContent = reconciliationPeriodLabel(sel.value);
    }
  }

  function setRowEditing(tr, editing) {
    tr.classList.toggle("is-editing", editing);
    tr.classList.toggle("row-editing", editing);
    tr.querySelector(".dn-delivery-edit")?.classList.toggle("is-hidden", !editing);
    tr.querySelector(".dn-delivery-display")?.classList.toggle("is-hidden", editing);
    tr.querySelector(".dn-period-edit")?.classList.toggle("is-hidden", !editing);
    tr.querySelector(".dn-period-display")?.classList.toggle("is-hidden", editing);
    rowEditableFields(tr).forEach((el) => {
      el.disabled = !editing;
    });
    const btn = tr.querySelector(".dn-edit-row-btn");
    if (btn) {
      btn.textContent = editing ? "保存" : "编辑";
      btn.classList.toggle("btn-primary", editing);
      btn.classList.toggle("btn-outline", !editing);
    }
    tr.querySelector(".dn-delete-row-btn")?.classList.toggle("is-hidden", editing);
    syncRowDeliveryUi(tr);
  }

  function exitOtherEditingRows(activeTr) {
    document.querySelectorAll("#dnCustomerBody tr.is-editing").forEach((tr) => {
      if (tr === activeTr) return;
      restoreRowSnapshot(tr);
      setRowEditing(tr, false);
    });
  }

  function bindDeliveryModeSelect(tr) {
    const modeSel = tr.querySelector('[data-field="delivery_mode"]');
    if (!modeSel) return;
    modeSel.addEventListener("change", () => syncRowDeliveryUi(tr));
    syncRowDeliveryUi(tr);
  }

  function renderCustomerTable(data) {
    const tbody = document.getElementById("dnCustomerBody");
    if (!tbody) return;
    const rows = rowsFromConfig(data);
    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="9" class="empty-cell">暂无客户。请使用上方「新增客户」录入，或在「订单录入」中创建订单时自动带出客户。</td></tr>';
      return;
    }
    tbody.innerHTML = rows
      .map((row) => {
        const mode = deliveryModeFromRow(row);
        const p = rowProfile(row);
        const customSelected = row.template_file || "";
        return `<tr data-customer="${esc(row.customer)}">
              <td class="list-td-text dn-cell-name">${esc(row.customer)}</td>
              <td class="list-td-text dn-cell-delivery">
                <span class="dn-delivery-display${mode === "custom" ? " is-custom" : ""}">${esc(deliveryDisplayLabel(mode, customSelected))}</span>
                <div class="dn-delivery-edit is-hidden">
                  <select class="dn-inline-select le" data-field="delivery_mode">
                    <option value="off"${mode === "off" ? " selected" : ""}>不使用</option>
                    <option value="wkt"${mode === "wkt" ? " selected" : ""}>威可特统一模板</option>
                    <option value="custom"${mode === "custom" ? " selected" : ""}>专用模板</option>
                  </select>
                  <select class="dn-inline-select dn-custom-tpl-select le is-hidden" data-field="custom_template">${customTemplateOptions(customSelected)}</select>
                  <label class="dn-upload-label${mode === "custom" ? "" : " is-hidden"}" data-role="custom-upload">上传 Excel
                    <input type="file" data-field="template_upload" accept=".xlsx,.xlsm" />
                  </label>
                </div>
              </td>
              <td class="list-td-text"><input type="text" class="dn-inline-input le" data-field="address" value="${attrEsc(p.address)}" placeholder="地址" /></td>
              <td class="list-td-text"><input type="text" class="dn-inline-input le" data-field="contact" value="${attrEsc(p.contact)}" placeholder="联系人" /></td>
              <td class="list-td-text"><input type="text" class="dn-inline-input le" data-field="phone" value="${attrEsc(p.phone)}" placeholder="电话" /></td>
              <td class="list-td-text"><input type="email" class="dn-inline-input le" data-field="email" value="${attrEsc(p.email)}" placeholder="邮箱" /></td>
              <td class="list-td-text"><input type="text" class="dn-inline-input le" data-field="payment_terms" value="${attrEsc(p.payment_terms)}" placeholder="账期" /></td>
              <td class="list-td-text dn-cell-period">
                <span class="dn-period-display">${esc(reconciliationPeriodLabel(p.reconciliation_period))}</span>
                <div class="dn-period-edit is-hidden">${reconciliationPeriodSelectHtml(p.reconciliation_period, { selectClass: "dn-inline-select le" })}</div>
              </td>
              <td class="action-cell dn-cell-actions">
                <button type="button" class="btn btn-sm btn-outline dn-edit-row-btn" data-customer="${esc(row.customer)}">编辑</button>
                <button type="button" class="btn btn-sm btn-outline dn-preview-row-btn" data-customer="${esc(row.customer)}"${mode === "off" ? " disabled" : ""}>预览</button>
                <button type="button" class="btn btn-sm btn-danger dn-delete-row-btn" data-customer="${esc(row.customer)}">删除</button>
              </td>
            </tr>`;
      })
      .join("");

    const msg = document.getElementById("dnMapMsg");

    tbody.querySelectorAll("tr").forEach((tr) => {
      bindDeliveryModeSelect(tr);
      rowEditableFields(tr).forEach((el) => {
        el.disabled = true;
      });
      storeRowSnapshot(tr);
      setRowEditing(tr, false);
    });

    tbody.querySelectorAll(".dn-edit-row-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const customer = btn.dataset.customer || "";
        const tr = btn.closest("tr");
        if (!customer || !tr) return;

        if (!tr.classList.contains("is-editing")) {
          exitOtherEditingRows(tr);
          setRowEditing(tr, true);
          tr.querySelector('[data-field="address"]')?.focus();
          return;
        }

        btn.disabled = true;
        try {
          const inputs = readRowInputs(tr);
          if (inputs.delivery_mode === "custom") {
            const uploadInp = tr.querySelector('[data-field="template_upload"]');
            if (uploadInp?.files?.[0]) {
              inputs.custom_template = await uploadCustomTemplate(customer, uploadInp.files[0]);
            } else if (!inputs.custom_template) {
              throw new Error("请上传专用 Excel 模板");
            }
          }
          await saveCustomerRow(customer, inputs);
          storeRowSnapshot(tr);
          setRowEditing(tr, false);
          showMsg(msg, "✓ 已保存", true);
          if (window.showSaveSuccess) window.showSaveSuccess("✓ 已保存");
          profileMap[customer] = {
            ...(profileMap[customer] || {}),
            address: inputs.address,
            contact: inputs.contact,
            phone: inputs.phone,
            email: inputs.email,
            payment_terms: inputs.payment_terms,
            reconciliation_period: inputs.reconciliation_period,
            delivery_enabled: inputs.delivery_enabled,
          };
          syncRowPeriodUi(tr);
        } catch (err) {
          showMsg(msg, err.message || "保存失败", false);
          if (window.showSaveError) window.showSaveError(err.message || "保存失败");
        } finally {
          btn.disabled = false;
        }
      });
    });

    tbody.querySelectorAll(".dn-preview-row-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.disabled) return;
        loadDeliveryNotePreview(btn.dataset.customer || "");
      });
    });

    tbody.querySelectorAll(".dn-delete-row-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const customer = btn.dataset.customer || "";
        if (!customer) return;
        const tr = btn.closest("tr");
        if (tr?.classList.contains("is-editing")) return;
        if (
          !window.confirm(
            `确定删除客户「${customer}」？\n\n将同时删除客户档案与送货单配置。已有订单的客户无法删除。`
          )
        ) {
          return;
        }
        btn.disabled = true;
        try {
          await deleteCustomerRow(customer);
          showMsg(msg, "✓ 已删除", true);
          if (window.showSaveSuccess) window.showSaveSuccess("✓ 已删除");
          await loadDeliveryNoteAdmin();
        } catch (err) {
          showMsg(msg, err.message || "删除失败", false);
          if (window.showSaveError) window.showSaveError(err.message || "删除失败");
        } finally {
          btn.disabled = false;
        }
      });
    });
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

      if (data.is_custom_excel) {
        frame?.classList.add("is-hidden");
        if (frame) frame.src = "about:blank";
        if (download && data.preview_download_url) {
          download.href = data.preview_download_url;
          download.textContent = "下载预览（已自动填入示例）";
          download.classList.remove("is-hidden");
        }
        if (openTab) openTab.classList.add("is-hidden");
        const fields = (data.placeholder_fields || []).slice(0, 8).join("、");
        setStatus(
          fields
            ? `模板单元格写 {{占位符}}，如：${fields}… 出货时自动替换`
            : "模板单元格写 {{占位符}}，出货时自动填入订单数据"
        );
      } else {
        if (download && data.preview_download_url) {
          download.href = data.preview_download_url;
          download.textContent = "下载 Excel";
          download.classList.remove("is-hidden");
        }
        const htmlUrl = (data.preview_html_url || "") + "&embed=1";
        if (openTab) {
          openTab.href = data.preview_html_url;
          openTab.classList.remove("is-hidden");
        }
        if (frame && htmlUrl) {
          frame.classList.remove("is-hidden");
          frame.src = htmlUrl;
        }
        setStatus("✓ 已加载送货单预览");
      }
      document.getElementById("dnPreviewSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      setStatus("");
      empty?.classList.remove("is-hidden");
      if (empty) empty.textContent = "预览失败：" + (err.message || "网络错误");
      alert("预览失败：" + (err.message || "请检查网页服务是否已重启"));
    }
  }

  function fillTemplateSelects() {
    /* 专用模板改为直接上传，不再依赖下拉列表 */
  }

  function bindNewCustomerForm() {
    const form = document.getElementById("dnNewCustomerForm");
    const modeSel = document.getElementById("dnNewDeliveryMode");
    const customWrap = document.getElementById("dnNewCustomUploadWrap");
    if (!form || form.dataset.bound) return;
    form.dataset.bound = "1";

    function syncNewDeliveryUi() {
      const mode = modeSel?.value || "wkt";
      customWrap?.classList.toggle("is-hidden", mode !== "custom");
    }
    modeSel?.addEventListener("change", syncNewDeliveryUi);
    syncNewDeliveryUi();

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = document.getElementById("dnNewMsg");
      const name = document.getElementById("dnNewName")?.value.trim() || "";
      if (!name) {
        showMsg(msg, "请填写客户名称", false);
        return;
      }
      const mode = modeSel?.value || "wkt";
      const period = document.getElementById("dnNewReconcilePeriod")?.value.trim() || "";
      if (!period) {
        showMsg(msg, "请选择对账周期", false);
        return;
      }
      const uploadInp = document.getElementById("dnNewCustomUpload");
      const profile = {
        address: document.getElementById("dnNewAddress")?.value.trim() || "",
        contact: document.getElementById("dnNewContact")?.value.trim() || "",
        phone: document.getElementById("dnNewPhone")?.value.trim() || "",
        email: document.getElementById("dnNewEmail")?.value.trim() || "",
        payment_terms: document.getElementById("dnNewPaymentTerms")?.value.trim() || "",
        reconciliation_period: period,
        delivery_enabled: mode === "off" ? "0" : "1",
      };
      const btn = form.querySelector('button[type="submit"]');
      if (btn) btn.disabled = true;
      try {
        const res = await fetch("/api/customer-profiles/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ customer: name, profile }),
        });
        const data = await parseJsonResponse(res);
        if (!res.ok) throw new Error(data.error || "添加失败");
        let customTpl = "";
        if (mode === "custom") {
          if (!uploadInp?.files?.[0]) throw new Error("请上传专用 Excel 模板");
          customTpl = await uploadCustomTemplate(name, uploadInp.files[0]);
        }
        await saveDeliveryTemplate(name, mode, customTpl);
        if (mode !== "off") {
          await fetch("/api/delivery-templates/customer-info", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              customer: name,
              info: {
                receiver_address: profile.address,
                receiver_contact: profile.contact,
                receiver_phone: profile.phone,
              },
            }),
          });
        }
        form.reset();
        if (modeSel) modeSel.value = "wkt";
        syncNewDeliveryUi();
        showMsg(msg, "✓ 已添加客户", true);
        if (window.showSaveSuccess) window.showSaveSuccess("✓ 已添加客户");
        await loadDeliveryNoteAdmin();
      } catch (err) {
        showMsg(msg, err.message || "添加失败", false);
        if (window.showSaveError) window.showSaveError(err.message || "添加失败");
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  }

  async function loadDeliveryNoteAdmin() {
    const res = await fetch("/api/delivery-templates");
    const data = await parseJsonResponse(res);
    profileMap = data.customer_profiles || {};
    templateFiles = data.template_files || [];
    fillTemplateSelects();
    renderCustomerTable(data);
  }

  function bindDeliveryNoteAdmin() {
    bindNewCustomerForm();
    const refreshBtn = document.getElementById("dnRefreshBtn");
    if (refreshBtn && !refreshBtn.dataset.bound) {
      refreshBtn.dataset.bound = "1";
      refreshBtn.addEventListener("click", () => {
        showMsg(document.getElementById("dnMapMsg"), "", true);
        loadDeliveryNoteAdmin().catch((e) => {
          showMsg(document.getElementById("dnMapMsg"), e.message || "刷新失败", false);
        });
      });
    }
  }

  bindDeliveryNoteAdmin();
  window.loadDeliveryNoteAdmin = loadDeliveryNoteAdmin;
  window.bindDeliveryNoteAdmin = bindDeliveryNoteAdmin;
  window.loadDeliveryNotePreview = loadDeliveryNotePreview;
})();
