/** 供应商信息维护 */
(function () {
  let profileMap = {};
  let allRows = [];

  const SP_COLS = [{ field: "supplier", label: "供应商" }];

  const spColFilter = window.createListColFilter({
    prefix: "spColFilter",
    headSelector: "#spMaintHead",
    columns: SP_COLS,
    getCellKey(row, field) {
      if (field !== "supplier") return "(空白)";
      const raw = String(row.supplier || "").trim();
      return raw || "(空白)";
    },
    onChange(filtered, meta) {
      updateSupplierListCount(meta.shown, meta.total, meta.filtered);
      renderTable(filtered, { isFiltered: meta.filtered, totalCount: meta.total });
    },
  });

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
      throw new Error("服务器返回异常，请重启服务后 Ctrl+F5 刷新。HTTP " + res.status);
    }
    return res.json();
  }

  function updateSupplierListCount(shown, total, filtered) {
    const el = document.getElementById("spListCount");
    if (!el) return;
    if (!total) {
      el.textContent = "共 0 条";
      return;
    }
    if (filtered && shown !== total) {
      el.textContent = `显示 ${shown} / 共 ${total} 条`;
      return;
    }
    el.textContent = `共 ${total} 条`;
  }

  function refreshSupplierTable() {
    spColFilter.setRows(allRows);
    spColFilter.bindHeader();
    spColFilter.refresh();
  }

  function rowProfile(row) {
    const p = profileMap[row.supplier] || {};
    return {
      address: row.address || p.address || "",
      contact: row.contact || p.contact || "",
      phone: row.phone || p.phone || "",
      email: row.email || p.email || "",
      payment_terms: row.payment_terms || p.payment_terms || "",
      notes: row.notes || p.notes || "",
    };
  }

  function readRowInputs(tr) {
    const val = (field) => tr.querySelector(`[data-field="${field}"]`)?.value.trim() || "";
    return {
      supplier: val("supplier"),
      address: val("address"),
      contact: val("contact"),
      phone: val("phone"),
      email: val("email"),
      payment_terms: val("payment_terms"),
      notes: val("notes"),
    };
  }

  async function saveSupplierRow(oldSupplier, inputs) {
    const newName = inputs.supplier || oldSupplier;
    const profile = {
      address: inputs.address,
      contact: inputs.contact,
      phone: inputs.phone,
      email: inputs.email,
      payment_terms: inputs.payment_terms,
      notes: inputs.notes,
    };
    const body = { supplier: oldSupplier, profile };
    if (newName && newName !== oldSupplier) {
      body.new_supplier = newName;
    }
    const res = await fetch("/api/supplier-profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await parseJsonResponse(res);
    if (!res.ok) throw new Error(data.error || "供应商档案保存失败");
  }

  async function deleteSupplierRow(supplier) {
    const res = await fetch("/api/supplier-profiles/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ supplier }),
    });
    const data = await parseJsonResponse(res);
    if (!res.ok) throw new Error(data.error || "删除失败");
  }

  function rowEditableFields(tr) {
    return tr.querySelectorAll("[data-field]");
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
  }

  function setRowEditing(tr, editing) {
    tr.classList.toggle("is-editing", editing);
    tr.classList.toggle("row-editing", editing);
    rowEditableFields(tr).forEach((el) => {
      el.disabled = !editing;
    });
    tr.querySelector(".sp-edit-btn")?.classList.toggle("is-hidden", editing);
    tr.querySelector(".sp-delete-btn")?.classList.toggle("is-hidden", editing);
    tr.querySelector(".sp-save-btn")?.classList.toggle("is-hidden", !editing);
    tr.querySelector(".sp-cancel-btn")?.classList.toggle("is-hidden", !editing);
  }

  function renderTable(rows, opts) {
    const options = opts || {};
    const tbody = document.getElementById("spSupplierBody");
    if (!tbody) return;
    const totalCount = options.totalCount != null ? options.totalCount : rows.length;
    updateSupplierListCount(rows.length, totalCount, options.isFiltered);
    if (!rows.length) {
      tbody.innerHTML = options.isFiltered
        ? '<tr><td colspan="9" class="empty-cell">无匹配结果，请调整筛选条件</td></tr>'
        : '<tr><td colspan="9" class="empty-cell">暂无供应商，请在上方添加</td></tr>';
      return;
    }
    tbody.innerHTML = rows
      .map((row, idx) => {
        const p = rowProfile(row);
        const supplier = row.supplier || "";
        return `
      <tr data-supplier="${esc(supplier)}">
        <td class="list-td-seq">${idx + 1}</td>
        <td class="list-td-text sp-name-cell"><input type="text" class="dn-inline-input le" data-field="supplier" value="${esc(supplier)}" disabled /></td>
        <td class="list-td-text"><input type="text" class="dn-inline-input le" data-field="address" value="${esc(p.address)}" disabled /></td>
        <td class="list-td-text"><input type="text" class="dn-inline-input le" data-field="contact" value="${esc(p.contact)}" disabled /></td>
        <td class="list-td-text"><input type="text" class="dn-inline-input le" data-field="phone" value="${esc(p.phone)}" disabled /></td>
        <td class="list-td-text"><input type="email" class="dn-inline-input le" data-field="email" value="${esc(p.email)}" disabled /></td>
        <td class="list-td-text"><input type="text" class="dn-inline-input le" data-field="payment_terms" value="${esc(p.payment_terms)}" disabled /></td>
        <td class="list-td-text"><input type="text" class="dn-inline-input le" data-field="notes" value="${esc(p.notes)}" disabled /></td>
        <td class="action-cell sp-actions">
          <button type="button" class="btn btn-outline btn-sm sp-edit-btn">编辑</button>
          <button type="button" class="btn btn-danger btn-sm sp-delete-btn">删除</button>
          <button type="button" class="btn btn-primary btn-sm sp-save-btn is-hidden">保存</button>
          <button type="button" class="btn btn-outline btn-sm sp-cancel-btn is-hidden">取消</button>
        </td>
      </tr>`;
      })
      .join("");

    tbody.querySelectorAll("tr[data-supplier]").forEach((tr) => {
      storeRowSnapshot(tr);
      tr.querySelector(".sp-edit-btn")?.addEventListener("click", () => {
        storeRowSnapshot(tr);
        setRowEditing(tr, true);
        tr.querySelector('[data-field="supplier"]')?.focus();
      });
      tr.querySelector(".sp-cancel-btn")?.addEventListener("click", () => {
        restoreRowSnapshot(tr);
        setRowEditing(tr, false);
      });
      tr.querySelector(".sp-save-btn")?.addEventListener("click", async () => {
        const supplier = tr.dataset.supplier || "";
        const msg = document.getElementById("spMapMsg");
        const btn = tr.querySelector(".sp-save-btn");
        const inputs = readRowInputs(tr);
        if (!inputs.supplier) {
          showMsg(msg, "供应商名称不能为空", false);
          return;
        }
        if (btn) btn.disabled = true;
        try {
          await saveSupplierRow(supplier, inputs);
          storeRowSnapshot(tr);
          setRowEditing(tr, false);
          showMsg(msg, "✓ 已保存", true);
          if (window.showSaveSuccess) window.showSaveSuccess("✓ 已保存");
          await loadSupplierAdmin();
        } catch (err) {
          showMsg(msg, err.message || "保存失败", false);
          if (window.showSaveError) window.showSaveError(err.message || "保存失败");
        } finally {
          if (btn) btn.disabled = false;
        }
      });
      tr.querySelector(".sp-delete-btn")?.addEventListener("click", async () => {
        const supplier = tr.dataset.supplier || "";
        if (!supplier) return;
        if (
          !window.confirm(
            `确定删除供应商「${supplier}」？\n\n此操作不可恢复。`
          )
        ) {
          return;
        }
        const msg = document.getElementById("spMapMsg");
        const btn = tr.querySelector(".sp-delete-btn");
        if (btn) btn.disabled = true;
        try {
          await deleteSupplierRow(supplier);
          showMsg(msg, "✓ 已删除", true);
          if (window.showSaveSuccess) window.showSaveSuccess("✓ 已删除");
          await loadSupplierAdmin();
        } catch (err) {
          showMsg(msg, err.message || "删除失败", false);
          if (window.showSaveError) window.showSaveError(err.message || "删除失败");
        } finally {
          if (btn) btn.disabled = false;
        }
      });
    });
  }

  function bindNewSupplierForm() {
    const form = document.getElementById("spNewSupplierForm");
    if (!form || form.dataset.bound) return;
    form.dataset.bound = "1";

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = document.getElementById("spNewMsg");
      const name = document.getElementById("spNewName")?.value.trim() || "";
      if (!name) {
        showMsg(msg, "请填写供应商名称", false);
        return;
      }
      const profile = {
        address: document.getElementById("spNewAddress")?.value.trim() || "",
        contact: document.getElementById("spNewContact")?.value.trim() || "",
        phone: document.getElementById("spNewPhone")?.value.trim() || "",
        email: document.getElementById("spNewEmail")?.value.trim() || "",
        payment_terms: document.getElementById("spNewPaymentTerms")?.value.trim() || "",
        notes: document.getElementById("spNewNotes")?.value.trim() || "",
      };
      const btn = form.querySelector('button[type="submit"]');
      if (btn) btn.disabled = true;
      try {
        const res = await fetch("/api/supplier-profiles/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ supplier: name, profile }),
        });
        const data = await parseJsonResponse(res);
        if (!res.ok) throw new Error(data.error || "添加失败");
        form.reset();
        showMsg(msg, "✓ 已添加供应商", true);
        if (window.showSaveSuccess) window.showSaveSuccess("✓ 已添加供应商");
        await loadSupplierAdmin();
      } catch (err) {
        showMsg(msg, err.message || "添加失败", false);
        if (window.showSaveError) window.showSaveError(err.message || "添加失败");
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  }

  async function loadSupplierAdmin() {
    const res = await fetch("/api/supplier-profiles");
    const data = await parseJsonResponse(res);
    if (!res.ok) throw new Error(data.error || "加载失败");
    profileMap = {};
    allRows = data.rows || [];
    allRows.forEach((row) => {
      profileMap[row.supplier] = row;
    });
    refreshSupplierTable();
    bindNewSupplierForm();
  }

  function bindRefreshBtn() {
    const btn = document.getElementById("spRefreshBtn");
    if (!btn || btn.dataset.bound) return;
    btn.dataset.bound = "1";
    btn.addEventListener("click", () => {
      loadSupplierAdmin().catch((err) => {
        showMsg(document.getElementById("spMapMsg"), err.message || "刷新失败", false);
      });
    });
  }

  function bindClearFiltersBtn() {
    const btn = document.getElementById("spClearFiltersBtn");
    if (!btn || btn.dataset.bound) return;
    btn.dataset.bound = "1";
    btn.addEventListener("click", () => {
      spColFilter.clearAll();
    });
  }

  bindRefreshBtn();
  bindClearFiltersBtn();
  spColFilter.bindHeader();

  window.loadSupplierAdmin = loadSupplierAdmin;
})();
