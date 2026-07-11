let records = [];
let processOptions = [];
let editingRecordId = null;
let detailRecordId = null;

function renderTable(items) {
  const tbody = document.getElementById("costQueryBody");
  const empty = document.getElementById("costQueryEmpty");
  if (!tbody) return;

  if (!items.length) {
    tbody.innerHTML = "";
    if (empty) empty.hidden = false;
    return;
  }
  if (empty) empty.hidden = true;

  tbody.innerHTML = items
    .map(
      (r) => `
    <tr data-id="${r.id}" tabindex="0">
      <td>${r.customer_name}</td>
      <td>${r.product_name}</td>
      <td>${r.product_part_no}</td>
      <td>${r.material}</td>
      <td>${r.unit_weight_g}</td>
      <td>${r.machine_tonnage}</td>
      <td>${(r.process_selections || r.selected_processes || []).length}</td>
      <td>${CostCommon.money(r.unit_cost)}</td>
      <td>${CostCommon.formatDate(r.created_at)}</td>
      <td class="cost-query-actions">
        <button type="button" class="btn btn-ghost btn-sm" data-action="edit" data-id="${r.id}">修改</button>
        <button type="button" class="btn btn-danger btn-sm" data-action="delete" data-id="${r.id}">删除</button>
      </td>
    </tr>`
    )
    .join("");

  tbody.querySelectorAll("tr[data-id]").forEach((row) => {
    row.addEventListener("click", (e) => {
      if (e.target.closest("[data-action]")) return;
      openDetail(Number(row.dataset.id));
    });
    row.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        if (e.target.closest("[data-action]")) return;
        e.preventDefault();
        openDetail(Number(row.dataset.id));
      }
    });
  });

  tbody.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = Number(btn.dataset.id);
      if (btn.dataset.action === "edit") openEdit(id);
      if (btn.dataset.action === "delete") deleteRecord(id);
    });
  });
}

function openDetail(id) {
  detailRecordId = id;
  const record = records.find((r) => r.id === id);
  if (!record) return;
  const modal = document.getElementById("costDetailModal");
  const body = document.getElementById("costDetailBody");
  const chips = (record.process_selections || [])
    .map((item) => {
      const label = `${item.code} ${item.name}`;
      return `<span class="chip">${label} <b>${CostCommon.money(item.price)}</b></span>`;
    })
    .join("");

  body.innerHTML = `
    <div class="cost-detail-grid">
      <div><span class="detail-label">客户名称</span><span>${record.customer_name}</span></div>
      <div><span class="detail-label">产品名称</span><span>${record.product_name}</span></div>
      <div><span class="detail-label">模具编号</span><span>${record.mold_no}</span></div>
      <div><span class="detail-label">产品料号</span><span>${record.product_part_no}</span></div>
      <div><span class="detail-label">模穴</span><span>${record.cavity}</span></div>
      <div><span class="detail-label">产品单重</span><span>${record.unit_weight_g} g</span></div>
      <div><span class="detail-label">材质</span><span>${record.material}</span></div>
      <div><span class="detail-label">机台吨位</span><span>${record.machine_tonnage}</span></div>
    </div>
    <div class="result-grid cost-detail-costs">
      <div class="result-row">
        <span class="r-label">原材成本</span>
        <span class="r-value">${CostCommon.money(record.material_cost)}</span>
      </div>
      <div class="result-row">
        <span class="r-label">工艺合计</span>
        <span class="r-value">${CostCommon.money(record.process_total)}</span>
      </div>
      <div class="result-row grand">
        <span class="r-label">单件成本</span>
        <span class="r-value">${CostCommon.money(record.unit_cost)}</span>
      </div>
    </div>
    <div class="result-processes">
      <h5>已选工序（${(record.process_selections || record.selected_processes || []).length}）</h5>
      <div class="chip-row">${chips || "—"}</div>
    </div>
    <p class="detail-meta">录入时间：${CostCommon.formatDate(record.created_at)}</p>`;

  modal.hidden = false;
}

function closeDetail() {
  document.getElementById("costDetailModal").hidden = true;
  detailRecordId = null;
}

function renderEditProcessGrid(selectedByCode) {
  const grid = document.getElementById("editProcessGrid");
  if (!grid) return;
  grid.innerHTML = processOptions
    .map((p) => {
      const checked = selectedByCode && selectedByCode[p.code] != null;
      const price = checked ? selectedByCode[p.code] : "";
      return `
    <label class="process-pick-item">
      <span class="process-pick-head">
        <input type="checkbox" class="process-pick" data-process-code="${p.code}" data-process="${p.name}"${checked ? " checked" : ""} />
        <span class="process-code">${p.code}</span>
        <span class="process-name" title="${p.name}">${p.name}</span>
      </span>
      <input class="process-price" data-process-code="${p.code}" type="number" step="0.0001" min="0" placeholder="单价（可选）"${checked ? "" : " disabled"} value="${price !== "0" ? price : ""}" />
    </label>`;
    })
    .join("");

  grid.querySelectorAll(".process-pick").forEach((cb) => {
    cb.addEventListener("change", () => {
      const code = cb.dataset.processCode;
      const priceInput = grid.querySelector(`input.process-price[data-process-code="${code}"]`);
      if (!priceInput) return;
      priceInput.disabled = !cb.checked;
      if (!cb.checked) priceInput.value = "";
    });
  });
}

