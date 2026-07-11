/** 成本分析公共：选项加载、金额格式化、报价预览 */
window.CostCommon = (function () {
  let processes = [];
  let processOptions = [];
  let materials = [];

  function money(v) {
    const n = parseFloat(v);
    if (Number.isNaN(n)) return "¥ 0.0000";
    return (
      "¥ " +
      n.toLocaleString("zh-CN", {
        minimumFractionDigits: 4,
        maximumFractionDigits: 4,
      })
    );
  }

  function formatDate(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return iso;
      return d.toLocaleString("zh-CN", { hour12: false });
    } catch (_e) {
      return iso;
    }
  }

  async function loadOptions() {
    const res = await fetch("/api/cost/options");
    const data = await res.json();
    processes = data.processes || [];
    processOptions = data.process_options || [];
    materials = data.materials || [];
    return { processes, processOptions, materials };
  }

  function getProcessOptions() {
    return processOptions.slice();
  }

  function getProcesses() {
    return processes.slice();
  }

  function getMaterials() {
    return materials.slice();
  }

  function renderQuotePreview(container, q, labelMap) {
    if (!container || !q) return;
    const chips = Object.entries(q.process_prices || {})
      .map(([k, v]) => {
        const label = labelMap && labelMap[k] ? labelMap[k] : k;
        return `<span class="chip">${label} <b>${money(v)}</b></span>`;
      })
      .join("");

    container.innerHTML = `
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
          <span class="r-label">单件成本合计</span>
          <span class="r-value">${money(q.unit_cost || q.quote_price)}</span>
        </div>
      </div>
      ${
        chips
          ? `<div class="result-processes"><h5>已选工序</h5><div class="chip-row">${chips}</div></div>`
          : ""
      }`;
  }

  return {
    loadOptions,
    getProcesses,
    getProcessOptions,
    getMaterials,
    money,
    formatDate,
    renderQuotePreview,
  };
})();
