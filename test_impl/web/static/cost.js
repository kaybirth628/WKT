let PROCESSES = [];

async function loadOptions() {
  const res = await fetch("/api/cost/options");
  const data = await res.json();
  PROCESSES = data.processes;

  const sel = document.getElementById("materialSelect");
  sel.innerHTML = data.materials
    .map((m) => `<option value="${m}">${m}</option>`)
    .join("");

  const grid = document.getElementById("processGrid");
  grid.innerHTML = PROCESSES.map(
    (p) => `
    <label class="process-item">
      <span>${p}</span>
      <input data-process="${p}" type="number" step="0.0001" min="0" placeholder="0" />
    </label>`
  ).join("");

  grid.querySelectorAll("input[data-process]").forEach((inp) => {
    inp.addEventListener("input", () => {
      inp.classList.toggle("filled", inp.value !== "" && parseFloat(inp.value) > 0);
    });
  });
}

function collectProcessPrices() {
  const prices = {};
  document.querySelectorAll("#processGrid input[data-process]").forEach((inp) => {
    if (inp.value !== "" && parseFloat(inp.value) > 0) {
      prices[inp.dataset.process] = inp.value;
    }
  });
  return prices;
}

// 成本/报价为单件（单价）口径，统一 4 位小数 + 千分位
function money(v) {
  return "¥ " + parseFloat(v).toLocaleString("zh-CN", {
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  });
}

function renderResult(q) {
  const card = document.getElementById("resultCard");
  const body = document.getElementById("resultBody");
  const chips = Object.entries(q.process_prices)
    .map(([k, v]) => `<span class="chip">${k} <b>${money(v)}</b></span>`)
    .join("");

  body.innerHTML = `
    <div class="result-grid">
      <div class="result-row">
        <span class="r-label">原材（${q.material_code}）成本　单价 ${money(q.material_unit_price)} × 重量 ${q.material_weight}</span>
        <span class="r-value">${money(q.material_cost)}</span>
      </div>
      <div class="result-row">
        <span class="r-label">工艺合计</span>
        <span class="r-value">${money(q.process_total)}</span>
      </div>
      <div class="result-row grand">
        <span class="r-label">客户报价（单件成本合计）</span>
        <span class="r-value">${money(q.quote_price)}</span>
      </div>
    </div>
    ${
      chips
        ? `<div class="result-processes"><h5>已计入工艺</h5><div class="chip-row">${chips}</div></div>`
        : ""
    }`;
  card.hidden = false;
}

document.getElementById("costForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const msg = document.getElementById("costMsg");
  const body = {
    material_code: form.material_code.value,
    material_unit_price: form.material_unit_price.value || "0",
    material_weight: form.material_weight.value || "0",
    process_prices: collectProcessPrices(),
  };
  const res = await fetch("/api/cost/quote", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    msg.textContent = data.error || "生成失败";
    msg.className = "msg error";
    return;
  }
  msg.textContent = "";
  renderResult(data);
});

loadOptions();