function collectEditProcessPrices() {
  const byCode = {};
  document.querySelectorAll("#editProcessGrid .process-pick:checked").forEach((cb) => {
    const code = cb.dataset.processCode;
    const inp = document.querySelector(`#editProcessGrid input.process-price[data-process-code="${code}"]`);
    byCode[code] = inp && inp.value !== "" ? inp.value : "0";
  });
  return byCode;
}

function openEdit(id) {
  const record = records.find((r) => r.id === id);
  if (!record) return;
  editingRecordId = id;
  closeDetail();

  const form = document.getElementById("costEditForm");
  form.customer_name.value = record.customer_name;
  form.product_name.value = record.product_name;
  form.mold_no.value = record.mold_no;
  form.product_part_no.value = record.product_part_no;
  form.cavity.value = record.cavity;
  form.unit_weight_g.value = record.unit_weight_g;
  form.material.value = record.material;
  form.machine_tonnage.value = record.machine_tonnage;
  form.material_unit_price.value = record.material_unit_price || "0";

  renderEditProcessGrid(record.process_prices || {});
  document.getElementById("costEditMsg").textContent = "";
  document.getElementById("costEditModal").hidden = false;
}

function closeEdit() {
  document.getElementById("costEditModal").hidden = true;
  editingRecordId = null;
}

async function saveEdit(e) {
  e.preventDefault();
  if (!editingRecordId) return;
  const form = document.getElementById("costEditForm");
  const msg = document.getElementById("costEditMsg");
  const processPrices = collectEditProcessPrices();
  if (!Object.keys(processPrices).length) {
    msg.textContent = "请至少选择一道工序";
    msg.className = "msg error";
    return;
  }

  const payload = {
    customer_name: form.customer_name.value.trim(),
    product_name: form.product_name.value.trim(),
    mold_no: form.mold_no.value.trim(),
    product_part_no: form.product_part_no.value.trim(),
    cavity: form.cavity.value.trim(),
    unit_weight_g: form.unit_weight_g.value.trim(),
    material: form.material.value.trim(),
    machine_tonnage: form.machine_tonnage.value.trim(),
    material_unit_price: form.material_unit_price.value || "0",
    process_prices: processPrices,
  };

  const res = await fetch(`/api/cost/records/${editingRecordId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    msg.textContent = data.error || "保存失败";
    msg.className = "msg error";
    return;
  }

  closeEdit();
  await loadRecords();
}

async function deleteRecord(id) {
  const record = records.find((r) => r.id === id);
  const label = record ? `${record.product_part_no}（${record.customer_name}）` : `#${id}`;
  if (!window.confirm(`确定删除成本记录 ${label}？此操作不可恢复。`)) return;

  const res = await fetch(`/api/cost/records/${id}`, { method: "DELETE" });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "删除失败");
    return;
  }
  if (detailRecordId === id) closeDetail();
  if (editingRecordId === id) closeEdit();
  await loadRecords();
}

async function loadRecords() {
  const form = document.getElementById("costQueryForm");
  const params = new URLSearchParams();
  const q = form.q.value.trim();
  const customer = form.customer.value.trim();
  const productPartNo = form.product_part_no.value.trim();
  if (q) params.set("q", q);
  if (customer) params.set("customer", customer);
  if (productPartNo) params.set("product_part_no", productPartNo);

  const res = await fetch("/api/cost/records?" + params.toString());
  const data = await res.json();
  records = data.records || [];
  document.getElementById("costQueryCount").textContent = `共 ${data.total || 0} 条`;
  renderTable(records);
}

document.getElementById("costQueryForm").addEventListener("submit", (e) => {
  e.preventDefault();
  loadRecords();
});

document.getElementById("costQueryReset").addEventListener("click", () => {
  document.getElementById("costQueryForm").reset();
  loadRecords();
});

document.getElementById("costDetailClose").addEventListener("click", closeDetail);
document.getElementById("costDetailEdit").addEventListener("click", () => {
  if (detailRecordId) openEdit(detailRecordId);
});
document.getElementById("costDetailDelete").addEventListener("click", () => {
  if (detailRecordId) deleteRecord(detailRecordId);
});
document.getElementById("costDetailModal").addEventListener("click", (e) => {
  if (e.target.id === "costDetailModal") closeDetail();
});

document.getElementById("costEditClose").addEventListener("click", closeEdit);
document.getElementById("costEditCancel").addEventListener("click", closeEdit);
document.getElementById("costEditForm").addEventListener("submit", saveEdit);
document.getElementById("costEditModal").addEventListener("click", (e) => {
  if (e.target.id === "costEditModal") closeEdit();
});

document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  closeDetail();
  closeEdit();
});

CostCommon.loadOptions().then(({ processOptions: opts, materials }) => {
  processOptions = opts || [];
  const list = document.getElementById("editMaterialOptions");
  if (list) {
    list.innerHTML = (materials || []).map((m) => `<option value="${m}"></option>`).join("");
  }
  loadRecords();
});
