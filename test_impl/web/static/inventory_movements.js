function esc(t) {
  return String(t ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString("zh-CN", { hour12: false });
  } catch (_e) {
    return iso;
  }
}

function todayYmd() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function setMsg(text, ok) {
  const el = document.getElementById("invMovMsg");
  if (!el) return;
  el.textContent = text || "";
  el.className = "msg list-msg" + (text ? (ok ? " ok" : " error") : "");
}

function formatProcessCell(code, name) {
  const c = String(code ?? "").trim();
  const n = String(name ?? "").trim();
  if (!c && !n) return "—";
  if (c && n) return `${c} ${n}`;
  return c || n;
}

let editingMovId = null;
let lastMovementItems = [];

function renderMovements(items) {
  const tbody = document.getElementById("invMovBody");
  const empty = document.getElementById("invMovEmpty");
  const count = document.getElementById("invMovCount");
  if (!tbody) return;
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="list-td-text">暂无流水记录</td></tr>`;
    if (empty) empty.hidden = false;
    if (count) count.textContent = "共 0 条";
    return;
  }
  if (empty) empty.hidden = true;
  if (count) count.textContent = `共 ${items.length} 条`;
  tbody.innerHTML = items
    .map((r) => {
      const op = r.editable
        ? `<button type="button" class="btn btn-outline btn-sm inv-mov-edit" data-id="${esc(r.id)}">修改</button>`
        : `<span class="list-td-muted">—</span>`;
      const main = `<tr data-mov-id="${esc(r.id)}">
        <td>${esc(fmtDate(r.created_at))}</td>
        <td class="list-td-text">${esc(r.customer_name || "—")}</td>
        <td class="list-td-mono">${esc(r.product_part_no)}</td>
        <td class="list-td-text">${esc(r.product_name || "—")}</td>
        <td>${esc(r.action_label || r.action_type)}</td>
        <td>${esc(r.route_display || formatProcessCell(r.process_code, r.process_name))}</td>
        <td>${esc(r.qty)}</td>
        <td class="list-td-text">${esc(r.doc_no || "—")}</td>
        <td class="list-td-text">${esc(r.note || "—")}</td>
        <td>${op}</td>
      </tr>`;
      if (editingMovId !== r.id) return main;
      return (
        main +
        `<tr class="inv-mov-edit-row"><td colspan="10">
          <form class="inv-mov-edit-form" data-id="${esc(r.id)}">
            <label class="inv-mov-edit-field"><span>数量</span>
              <input name="qty" type="number" step="0.1" min="0.1" required value="${esc(r.qty)}" /></label>
            <label class="inv-mov-edit-field"><span>备注</span>
              <input name="note" type="text" value="${esc(r.note || "")}" placeholder="可选" /></label>
            <button type="submit" class="btn btn-primary btn-sm">保存</button>
            <button type="button" class="btn btn-outline btn-sm inv-mov-cancel">取消</button>
          </form>
        </td></tr>`
      );
    })
    .join("");
  tbody.querySelectorAll(".inv-mov-edit").forEach((btn) => {
    btn.addEventListener("click", () => {
      editingMovId = Number(btn.getAttribute("data-id"));
      renderMovements(lastMovementItems);
    });
  });
  tbody.querySelectorAll(".inv-mov-cancel").forEach((btn) => {
    btn.addEventListener("click", () => {
      editingMovId = null;
      renderMovements(lastMovementItems);
    });
  });
  tbody.querySelectorAll(".inv-mov-edit-form").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = Number(form.getAttribute("data-id"));
      const qty = form.qty.value;
      const note = form.note.value.trim();
      setMsg("保存修改中…", true);
      const res = await fetch(`/api/inventory/movements/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ qty, note }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMsg(data.error || "修改失败", false);
        return;
      }
      editingMovId = null;
      setMsg("✓ 已修改出入库流水，库存已同步", true);
      await loadMovements();
    });
  });
}

async function loadMovements() {
  const form = document.getElementById("invMovForm");
  const hint = document.getElementById("invMovBomHint");
  const partInput = form?.product_part_no;
  const nameInput = form?.product_name;
  const customerInput = form?.customer_name;
  const dateInput = form?.on_date;
  let partNo = partInput?.value.trim() || "";
  const nameQ = nameInput?.value.trim() || "";
  const customerQ = customerInput?.value.trim() || "";
  const onDate = dateInput?.value.trim() || "";
  if (!partNo && nameQ && window.InventoryBomLookup) {
    partNo = await window.InventoryBomLookup.resolvePartNo(
      partInput,
      nameInput,
      hint,
      customerInput
    );
  } else if (partNo && window.InventoryBomLookup) {
    await window.InventoryBomLookup.lookupByPartNo(partInput, nameInput, hint, customerInput);
  }
  const params = new URLSearchParams();
  if (partNo) params.set("product_part_no", partNo);
  if (customerQ) params.set("customer_name", customerQ);
  if (onDate) params.set("on_date", onDate);
  params.set("limit", "500");
  const qs = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`/api/inventory/movements${qs}`);
  const data = await res.json();
  if (!res.ok) {
    setMsg(data.error || "查询失败", false);
    lastMovementItems = [];
    renderMovements([]);
    return;
  }
  setMsg("", true);
  lastMovementItems = data.items || [];
  renderMovements(lastMovementItems);
}

document.getElementById("invMovForm")?.addEventListener("submit", (e) => {
  e.preventDefault();
  loadMovements();
});

document.getElementById("invMovToday")?.addEventListener("click", () => {
  const form = document.getElementById("invMovForm");
  if (form?.on_date) form.on_date.value = todayYmd();
  loadMovements();
});

(function initBomLookup() {
  const form = document.getElementById("invMovForm");
  if (!form || !window.InventoryBomLookup) return;
  window.InventoryBomLookup.bindPair({
    partInput: form.product_part_no,
    nameInput: form.product_name,
    customerInput: form.customer_name,
    hintEl: document.getElementById("invMovBomHint"),
  });
  if (form.customer_name) {
    window.InventoryBomLookup.bindCustomer({ customerInput: form.customer_name });
  }
})();

loadMovements();
