/** 送货单维护：客户档案 + 送货收货信息（合并原客户信息维护） */
(function () {
  let profileMap = {};

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
      reconciliation_cycle: row.reconciliation_cycle || p.reconciliation_cycle || "",
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
    return {
      address,
      contact,
      phone,
      email: val("email"),
      payment_terms: val("payment_terms"),
      reconciliation_cycle: val("reconciliation_cycle"),
      receiver_address: address,
      receiver_contact: contact,
      receiver_phone: phone,
    };
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
          reconciliation_cycle: inputs.reconciliation_cycle,
        },
      }),
    });
    const profileData = await parseJsonResponse(profileRes);
    if (!profileRes.ok) throw new Error(profileData.error || "客户档案保存失败");

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

  function renderCustomerTable(data) {
    const tbody = document.getElementById("dnCustomerBody");
    if (!tbody) return;
    const rows = rowsFromConfig(data);
    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="9" class="empty-cell">暂无客户。请先在「订单录入」创建客户。</td></tr>';
      return;
    }
    tbody.innerHTML = rows
      .map((row) => {
        const tpl = esc(row.template_display || (row.is_wkt_standard ? "威可特统一模板" : row.template || "—"));
        const tplCls = row.template_missing ? " dn-badge-warn" : row.is_custom_excel ? " dn-badge-excel" : " dn-badge-default";
        const p = rowProfile(row);
        return `<tr data-customer="${esc(row.customer)}">
              <td class="dn-cell-name">${esc(row.customer)}</td>
              <td><span class="dn-badge${tplCls}">${tpl}</span></td>
              <td><input type="text" class="dn-inline-input" data-field="address" value="${attrEsc(p.address)}" placeholder="地址" /></td>
              <td><input type="text" class="dn-inline-input" data-field="contact" value="${attrEsc(p.contact)}" placeholder="联系人" /></td>
              <td><input type="text" class="dn-inline-input" data-field="phone" value="${attrEsc(p.phone)}" placeholder="电话" /></td>
              <td><input type="email" class="dn-inline-input" data-field="email" value="${attrEsc(p.email)}" placeholder="邮箱" /></td>
              <td><input type="text" class="dn-inline-input" data-field="payment_terms" value="${attrEsc(p.payment_terms)}" placeholder="账期" /></td>
              <td><input type="text" class="dn-inline-input" data-field="reconciliation_cycle" value="${attrEsc(p.reconciliation_cycle)}" placeholder="对账周期" /></td>
              <td class="dn-cell-actions">
                <button type="button" class="btn btn-sm btn-primary dn-save-row-btn" data-customer="${esc(row.customer)}">保存</button>
                <button type="button" class="btn btn-sm btn-outline dn-preview-row-btn" data-customer="${esc(row.customer)}">预览</button>
              </td>
            </tr>`;
      })
      .join("");

    const msg = document.getElementById("dnMapMsg");

    tbody.querySelectorAll(".dn-save-row-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const customer = btn.dataset.customer || "";
        const tr = btn.closest("tr");
        if (!customer || !tr) return;
        btn.disabled = true;
        try {
          await saveCustomerRow(customer, readRowInputs(tr));
          showMsg(msg, "✓ 已保存", true);
          if (window.showSaveSuccess) window.showSaveSuccess("✓ 已保存");
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
        loadDeliveryNotePreview(btn.dataset.customer || "");
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

      if (download && data.preview_download_url) {
        download.href = data.preview_download_url;
        download.classList.remove("is-hidden");
      }
      const htmlUrl =
        data.is_custom_excel && !data.preview_html_url
          ? `/delivery-note/preview-sample?customer=${encodeURIComponent(customer)}&embed=1`
          : (data.preview_html_url || "") + "&embed=1";
      if (openTab) {
        openTab.href = data.is_custom_excel && !data.preview_html_url
          ? `/delivery-note/preview-sample?customer=${encodeURIComponent(customer)}`
          : data.preview_html_url;
      }
      if (frame && htmlUrl) {
        frame.classList.remove("is-hidden");
        frame.src = htmlUrl;
      }
      setStatus(data.template_missing ? "专用模板文件待放入 files/" : "✓ 已加载送货单预览");
      document.getElementById("dnPreviewSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      setStatus("");
      empty?.classList.remove("is-hidden");
      if (empty) empty.textContent = "预览失败：" + (err.message || "网络错误");
      alert("预览失败：" + (err.message || "请检查网页服务是否已重启"));
    }
  }

  async function loadReconcileHint() {
    const hint = document.getElementById("dnMaintHint");
    if (!hint) return;
    const base =
      "维护客户地址、联系人、电话、邮箱、账期、对账周期及送货收货信息；编辑后点「保存」，地址与联系人同步用于送货单。";
    try {
      const res = await fetch("/api/reconciliation/config");
      const data = await res.json();
      if (res.ok && data.terms_display) {
        hint.textContent = `${base} 对账周期示例：${data.terms_display}`;
      } else {
        hint.textContent = base;
      }
    } catch {
      hint.textContent = base;
    }
  }

  async function loadDeliveryNoteAdmin() {
    await loadReconcileHint();
    const res = await fetch("/api/delivery-templates");
    const data = await parseJsonResponse(res);
    profileMap = data.customer_profiles || {};
    renderCustomerTable(data);
  }

  function bindDeliveryNoteAdmin() {
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
