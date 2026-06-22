/** 客户信息维护：公司全称、地址、联系人、账期、对账周期等 */
(function () {
  const FIELDS = [
    { id: "ciCompanyFullName", key: "company_full_name", label: "公司全称" },
    { id: "ciAddress", key: "address", label: "地址" },
    { id: "ciContact", key: "contact", label: "联系人" },
    { id: "ciPhone", key: "phone", label: "电话" },
    { id: "ciEmail", key: "email", label: "邮箱" },
    { id: "ciPaymentTerms", key: "payment_terms", label: "账期" },
    { id: "ciReconciliationCycle", key: "reconciliation_cycle", label: "对账周期" },
  ];

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

  async function parseJsonResponse(res) {
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (!ct.includes("application/json")) {
      throw new Error("服务器返回异常，请重启服务后 Ctrl+F5 刷新。");
    }
    return res.json();
  }

  function readFormProfile() {
    const profile = {};
    FIELDS.forEach((f) => {
      const el = document.getElementById(f.id);
      profile[f.key] = el ? String(el.value || "").trim() : "";
    });
    return profile;
  }

  function fillFormProfile(profile) {
    FIELDS.forEach((f) => {
      const el = document.getElementById(f.id);
      if (el) el.value = (profile && profile[f.key]) || "";
    });
  }

  async function loadCustomerProfileFields(customer) {
    if (!customer) {
      fillFormProfile({});
      return;
    }
    const res = await fetch(
      "/api/customer-profiles/detail?customer=" + encodeURIComponent(customer)
    );
    const data = await parseJsonResponse(res);
    if (!res.ok) throw new Error(data.error || "加载失败");
    fillFormProfile(data.profile || {});
  }

  function renderCustomerTable(rows) {
    const tbody = document.getElementById("ciCustomerBody");
    if (!tbody) return;
    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="8" class="empty-cell">暂无客户。请先在「订单录入」创建客户。</td></tr>';
      return;
    }
    tbody.innerHTML = rows
      .map((row) => {
        const cells = [
          esc(row.customer),
          esc(row.company_full_name || "—"),
          esc(row.contact || "—"),
          esc(row.phone || "—"),
          esc(row.payment_terms || "—"),
          esc(row.reconciliation_cycle || "—"),
        ];
        return `<tr data-customer="${esc(row.customer)}">
          ${cells.map((c) => `<td>${c}</td>`).join("")}
          <td>
            <button type="button" class="btn btn-sm btn-outline ci-edit-btn" data-customer="${esc(row.customer)}">编辑</button>
          </td>
        </tr>`;
      })
      .join("");

    tbody.querySelectorAll(".ci-edit-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const customer = btn.dataset.customer || "";
        const sel = document.getElementById("ciMapCustomer");
        if (sel) sel.value = customer;
        await loadCustomerProfileFields(customer);
        document.getElementById("ciInfoForm")?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  async function fillCustomerSelect(rows, keepValue) {
    const sel = document.getElementById("ciMapCustomer");
    if (!sel) return;
    const prev = keepValue != null ? keepValue : sel.value;
    sel.innerHTML = '<option value="">请选择客户</option>';
    rows.forEach((row) => {
      sel.appendChild(new Option(row.customer, row.customer));
    });
    if (prev && [...sel.options].some((o) => o.value === prev)) sel.value = prev;
  }

  async function loadReconcileHint() {
    const hint = document.getElementById("ciReconcileHint");
    if (!hint) return;
    try {
      const res = await fetch("/api/reconciliation/config");
      const data = await res.json();
      if (res.ok && data.terms_display) {
        hint.textContent = `对账周期示例：${data.terms_display}（可按客户单独填写）`;
      }
    } catch (e) {
      hint.textContent = "对账周期示例：月结90天·每月25日对账";
    }
  }

  async function loadCustomerInfoAdmin() {
    const msg = document.getElementById("ciMapMsg");
    showMsg(msg, "", true);
    await loadReconcileHint();
    const res = await fetch("/api/customer-profiles");
    const data = await parseJsonResponse(res);
    if (!res.ok) {
      showMsg(msg, data.error || "加载失败", false);
      return;
    }
    const rows = Array.isArray(data.rows) ? data.rows : [];
    const sel = document.getElementById("ciMapCustomer");
    await fillCustomerSelect(rows, sel ? sel.value : "");
    renderCustomerTable(rows);
    if (sel && sel.value) await loadCustomerProfileFields(sel.value);
  }

  function bindCustomerInfoAdmin() {
    const form = document.getElementById("ciInfoForm");
    const sel = document.getElementById("ciMapCustomer");
    const refreshBtn = document.getElementById("ciRefreshBtn");

    sel?.addEventListener("change", () => {
      loadCustomerProfileFields(sel.value).catch((e) => {
        showMsg(document.getElementById("ciMapMsg"), e.message || "加载失败", false);
      });
    });

    form?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = document.getElementById("ciMapMsg");
      const customer = sel?.value || "";
      if (!customer) {
        showMsg(msg, "请选择客户", false);
        return;
      }
      try {
        const res = await fetch("/api/customer-profiles", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ customer, profile: readFormProfile() }),
        });
        const data = await parseJsonResponse(res);
        if (!res.ok) throw new Error(data.error || "保存失败");
        showMsg(msg, "✓ 已保存", true);
        await loadCustomerInfoAdmin();
        if (sel) sel.value = customer;
        await loadCustomerProfileFields(customer);
      } catch (err) {
        showMsg(msg, err.message || "保存失败", false);
      }
    });

    refreshBtn?.addEventListener("click", () => {
      loadCustomerInfoAdmin().catch((e) => {
        showMsg(document.getElementById("ciMapMsg"), e.message || "刷新失败", false);
      });
    });
  }

  bindCustomerInfoAdmin();
  window.loadCustomerInfoAdmin = loadCustomerInfoAdmin;
})();
