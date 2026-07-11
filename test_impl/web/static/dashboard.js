/** 订单首页 · 可视化分析 */
(function () {
  const CHART_COLORS = {
    primary: "#024ad8",
    success: "#1aae39",
    warning: "#b45309",
    danger: "#b3262b",
    muted: "#636363",
    soft: "#c9e0fc",
  };

  let chartJsPromise = null;
  let charts = {};
  let lastPayload = null;

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtNum(v) {
    const n = Number(String(v || "").replace(/,/g, ""));
    if (Number.isNaN(n)) return String(v || "0");
    return n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  }

  function ensureChartJs() {
    if (window.Chart) return Promise.resolve(window.Chart);
    if (chartJsPromise) return chartJsPromise;
    chartJsPromise = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js";
      s.async = true;
      s.onload = () => resolve(window.Chart);
      s.onerror = () => reject(new Error("Chart.js 加载失败"));
      document.head.appendChild(s);
    });
    return chartJsPromise;
  }

  function destroyCharts() {
    Object.values(charts).forEach((c) => {
      try {
        c.destroy();
      } catch {
        /* ignore */
      }
    });
    charts = {};
  }

  function renderKpis(kpis) {
    const el = document.getElementById("dashKpis");
    if (!el || !kpis) return;
    const cards = [
      { label: "订单行总数", value: kpis.total_lines, cls: "is-primary" },
      { label: "未结行数", value: kpis.open_lines, sub: `未结数量 ${fmtNum(kpis.open_qty)}` },
      { label: "未结金额", value: fmtNum(kpis.open_amount), cls: "is-primary", sub: "含税 PO×单价" },
      { label: "正常结案", value: kpis.closed_lines },
      { label: "强制结案", value: kpis.forced_closed_lines, cls: kpis.forced_closed_lines ? "is-muted" : "" },
      { label: "出货记录", value: kpis.shipment_events, sub: `本月 ${kpis.shipments_this_month} 笔` },
      { label: "活跃客户", value: kpis.customers },
      {
        label: "交期预警",
        value: kpis.overdue_lines,
        cls: kpis.overdue_lines ? "is-danger" : "",
        sub: `10 天内到期 ${kpis.due_soon_lines} 行`,
      },
    ];
    el.innerHTML = cards
      .map(
        (c) =>
          `<div class="dash-kpi ${c.cls || ""}">` +
          `<div class="dash-kpi-label">${esc(c.label)}</div>` +
          `<div class="dash-kpi-value">${esc(String(c.value ?? 0))}</div>` +
          (c.sub ? `<div class="dash-kpi-sub">${esc(c.sub)}</div>` : "") +
          `</div>`
      )
      .join("");
  }

  function baseChartOptions(extra) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
      },
      ...extra,
    };
  }

  async function renderCharts(data) {
    const Chart = await ensureChartJs();
    destroyCharts();

    const status = data.status_distribution || [];
    const statusCtx = document.getElementById("dashChartStatus");
    if (statusCtx && status.length) {
      charts.status = new Chart(statusCtx, {
        type: "doughnut",
        data: {
          labels: status.map((x) => x.label),
          datasets: [
            {
              data: status.map((x) => x.count),
              backgroundColor: [CHART_COLORS.primary, CHART_COLORS.success, CHART_COLORS.muted],
              borderWidth: 1,
            },
          ],
        },
        options: baseChartOptions(),
      });
    }

    const top = data.top_open_customers || [];
    const topCtx = document.getElementById("dashChartTopCustomers");
    if (topCtx) {
      charts.topCustomers = new Chart(topCtx, {
        type: "bar",
        data: {
          labels: top.map((x) => x.customer),
          datasets: [
            {
              label: "未结数量",
              data: top.map((x) => Number(String(x.open_qty).replace(/,/g, "")) || 0),
              backgroundColor: CHART_COLORS.primary,
              borderRadius: 4,
            },
          ],
        },
        options: baseChartOptions({
          scales: {
            x: { ticks: { maxRotation: 45, minRotation: 0, font: { size: 10 } } },
            y: { beginAtZero: true },
          },
        }),
      });
    }

    const monthly = data.monthly_shipments || [];
    const monthCtx = document.getElementById("dashChartMonthly");
    if (monthCtx) {
      charts.monthly = new Chart(monthCtx, {
        type: "line",
        data: {
          labels: monthly.map((x) => x.label),
          datasets: [
            {
              label: "出货笔数",
              data: monthly.map((x) => x.count),
              borderColor: CHART_COLORS.primary,
              backgroundColor: "rgba(2, 74, 216, 0.12)",
              fill: true,
              tension: 0.25,
            },
          ],
        },
        options: baseChartOptions({
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        }),
      });
    }

    const sources = data.shipment_sources || [];
    const srcCtx = document.getElementById("dashChartSources");
    if (srcCtx && sources.length) {
      charts.sources = new Chart(srcCtx, {
        type: "bar",
        data: {
          labels: sources.map((x) => x.label),
          datasets: [
            {
              label: "记录数",
              data: sources.map((x) => x.count),
              backgroundColor: [CHART_COLORS.primary, CHART_COLORS.warning],
              borderRadius: 4,
            },
          ],
        },
        options: baseChartOptions({
          indexAxis: "y",
          scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
        }),
      });
    }
  }

  function setUpdatedAt(iso) {
    const el = document.getElementById("dashUpdatedAt");
    if (!el) return;
    if (!iso) {
      el.textContent = "";
      return;
    }
    const d = new Date(iso);
    el.textContent = Number.isNaN(d.getTime()) ? "" : `更新于 ${d.toLocaleString("zh-CN")}`;
  }

  function showDashMsg(text, ok) {
    const el = document.getElementById("dashMsg");
    if (!el) return;
    el.textContent = text || "";
    el.className = "msg " + (ok ? "ok" : "error");
  }

  async function loadOrderDashboard(force) {
    if (!force && lastPayload) return lastPayload;
    showDashMsg("正在加载分析数据…", true);
    const res = await fetch("/api/dashboard/overview");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "加载失败");
    lastPayload = data;
    renderKpis(data.kpis);
    setUpdatedAt(data.generated_at);
    await renderCharts(data);
    showDashMsg("", true);
    return data;
  }

  function bindDashboardUi() {
    const btn = document.getElementById("dashRefreshBtn");
    if (btn && !btn.dataset.bound) {
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        lastPayload = null;
        loadOrderDashboard(true).catch((err) => showDashMsg(err.message || "刷新失败", false));
      });
    }
    document.querySelectorAll("[data-dash-link]").forEach((el) => {
      if (el.dataset.bound) return;
      el.dataset.bound = "1";
      el.addEventListener("click", (e) => {
        e.preventDefault();
        const key = el.dataset.dashLink;
        if (key && typeof window.switchSubmodule === "function") {
          window.switchSubmodule(key);
        }
      });
    });
  }

  bindDashboardUi();
  window.loadOrderDashboard = loadOrderDashboard;
})();
