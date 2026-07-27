/* ========== 功能开关（后续要恢复改为 true 即可） ========== */
const FEATURE_EXCEL_IMPORT = false;
/** 出货明细子模块（已出货记录列表） */
const FEATURE_SHIPPED_MODULE = true;
/** 未结订单：同一客户多料号合并出货 */
const FEATURE_BATCH_SHIP = true;
/** 订单首页可视化（数据量不足时可先关闭） */
const FEATURE_HOME_DASHBOARD = false;
/** AI 数据助手（暂时不用时可关闭） */
const FEATURE_AI_ASSISTANT = false;

/** 未结订单：接单日期超过该月数则高亮 */
const OPEN_ORDER_STALE_MONTHS = 6;
/** 未结订单：距客户交期 ≤ 该天数时黄色预警 */
const OPEN_DELIVERY_WARN_DAYS = 10;

(function patchFetchAuth() {
  const rawFetch = window.fetch.bind(window);
  window.fetch = async function (input, init) {
    const res = await rawFetch(input, init);
    if (res.status === 401) {
      const url = typeof input === "string" ? input : (input && input.url) || "";
      if (!url.includes("/api/auth/login")) {
        location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search + location.hash);
      }
    }
    return res;
  };
})();

/* ========== 附件2 字段定义 ========== */
const COLS = [
  { f: "customer", label: "客户", type: "text" },
  { f: "order_date", label: "接单日期", type: "date" },
  { f: "delivery_date", label: "客户交期", type: "date" },
  { f: "order_no", label: "订单号", type: "text" },
  { f: "product_spec", label: "品名规格", type: "text" },
  { f: "customer_part_no", label: "客户料号", type: "text" },
  { f: "unit_weight_g", label: "单重（不含损耗）g", type: "text" },
  { f: "material", label: "材质", type: "text" },
  { f: "po_qty", label: "PO数量", type: "decimal", dp: 1 },
  { f: "shipped_qty", label: "已出货", type: "decimal", dp: 1 },
  { f: "open_qty", label: "未结数量", type: "readonly" },
  { f: "unit", label: "单位", type: "text" },
  { f: "tax_rate", label: "税率", type: "tax" },
  { f: "rmb_tax_incl_price", label: "人民币单价（含税）", type: "decimal", dp: 4 },
  { f: "amount", label: "金额（含税）", type: "amount", dp: 2 },
  { f: "payment_terms", label: "账期", type: "text" },
];

/** 订单明细列表列（在客户交期后增加系统录入时间，不参与 OCR/Excel/手动表单） */
const LIST_DETAIL_COLS = (() => {
  const idx = COLS.findIndex((c) => c.f === "delivery_date");
  const entryTimeCol = { f: "created_at", label: "录入时间", type: "datetime" };
  return [...COLS.slice(0, idx + 1), entryTimeCol, ...COLS.slice(idx + 1)];
})();

/** 出货明细专用列（每条 = 一次出货登记或一条导入记录） */
const SHIPMENT_LIST_COLS = [
  { f: "customer", label: "客户", type: "text" },
  { f: "delivery_doc_no", label: "送货单号", type: "text" },
  { f: "order_no", label: "订单号", type: "text" },
  { f: "order_date", label: "接单日期", type: "date" },
  { f: "shipped_at", label: "出货时间", type: "datetime" },
  { f: "customer_part_no", label: "客户料号", type: "text" },
  { f: "product_spec", label: "品名规格", type: "text" },
  { f: "ship_qty", label: "本次出货", type: "decimal", dp: 1 },
  { f: "open_qty_after", label: "出货后未结", type: "decimal", dp: 1 },
  { f: "shipped_qty_after", label: "累计已出货", type: "decimal", dp: 1 },
];

const LIST_CLOSED_EXTRA_COLS = [
  { f: "last_shipped_at", label: "出货时间", type: "datetime" },
  { f: "last_delivery_doc_no", label: "出货单号", type: "text" },
];

const LIST_DETAIL_COL_WEIGHTS = [
  1.25, 1.0, 1.0, 1.15, 1.35, 2.1, 1.15, 0.7, 0.65, 0.75, 0.7, 0.7, 0.65, 0.65, 0.85, 0.85, 0.85,
];

const LIST_CLOSED_EXTRA_WEIGHTS = [1.15, 1.25];

const LIST_SHIPMENT_COL_WEIGHTS = [
  1.15, 1.25, 1.35, 1.05, 1.2, 1.15, 2.1, 0.85, 0.85, 0.85,
];

/** 对账明细列：客户→出货→订单→料号→数量→单价→金额→单号→应收→收款 */
const RECONCILE_LIST_COLS = [
  { f: "customer", label: "客户", type: "text" },
  { f: "shipped_at", label: "出货时间", type: "datetime" },
  { f: "order_no", label: "订单号", type: "text" },
  { f: "customer_part_no", label: "客户料号", type: "text" },
  { f: "ship_qty", label: "出货数量", type: "decimal", dp: 1 },
  { f: "rmb_tax_incl_price", label: "单价", type: "decimal", dp: 4 },
  { f: "amount", label: "出货金额", type: "decimal", dp: 2 },
  { f: "delivery_doc_no", label: "出货单号", type: "text" },
  { f: "receivable_date", label: "应收日期", type: "date" },
  { f: "collection_time", label: "收款时间", type: "text" },
];

const LIST_RECONCILE_COL_WEIGHTS = [
  1.15, 1.1, 1.2, 1.1, 0.85, 0.85, 0.9, 1.05, 0.9, 0.8,
];

/** 对账汇总：客户 × 收款月份应收金额 */
const RECONCILE_SUMMARY_COLS = [
  { f: "customer", label: "客户", type: "text" },
  { f: "collection_time", label: "收款月份", type: "text" },
  { f: "receivable_date", label: "应收日期", type: "date" },
  { f: "line_count", label: "明细行数", type: "text" },
  { f: "total_amount", label: "应收金额", type: "decimal", dp: 2 },
];

const LIST_RECONCILE_SUMMARY_COL_WEIGHTS = [1.25, 0.95, 0.95, 0.8, 1.05];

/** 应付明细列 */
const PAYABLE_LIST_COLS = [
  { f: "supplier", label: "供应商", type: "text" },
  { f: "received_at", label: "收货时间", type: "datetime" },
  { f: "product_part_no", label: "料号", type: "text" },
  { f: "process_name", label: "工序", type: "text" },
  { f: "qty", label: "回货数量", type: "decimal", dp: 1 },
  { f: "unit_price", label: "工序单价", type: "decimal", dp: 4 },
  { f: "amount", label: "应付金额", type: "decimal", dp: 2 },
  { f: "doc_no", label: "回货单号", type: "text" },
  { f: "payable_date", label: "应付日期", type: "date" },
  { f: "settlement_month", label: "结算月份", type: "text" },
];

const LIST_PAYABLE_COL_WEIGHTS = [1.2, 1.1, 1.15, 0.9, 0.85, 0.85, 0.9, 1.0, 0.9, 0.85];

/** 应付汇总：供应商 × 结算月份 */
const PAYABLE_SUMMARY_COLS = [
  { f: "supplier", label: "供应商", type: "text" },
  { f: "settlement_month", label: "结算月份", type: "text" },
  { f: "payable_date", label: "应付日期", type: "date" },
  { f: "line_count", label: "明细行数", type: "text" },
  { f: "total_qty", label: "回货总量", type: "decimal", dp: 1 },
  { f: "total_amount", label: "应付金额", type: "decimal", dp: 2 },
];

const LIST_PAYABLE_SUMMARY_COL_WEIGHTS = [1.25, 0.95, 0.95, 0.75, 0.85, 1.05];

/** 到期总览列（本月/下月） */
const RECEIVABLE_OUTLOOK_COLS = [
  { f: "customer", label: "客户", type: "text" },
  { f: "line_count", label: "明细行数", type: "text" },
  { f: "total_amount", label: "到期金额", type: "decimal", dp: 2 },
];

const PAYABLE_OUTLOOK_COLS = [
  { f: "supplier", label: "供应商", type: "text" },
  { f: "line_count", label: "明细行数", type: "text" },
  { f: "total_amount", label: "到期金额", type: "decimal", dp: 2 },
];

const LIST_RECEIVABLE_OUTLOOK_COL_WEIGHTS = [1.5, 0.85, 1.0];
const LIST_PAYABLE_OUTLOOK_COL_WEIGHTS = [1.5, 0.85, 1.0];

let dueOutlookCache = null;
let reconcileDetailCustomer = "";
let reconcileDetailMonth = "";

let payableDetailMode = false;
let payableDetailSupplier = "";
let payableDetailMonth = "";

const LIST_SEQ_PCT = 3;
const LIST_ACTION_PCT = 6;
const LIST_DATA_PCT = 100 - LIST_SEQ_PCT - LIST_ACTION_PCT;

function buildListColPercents(weights) {
  const total = weights.reduce((a, b) => a + b, 0);
  const targetCent = Math.round(LIST_DATA_PCT * 100);
  const raw = weights.map((w) => (w / total) * targetCent);
  const cents = raw.map((p) => Math.floor(p));
  let used = cents.reduce((a, b) => a + b, 0);
  let rem = targetCent - used;
  for (let i = 0; i < cents.length && rem > 0; i += 1) {
    const add = Math.min(rem, Math.ceil(raw[i]) - cents[i]);
    if (add > 0) {
      cents[i] += add;
      rem -= add;
    }
  }
  if (rem > 0) cents[cents.length - 1] += rem;
  return cents.map((c) => `${(c / 100).toFixed(2)}%`);
}

const LIST_COL_WIDTHS = buildListColPercents(LIST_DETAIL_COL_WEIGHTS);
const LIST_CLOSED_COL_WIDTHS = buildListColPercents([
  ...LIST_DETAIL_COL_WEIGHTS,
  ...LIST_CLOSED_EXTRA_WEIGHTS,
]);
const LIST_SHIPMENT_COL_WIDTHS = buildListColPercents(LIST_SHIPMENT_COL_WEIGHTS);
const LIST_RECONCILE_COL_WIDTHS = buildListColPercents(LIST_RECONCILE_COL_WEIGHTS);
const LIST_RECONCILE_SUMMARY_COL_WIDTHS = buildListColPercents(LIST_RECONCILE_SUMMARY_COL_WEIGHTS);
const LIST_PAYABLE_COL_WIDTHS = buildListColPercents(LIST_PAYABLE_COL_WEIGHTS);
const LIST_PAYABLE_SUMMARY_COL_WIDTHS = buildListColPercents(LIST_PAYABLE_SUMMARY_COL_WEIGHTS);
const LIST_RECEIVABLE_OUTLOOK_COL_WIDTHS = buildListColPercents(LIST_RECEIVABLE_OUTLOOK_COL_WEIGHTS);
const LIST_PAYABLE_OUTLOOK_COL_WIDTHS = buildListColPercents(LIST_PAYABLE_OUTLOOK_COL_WEIGHTS);

/** 订单管理子模块 */
const SUBMODULES = {
  home: {
    title: "首页",
    desc: "订单模块数据总览：未结、结案、出货与客户分布可视化",
    listTitle: "",
    view: null,
    summary: "",
  },
  entry: {
    title: "订单录入",
    desc: "支持 OCR 识别、手动录入",
    listTitle: "",
    view: null,
    summary: "",
  },
  detail: {
    title: "订单明细",
    desc: "全部已录入料号行；表头下方可按列筛选",
    listTitle: "订单明细",
    view: "all",
    summary: "全部料号行",
  },
  shipped: {
    title: "出货明细",
    desc: "未结出货登记与历史导入；误出货可对「未结出货」记录点「一键返回」回到未结订单",
    listTitle: "出货明细",
    view: "shipped",
    summary: "出货记录",
  },
  reconcile: {
    title: "应收",
    desc: "自本月起重连续 6 个收款月滚动展示；点「查看明细」看出货对账行",
    listTitle: "收款到期",
    view: "reconcile",
    summary: "到期客户",
  },
  payable: {
    title: "应付",
    desc: "自本月起重连续 6 个付款月滚动展示；点「查看明细」看回货对账行",
    listTitle: "付款到期",
    view: "payable",
    summary: "到期供应商",
  },
  open: {
    title: "未结订单",
    desc: "未结数量大于 0；距交期 ≤10 天黄色预警、已过交期红色预警；可合并出货",
    listTitle: "未结订单",
    view: "open",
    summary: "未结料号行",
  },
  closed: {
    title: "正常结案订单",
    desc: "通过出货将未结数量清零的料号行；按最后一次出货时间排序",
    listTitle: "正常结案订单",
    view: "closed",
    summary: "正常结案料号行",
  },
  closedForced: {
    title: "强制结案订单",
    desc: "未结订单中点「结案」强制关闭；不记出货、不纳入对账",
    listTitle: "强制结案订单",
    view: "closed_forced",
    summary: "强制结案料号行",
  },
  delivery: {
    title: "客户信息维护",
    desc: "维护客户地址、联系人、账期；对账周期二选一；送货单为可选项（威可特统一模板或专用模板）",
    listTitle: "",
    view: null,
    summary: "",
  },
  supplier: {
    title: "供应商信息维护",
    desc: "维护供应商地址、联系人、电话、邮箱、账期与备注",
    listTitle: "",
    view: null,
    summary: "",
  },
  ai: {
    title: "AI 数据助手",
    desc: "自然语言查询本地订单库；支持业务记忆永久保存",
    listTitle: "",
    view: null,
    summary: "",
  },
};

function setSubmodulePageTitle(text) {
  document.querySelectorAll(".submodule-page-title").forEach((el) => {
    el.textContent = text;
  });
}

let currentSubmodule = "entry";

const PAYMENT_TERM_PRESETS = ["月结30天", "月结60天", "月结90天"];
const PAYMENT_TERM_CUSTOM = "__custom__";

function parsePaymentTerms(raw) {
  const s = String(raw || "").trim();
  if (!s) return { preset: "", customDays: "" };
  const m = s.match(/月结\s*(\d+)\s*天/);
  if (m) {
    const term = `月结${m[1]}天`;
    if (PAYMENT_TERM_PRESETS.includes(term)) return { preset: term, customDays: "" };
    return { preset: PAYMENT_TERM_CUSTOM, customDays: m[1] };
  }
  const m2 = s.match(/(\d+)\s*days?/i);
  if (m2) {
    const term = `月结${m2[1]}天`;
    if (PAYMENT_TERM_PRESETS.includes(term)) return { preset: term, customDays: "" };
    return { preset: PAYMENT_TERM_CUSTOM, customDays: m2[1] };
  }
  return { preset: PAYMENT_TERM_CUSTOM, customDays: "" };
}

function formatPaymentTerms(preset, customDays) {
  if (preset === PAYMENT_TERM_CUSTOM) {
    const d = String(customDays || "").trim();
    return d ? `月结${d}天` : "";
  }
  return preset || "";
}

function paymentTermsControlsHtml(value, options) {
  const opts = options || {};
  const selectClass = opts.selectClass || "payment-terms-preset";
  const customClass = opts.customClass || "payment-terms-custom";
  const hiddenClass = opts.hiddenClass || "payment-terms-value";
  const parsed = parsePaymentTerms(value);
  const term = formatPaymentTerms(
    parsed.preset === PAYMENT_TERM_CUSTOM ? PAYMENT_TERM_CUSTOM : parsed.preset,
    parsed.customDays
  ) || String(value || "").trim();
  const isPreset = PAYMENT_TERM_PRESETS.includes(term);
  const isDynamic = term && !isPreset && parsed.preset === PAYMENT_TERM_CUSTOM && parsed.customDays;
  const showCustomInput = parsed.preset === PAYMENT_TERM_CUSTOM && !isDynamic;
  const presetOpts = PAYMENT_TERM_PRESETS.map((t) =>
    `<option value="${esc(t)}"${term === t ? " selected" : ""}>${esc(t)}</option>`
  ).join("");
  const dynamicOpt = isDynamic
    ? `<option value="${esc(term)}" data-dynamic="1" selected>${esc(term)}</option>`
    : "";
  const selectValue = isDynamic ? term : showCustomInput ? PAYMENT_TERM_CUSTOM : term;
  return (
    `<select class="${selectClass}" data-role="preset">` +
    `<option value="">请选择</option>` +
    presetOpts +
    dynamicOpt +
    `<option value="${PAYMENT_TERM_CUSTOM}"${selectValue === PAYMENT_TERM_CUSTOM ? " selected" : ""}>自定义…</option>` +
    `</select>` +
    `<input class="${customClass}${showCustomInput ? "" : " is-hidden"}" data-role="custom-days" type="number" min="1" step="1" placeholder="天" value="${esc(parsed.customDays)}" title="自定义天数" />` +
    `<input type="hidden" data-f="payment_terms" class="pv ${hiddenClass}" value="${esc(term)}" />`
  );
}

function clearDynamicPaymentOption(preset) {
  preset?.querySelectorAll('option[data-dynamic="1"]').forEach((o) => o.remove());
}

function ensureDynamicPaymentOption(preset, term) {
  clearDynamicPaymentOption(preset);
  const opt = document.createElement("option");
  opt.value = term;
  opt.textContent = term;
  opt.dataset.dynamic = "1";
  const customOpt = preset.querySelector(`option[value="${PAYMENT_TERM_CUSTOM}"]`);
  preset.insertBefore(opt, customOpt || null);
  preset.value = term;
}

function bindPaymentTermsWrap(wrap) {
  if (!wrap || wrap.dataset.bound) return;
  wrap.dataset.bound = "1";
  const preset = wrap.querySelector('[data-role="preset"]');
  const custom = wrap.querySelector('[data-role="custom-days"]');
  const hidden = wrap.querySelector('[data-f="payment_terms"]');
  if (!preset || !hidden) return;

  const syncFromSelect = () => {
    if (preset.value === PAYMENT_TERM_CUSTOM) {
      custom?.classList.remove("is-hidden");
      custom?.focus();
      hidden.value = formatPaymentTerms(PAYMENT_TERM_CUSTOM, custom?.value);
    } else if (preset.value) {
      custom?.classList.add("is-hidden");
      if (custom) custom.value = "";
      hidden.value = preset.value;
    } else {
      custom?.classList.add("is-hidden");
      hidden.value = "";
    }
    hidden.dataset.hoverText = hidden.value ? `账期：${hidden.value}` : "";
    bindHoverTip(preset);
    bindHoverTip(hidden);
  };

  const commitCustomDays = () => {
    const days = String(custom?.value || "").trim();
    if (!days || Number(days) <= 0) {
      hidden.value = "";
      return;
    }
    const term = formatPaymentTerms(PAYMENT_TERM_CUSTOM, days);
    ensureDynamicPaymentOption(preset, term);
    custom?.classList.add("is-hidden");
    hidden.value = term;
    hidden.dataset.hoverText = `账期：${term}`;
    bindHoverTip(preset);
    bindHoverTip(hidden);
  };

  preset.addEventListener("change", () => {
    if (preset.value === PAYMENT_TERM_CUSTOM) {
      clearDynamicPaymentOption(preset);
      syncFromSelect();
      return;
    }
    if (preset.value && preset.selectedOptions[0]?.dataset.dynamic !== "1") {
      clearDynamicPaymentOption(preset);
    }
    syncFromSelect();
  });

  custom?.addEventListener("input", () => {
    if (preset.value !== PAYMENT_TERM_CUSTOM) {
      preset.value = PAYMENT_TERM_CUSTOM;
      clearDynamicPaymentOption(preset);
    }
    hidden.value = formatPaymentTerms(PAYMENT_TERM_CUSTOM, custom.value);
  });

  custom?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      commitCustomDays();
    }
  });

  custom?.addEventListener("blur", commitCustomDays);

  syncFromSelect();
}

function setManualPaymentTerms(value) {
  const wrap = document.getElementById("paymentTermsWrap");
  if (!wrap) return;
  wrap.dataset.bound = "";
  wrap.innerHTML = paymentTermsControlsHtml(value, {
    selectClass: "payment-terms-preset entry-payment-preset",
    customClass: "payment-terms-custom entry-payment-custom",
  });
  bindPaymentTermsWrap(wrap);
}

function readPaymentTermsFromWrap(wrap) {
  const preset = wrap?.querySelector('[data-role="preset"]');
  const custom = wrap?.querySelector('[data-role="custom-days"]');
  if (!preset) return "";
  return formatPaymentTerms(preset.value, custom?.value);
}

function showMsg(el, text, ok) {
  el.textContent = text;
  el.className = "msg " + (ok ? "ok" : "error");
  if (text && ok && typeof window.showSaveSuccess === "function" && /已保存|成功/.test(text)) {
    window.showSaveSuccess(text);
  }
}

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function roundToDp(n, dp) {
  const f = Math.pow(10, dp);
  return Math.round(n * f) / f;
}

/** 千分位；整数不补小数，有小数则保留（最多 maxDp 位） */
function fmtSmart(v, maxDp) {
  const n = parseFloat(String(v ?? "").replace(/,/g, ""));
  if (isNaN(n)) return "-";
  const rounded = roundToDp(n, maxDp);
  return rounded.toLocaleString("zh-CN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxDp,
  });
}

function fmtNum(v, dp) {
  return fmtSmart(v, dp);
}

function fmtTax(rate) {
  const n = parseFloat(rate);
  if (isNaN(n)) return "-";
  return (n * 100).toFixed(0) + "%";
}

const QTY_DP = 1;

function calcOpen(po, shipped) {
  return roundToDp((parseFloat(po) || 0) - (parseFloat(shipped) || 0), QTY_DP);
}

function calcOpenDisplay(po, shipped) {
  return fmtSmart(calcOpen(po, shipped), QTY_DP);
}

function fmtWeightDisplay(v) {
  const s = String(v ?? "").trim();
  if (!s) return "-";
  const n = parseFloat(s.replace(/,/g, ""));
  if (isNaN(n)) return esc(s);
  return fmtSmart(n, 2);
}

/* ========== 悬停完整显示（核对 OCR 用） ========== */
let _hoverTipEl = null;

function ensureHoverTip() {
  if (!_hoverTipEl) {
    _hoverTipEl = document.createElement("div");
    _hoverTipEl.id = "hoverTip";
    _hoverTipEl.className = "hover-tip";
    document.body.appendChild(_hoverTipEl);
  }
  return _hoverTipEl;
}

function getHoverText(el) {
  if (el.dataset.hoverText) return el.dataset.hoverText;
  if (el.tagName === "SELECT") {
    const opt = el.options[el.selectedIndex];
    return opt ? opt.text : el.value;
  }
  return el.value != null ? String(el.value) : el.textContent || "";
}

function cellNeedsHoverTip(el) {
  if (!el) return false;
  if (el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA") return true;
  if (el.dataset.hoverText) return true;
  return el.scrollWidth > el.clientWidth + 1;
}

function positionHoverTipNearEl(el) {
  if (!_hoverTipEl || _hoverTipEl.style.display === "none") return;
  const pad = 6;
  const cellRect = el.getBoundingClientRect();
  const tipRect = _hoverTipEl.getBoundingClientRect();
  let x = cellRect.left;
  let y = cellRect.bottom + pad;
  if (x + tipRect.width > window.innerWidth - 8) {
    x = Math.max(8, window.innerWidth - tipRect.width - 8);
  }
  if (y + tipRect.height > window.innerHeight - 8) {
    y = cellRect.top - tipRect.height - pad;
  }
  _hoverTipEl.style.left = x + "px";
  _hoverTipEl.style.top = y + "px";
}

function positionHoverTip(e) {
  if (!_hoverTipEl || _hoverTipEl.style.display === "none") return;
  const pad = 12;
  let x = e.clientX + pad;
  let y = e.clientY + pad;
  const rect = _hoverTipEl.getBoundingClientRect();
  if (x + rect.width > window.innerWidth - 8) x = e.clientX - rect.width - pad;
  if (y + rect.height > window.innerHeight - 8) y = e.clientY - rect.height - pad;
  _hoverTipEl.style.left = x + "px";
  _hoverTipEl.style.top = y + "px";
}

function bindHoverTip(el) {
  if (!el || el.dataset.hoverBound) return;
  el.dataset.hoverBound = "1";
  el.removeAttribute("title");
  const followCursor = el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA";
  if (el.tagName === "TD") {
    el.classList.toggle("has-ellipsis-tip", cellNeedsHoverTip(el));
  }
  el.addEventListener("mouseenter", (e) => {
    const text = getHoverText(el).trim();
    if (!text || !cellNeedsHoverTip(el)) return;
    el.removeAttribute("title");
    const tip = ensureHoverTip();
    tip.textContent = text;
    tip.style.display = "block";
    if (followCursor) {
      positionHoverTip(e);
    } else {
      requestAnimationFrame(() => positionHoverTipNearEl(el));
    }
  });
  if (followCursor) {
    el.addEventListener("mousemove", positionHoverTip);
  }
  el.addEventListener("mouseleave", () => {
    if (_hoverTipEl) _hoverTipEl.style.display = "none";
  });
}

function bindHoverTipAll(root) {
  (root || document).querySelectorAll(".pv, .entry-card input, .entry-card select, .data-table td:not(.action-cell)").forEach(bindHoverTip);
}

function attachDecimalLimit(input, maxDp) {
  input.addEventListener("input", () => {
    let v = input.value.replace(/[^\d.]/g, "");
    const parts = v.split(".");
    if (parts.length > 2) v = parts[0] + "." + parts.slice(1).join("");
    if (v.includes(".")) {
      const [i, d] = v.split(".");
      v = i + "." + d.slice(0, maxDp);
    }
    if (v !== input.value) input.value = v;
  });
}

/** 列表表头短文案（完整含义见 th title） */
const LIST_TH_LABEL = {
  order_date: "接单日期",
  delivery_date: "客户交期",
  created_at: "录入时间",
  order_no: "订单号",
  product_spec: "品名规格",
  customer_part_no: "客户料号",
  unit_weight_g: "单重(g)",
  po_qty: "PO数量",
  shipped_qty: "已出货",
  open_qty: "未结",
  rmb_tax_incl_price: "含税单价",
  amount: "含税金额",
  shipped_at: "出货时间",
  source_label: "来源",
  ship_qty: "本次出货",
  open_qty_after: "出货后未结",
  shipped_qty_after: "累计出货",
  last_shipped_at: "出货时间",
  last_delivery_doc_no: "出货单号",
  delivery_doc_no: "送货单号",
  ship_month: "出货月",
  receivable_date: "应收日期",
  collection_time: "收款时间",
  line_count: "明细行数",
  total_amount: "应收金额",
  amount: "出货金额",
  rmb_tax_incl_price: "含税单价",
};

const LIST_TEXT_COLS = new Set([
  "customer",
  "order_no",
  "product_spec",
  "customer_part_no",
  "created_at",
  "shipped_at",
  "last_shipped_at",
  "last_delivery_doc_no",
  "source_label",
  "ship_month",
  "collection_time",
  "line_count",
  "total_amount",
  "receivable_date",
  "amount",
  "delivery_doc_no",
  "rmb_tax_incl_price",
  "material",
  "payment_terms",
]);

function listColHtml(width) {
  return `<col style="width:${width}" />`;
}

function reconcileShowsSummaryActionColumn() {
  return currentSubmodule === "reconcile" && !reconcileDetailMode;
}

function payableShowsSummaryActionColumn() {
  return currentSubmodule === "payable" && !payableDetailMode;
}

function ledgerShowsSummaryActionColumn() {
  return reconcileShowsSummaryActionColumn() || payableShowsSummaryActionColumn();
}

function listTableCols(viewKey) {
  if (viewKey === "shipped") return SHIPMENT_LIST_COLS;
  if (viewKey === "reconcile") {
    return reconcileDetailMode ? RECONCILE_LIST_COLS : RECEIVABLE_OUTLOOK_COLS;
  }
  if (viewKey === "payable") {
    return payableDetailMode ? PAYABLE_LIST_COLS : PAYABLE_OUTLOOK_COLS;
  }
  if (viewKey === "closed") return [...LIST_DETAIL_COLS, ...LIST_CLOSED_EXTRA_COLS];
  if (viewKey === "closedForced") return LIST_DETAIL_COLS;
  return LIST_DETAIL_COLS;
}

/** 列表是否显示操作列（序号列之后） */
function listShowsActionColumn(viewKey) {
  return viewKey !== "closedForced";
}

function listTableColSpan(viewKey, colCount) {
  let span = colCount + 1;
  if (viewKey === "shipped" || ledgerShowsSummaryActionColumn() || listShowsActionColumn(viewKey)) {
    span += 1;
  }
  return span;
}

function listTableColWidths(viewKey) {
  if (viewKey === "shipped") return LIST_SHIPMENT_COL_WIDTHS;
  if (viewKey === "reconcile") {
    return reconcileDetailMode ? LIST_RECONCILE_COL_WIDTHS : LIST_RECEIVABLE_OUTLOOK_COL_WIDTHS;
  }
  if (viewKey === "payable") {
    return payableDetailMode ? LIST_PAYABLE_COL_WIDTHS : LIST_PAYABLE_OUTLOOK_COL_WIDTHS;
  }
  if (viewKey === "closed") return LIST_CLOSED_COL_WIDTHS;
  return LIST_COL_WIDTHS;
}

function listThText(col) {
  return LIST_TH_LABEL[col.f] || col.label;
}

function listThClass(col) {
  return LIST_TEXT_COLS.has(col.f) ? "list-th-filterable list-th-text" : "list-th-filterable";
}

function listTdClass(col) {
  return LIST_TEXT_COLS.has(col.f) ? "list-td-text" : "";
}

function renderHead(elId, extraCols) {
  const head = document.getElementById(elId);
  const extras = extraCols || [];
  const table = head.closest("table");
  const isShippedList = elId === "listHead" && currentSubmodule === "shipped";
  const isReconcileList = elId === "listHead" && currentSubmodule === "reconcile";
  const isPayableList = elId === "listHead" && currentSubmodule === "payable";
  const isOrderList = elId === "listHead" && !isShippedList && !isReconcileList && !isPayableList;
  const showListActions = isOrderList && listShowsActionColumn(currentSubmodule);
  if (elId === "listHead" && table) {
    let cg = table.querySelector("colgroup.list-colgroup");
    if (!cg) {
      cg = document.createElement("colgroup");
      cg.className = "list-colgroup";
      table.insertBefore(cg, head);
    }
    const widths = listTableColWidths(currentSubmodule);
    const seqCol = listColHtml(`${LIST_SEQ_PCT}%`);
    const actionCol = listColHtml(`${LIST_ACTION_PCT}%`);
    cg.innerHTML =
      seqCol +
      widths.map((w) => listColHtml(w)).join("") +
      (showListActions || isShippedList || ledgerShowsSummaryActionColumn() ? actionCol : "");
  }
  const cols = elId === "listHead" ? listTableCols(currentSubmodule) : COLS;
  const showActions = showListActions;
  const showShippedDn = isShippedList;
  const showLedgerSummaryAction = ledgerShowsSummaryActionColumn();
  const isListHead = elId === "listHead";
  const titleRow =
    "<tr class=\"list-header-row\">" +
    extras.map((c) => `<th scope="col" class="list-th-seq">${c}</th>`).join("") +
    cols
      .map((c) => {
        const text = isListHead ? listThText(c) : c.label;
        const title = isListHead && LIST_TH_LABEL[c.f] ? c.label : "";
        const filterBtn = isListHead
          ? `<button type="button" class="list-filter-btn" data-col="${c.f}" aria-label="筛选${esc(text)}" title="筛选${esc(c.label)}"><span aria-hidden="true">▾</span></button>`
          : "";
        const thCls = isListHead ? listThClass(c) : "";
        return `<th scope="col" class="${thCls}"${title ? ` title="${esc(title)}"` : ""}><span class="list-th-inner"><span class="list-th-label">${text}</span>${filterBtn}</span></th>`;
      })
      .join("") +
    (elId === "previewHead"
      ? '<th scope="col"></th>'
      : showActions
        ? '<th scope="col" class="list-th-action action-cell">操作</th>'
        : showShippedDn
          ? '<th scope="col" class="list-th-action action-cell">操作</th>'
          : showLedgerSummaryAction
            ? '<th scope="col" class="list-th-action action-cell">明细</th>'
            : "") +
    "</tr>";
  head.innerHTML = titleRow;
  if (elId === "listHead") {
    bindListColFilterButtons();
    updateListFilterBtnStates();
  }
}

/** 各子模块列筛选：字段 → 允许显示的值集合；缺省或 null 表示该列未筛选 */
const listColFilters = {};
let listRowsCache = [];
let listColFilterPanelCol = null;
let listColFilterPending = null;

function getListColFilters() {
  if (!listColFilters[currentSubmodule]) listColFilters[currentSubmodule] = {};
  return listColFilters[currentSubmodule];
}

function getListColFilterSet(colField) {
  const f = getListColFilters()[colField];
  if (!f || !(f instanceof Set)) return null;
  return f;
}

function setListColFilterSet(colField, valueSet) {
  const filters = getListColFilters();
  if (valueSet === null || valueSet === undefined) {
    delete filters[colField];
    return;
  }
  filters[colField] = new Set(valueSet);
}

function listFilterCellKey(row, col, viewKey) {
  const raw = String(listFilterRawText(row, col, viewKey) || "").trim();
  if (!raw || raw === "-") return "(空白)";
  return raw;
}

function listFilterRawText(row, col, viewKey) {
  if (viewKey === "reconcile" && !reconcileDetailMode) {
    if (col.f === "total_amount") return fmtSmart(row[col.f], col.dp || 2);
    if (col.f === "line_count") return String(row.line_count ?? "");
    if (col.type === "date") return fmtDateOnly(row[col.f]);
    return String(row[col.f] ?? "");
  }
  if (viewKey === "reconcile") {
    if (col.type === "datetime") return fmtCreatedAt(row.shipped_at);
    if (col.type === "date") return fmtDateOnly(row[col.f]);
    if (col.type === "decimal") return fmtSmart(row[col.f], col.dp || 2);
    return String(row[col.f] ?? "");
  }
  if (viewKey === "shipped") {
    if (col.type === "datetime") return fmtCreatedAt(row.shipped_at);
    if (col.type === "decimal") return fmtSmart(row[col.f], col.dp || 1);
    return String(row[col.f] ?? "");
  }
  if (col.f === "last_shipped_at") return row.last_shipped_at ? fmtCreatedAt(row.last_shipped_at) : "";
  if (col.f === "last_delivery_doc_no") return String(row.last_delivery_doc_no ?? "");
  if (col.type === "datetime") return fmtDateOnly(row.created_at);
  if (col.f === "open_qty") return calcOpenDisplay(row.po_qty, row.shipped_qty);
  if (col.f === "tax_rate") return fmtTax(row.tax_rate);
  if (col.f === "unit_weight_g") return fmtWeightDisplay(row.unit_weight_g);
  if (col.type === "amount") return fmtSmart(row.amount, col.dp || 2);
  if (col.type === "decimal") return fmtSmart(row[col.f], col.dp || 2);
  return String(row[col.f] ?? "");
}

function getColumnUniqueValues(col, viewKey) {
  const seen = new Set();
  listRowsCache.forEach((row) => seen.add(listFilterCellKey(row, col, viewKey)));
  return [...seen].sort((a, b) => a.localeCompare(b, "zh-CN", { numeric: true }));
}

function rowMatchesColFilters(row, cols, viewKey) {
  for (const col of cols) {
    const allowed = getListColFilterSet(col.f);
    if (!allowed) continue;
    const key = listFilterCellKey(row, col, viewKey);
    if (!allowed.has(key)) return false;
  }
  return true;
}

function applyListColFilters(rows, viewKey) {
  const cols = listTableCols(viewKey);
  return rows.filter((row) => rowMatchesColFilters(row, cols, viewKey));
}

function hasActiveListColFilters() {
  const filters = getListColFilters();
  return Object.values(filters).some((v) => v instanceof Set);
}

function updateListFilterBtnStates() {
  document.querySelectorAll("#listHead .list-filter-btn").forEach((btn) => {
    const active = Boolean(getListColFilterSet(btn.dataset.col));
    btn.classList.toggle("is-active", active);
  });
}

function closeListColFilterPanel() {
  document.getElementById("listColFilterPanel")?.classList.add("is-hidden");
  listColFilterPanelCol = null;
  listColFilterPending = null;
}

function positionListColFilterPanel(anchor) {
  const panel = document.getElementById("listColFilterPanel");
  if (!panel || !anchor) return;
  const rect = anchor.getBoundingClientRect();
  const margin = 8;
  let left = rect.left;
  let top = rect.bottom + 4;
  panel.style.left = `${left}px`;
  panel.style.top = `${top}px`;
  panel.classList.remove("is-hidden");
  requestAnimationFrame(() => {
    const pr = panel.getBoundingClientRect();
    if (left + pr.width > window.innerWidth - margin) {
      left = Math.max(margin, window.innerWidth - pr.width - margin);
      panel.style.left = `${left}px`;
    }
    if (top + pr.height > window.innerHeight - margin) {
      top = Math.max(margin, rect.top - pr.height - 4);
      panel.style.top = `${top}px`;
    }
  });
}

function getListColFilterSearchQuery() {
  return (document.getElementById("listColFilterSearch")?.value || "").trim().toLowerCase();
}

function collectListColFilterSelection() {
  const { selected: pendingSelected } = listColFilterPending;
  const box = document.getElementById("listColFilterOptions");
  const cbs = box ? [...box.querySelectorAll("input[type=checkbox]")] : [];
  const q = getListColFilterSearchQuery();

  if (q) {
    return new Set(cbs.filter((cb) => cb.checked).map((cb) => cb.dataset.value));
  }

  const selected = new Set(pendingSelected);
  cbs.forEach((cb) => {
    if (cb.checked) selected.add(cb.dataset.value);
    else selected.delete(cb.dataset.value);
  });
  return selected;
}

function isFullListColFilterSelection(selected, allValues) {
  return (
    allValues.length > 0 &&
    selected.size === allValues.length &&
    allValues.every((v) => selected.has(v))
  );
}

function renderListColFilterOptions(searchQ) {
  const box = document.getElementById("listColFilterOptions");
  if (!box || !listColFilterPanelCol || !listColFilterPending) return;
  const q = (searchQ || "").trim().toLowerCase();
  const values = listColFilterPending.allValues.filter((v) => !q || v.toLowerCase().includes(q));
  const labelEl = document.getElementById("listColFilterSelectAllLabel");
  if (labelEl) labelEl.textContent = q ? "全选当前搜索结果" : "全选";
  if (!values.length) {
    box.innerHTML = '<p class="list-col-filter-empty">无匹配选项</p>';
    syncListColFilterSelectAll();
    return;
  }
  box.innerHTML = values
    .map(
      (v) =>
        `<label class="list-col-filter-opt"><input type="checkbox" data-value="${esc(v)}"${listColFilterPending.selected.has(v) ? " checked" : ""} /> ${esc(v)}</label>`
    )
    .join("");
  box.querySelectorAll("input[type=checkbox]").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (cb.checked) listColFilterPending.selected.add(cb.dataset.value);
      else listColFilterPending.selected.delete(cb.dataset.value);
      syncListColFilterSelectAll();
    });
  });
  syncListColFilterSelectAll();
}

function syncListColFilterSelectAll() {
  const selAll = document.getElementById("listColFilterSelectAll");
  const box = document.getElementById("listColFilterOptions");
  if (!selAll || !box || !listColFilterPending) return;
  const cbs = [...box.querySelectorAll("input[type=checkbox]")];
  if (!cbs.length) {
    selAll.checked = false;
    selAll.indeterminate = false;
    return;
  }
  const checkedVisible = cbs.filter((cb) => cb.checked).length;
  const q = getListColFilterSearchQuery();
  selAll.checked = checkedVisible === cbs.length;
  selAll.indeterminate = checkedVisible > 0 && checkedVisible < cbs.length;
  if (q) {
    selAll.title = "仅作用于当前搜索结果中的选项";
  } else {
    selAll.title = "";
  }
}

function openListColFilterPanel(btn) {
  const colField = btn.dataset.col;
  const cols = listTableCols(currentSubmodule);
  const col = cols.find((c) => c.f === colField);
  if (!col) return;
  const allValues = getColumnUniqueValues(col, currentSubmodule);
  const current = getListColFilterSet(colField);
  const selected = current ? new Set([...current].filter((v) => allValues.includes(v))) : new Set(allValues);
  listColFilterPanelCol = colField;
  listColFilterPending = { allValues, selected, col };
  const label = listThText(col) || col.label;
  const titleEl = document.getElementById("listColFilterPanelTitle");
  if (titleEl) titleEl.textContent = `筛选 · ${label}`;
  const search = document.getElementById("listColFilterSearch");
  if (search) search.value = "";
  renderListColFilterOptions("");
  positionListColFilterPanel(btn);
  search?.focus();
}

function applyListColFilterPanel() {
  if (!listColFilterPanelCol || !listColFilterPending) return;
  const { allValues } = listColFilterPending;
  const selected = collectListColFilterSelection();
  if (isFullListColFilterSelection(selected, allValues)) {
    setListColFilterSet(listColFilterPanelCol, null);
  } else {
    setListColFilterSet(listColFilterPanelCol, selected);
  }
  closeListColFilterPanel();
  updateListFilterBtnStates();
  renderListFromCache();
}

function resetListColFilterPanel() {
  if (!listColFilterPanelCol) return;
  setListColFilterSet(listColFilterPanelCol, null);
  closeListColFilterPanel();
  updateListFilterBtnStates();
  renderListFromCache();
}

function bindListColFilterButtons() {
  document.querySelectorAll("#listHead .list-filter-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (
        listColFilterPanelCol === btn.dataset.col &&
        !document.getElementById("listColFilterPanel")?.classList.contains("is-hidden")
      ) {
        closeListColFilterPanel();
        return;
      }
      openListColFilterPanel(btn);
    });
  });
}

function initListColFilterPanel() {
  document.getElementById("listColFilterApply")?.addEventListener("click", applyListColFilterPanel);
  document.getElementById("listColFilterReset")?.addEventListener("click", resetListColFilterPanel);
  document.getElementById("listColFilterPanelClose")?.addEventListener("click", closeListColFilterPanel);
  document.getElementById("listColFilterSearch")?.addEventListener("input", (e) => {
    renderListColFilterOptions(e.target.value);
  });
  document.getElementById("listColFilterSelectAll")?.addEventListener("change", (e) => {
    const box = document.getElementById("listColFilterOptions");
    if (!box || !listColFilterPending) return;
    const checked = e.target.checked;
    box.querySelectorAll("input[type=checkbox]").forEach((cb) => {
      cb.checked = checked;
      if (checked) listColFilterPending.selected.add(cb.dataset.value);
      else listColFilterPending.selected.delete(cb.dataset.value);
    });
    syncListColFilterSelectAll();
  });
  document.addEventListener("click", (e) => {
    const panel = document.getElementById("listColFilterPanel");
    if (!panel || panel.classList.contains("is-hidden")) return;
    if (panel.contains(e.target) || e.target.closest(".list-filter-btn")) return;
    closeListColFilterPanel();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeListColFilterPanel();
  });
}

function clearListColFilters() {
  listColFilters[currentSubmodule] = {};
  closeListColFilterPanel();
  updateListFilterBtnStates();
  renderListFromCache();
}

function isShipmentRecord(row) {
  return Boolean(
    row &&
      row.shipped_at &&
      row.source &&
      (row.source === "open_ship" || row.source === "import")
  );
}

/** 对账明细：按出货时间等展示（钻取视图内使用） */
function reconcileCellValue(row, col) {
  if (col.type === "datetime") return fmtCreatedAt(row.shipped_at);
  if (col.type === "date") return fmtDateOnly(row[col.f]);
  if (col.type === "decimal") return fmtSmart(row[col.f], col.dp || 2);
  return esc(row[col.f]) || "-";
}

/** 对账汇总：按客户分组，每组多个月份行 + 客户小计 */
function buildReconcileSummaryGroupedRows(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    const key = row.customer || "(未填客户)";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  });
  const customerKeys = [...groups.keys()].sort((a, b) => {
    const sum = (rs) => rs.reduce((s, r) => s + (parseFloat(r.total_amount) || 0), 0);
    const diff = sum(groups.get(b)) - sum(groups.get(a));
    return diff !== 0 ? diff : a.localeCompare(b, "zh-CN");
  });
  const display = [];
  customerKeys.forEach((customer) => {
    const monthRows = groups.get(customer);
    let totalAmt = 0;
    monthRows.forEach((row) => {
      totalAmt += parseFloat(row.total_amount) || 0;
      display.push({ kind: "month", row });
    });
    display.push({
      kind: "customer_summary",
      customer,
      month_count: monthRows.length,
      total_amount: totalAmt,
    });
  });
  return display;
}

function reconcileSummaryMonthCell(row, col) {
  if (col.f === "total_amount") return fmtSmart(row[col.f], col.dp || 2);
  if (col.f === "line_count") return String(row.line_count ?? "-");
  if (col.type === "date") return fmtDateOnly(row[col.f]);
  return esc(row[col.f]) || "-";
}

function reconcileCustomerMonthSubtotalCell(col, summary) {
  if (col.f === "customer") {
    return `<strong>【小计】${esc(summary.customer)}</strong>（${summary.month_count} 个月）`;
  }
  if (col.f === "total_amount") return `<strong>${fmtSmart(String(summary.total_amount), 2)}</strong>`;
  return "—";
}

function reconcileGrandTotalCell(col, summary) {
  if (col.f === "customer") {
    return `<strong>【合计】</strong>（${summary.customer_count} 个客户）`;
  }
  if (col.f === "line_count") return String(summary.line_count);
  if (col.f === "total_amount") return `<strong>${fmtSmart(String(summary.total_amount), 2)}</strong>`;
  return "—";
}

function buildReconcileGrandTotalRowHtml(cols, summary) {
  return `<tr class="reconcile-grand-total-row"><td class="list-td-seq">—</td>${cols
    .map((c) => `<td class="${listTdClass(c)}">${reconcileGrandTotalCell(c, summary)}</td>`)
    .join("")}<td class="action-cell"></td></tr>`;
}

function updateReconcileToolbarState() {
  const isReconcile = currentSubmodule === "reconcile";
  document.querySelectorAll(".reconcile-summary-only").forEach((el) => {
    el.classList.add("is-hidden");
  });
  const backBtn = document.getElementById("reconcileBackBtn");
  const badge = document.getElementById("reconcileDetailBadge");
  if (!isReconcile) return;
  backBtn?.classList.toggle("is-hidden", !reconcileDetailMode);
  badge?.classList.toggle("is-hidden", !reconcileDetailMode);
  if (badge && reconcileDetailMode) {
    badge.textContent = `${reconcileDetailCustomer} · ${reconcileDetailMonth}`;
  }
}

function outlookRowCell(row, col) {
  if (col.f === "line_count") return String(row.line_count ?? "—");
  if (col.type === "decimal") return fmtSmart(row[col.f], col.dp || 2);
  return esc(row[col.f]) || "—";
}

function renderDueOutlook(viewKey, outlook) {
  const cols = listTableCols(viewKey);
  const tbody = document.getElementById("lineListBody");
  const summaryEl = document.getElementById("listSummary");
  if (!tbody || !outlook) return;
  const isReceivable = viewKey === "reconcile";
  const nameField = isReceivable ? "customer" : "supplier";
  const monthField = isReceivable ? "collection_month" : "payment_month";
  const btnClass = isReceivable ? "reconcile-detail-btn" : "payable-detail-btn";
  const dataNameAttr = isReceivable ? "data-customer" : "data-supplier";
  const unitLabel = isReceivable ? "个客户" : "家供应商";
  const colSpan = listTableColSpan(viewKey, cols.length);

  function sectionHtml(section) {
    const rows = section?.rows || [];
    let html = `<tr class="ledger-due-section-head"><td colspan="${colSpan}" class="list-td-text"><strong>${esc(
      section?.label || section?.month || ""
    )}</strong> · 合计 <strong>¥${fmtSmart(
      section?.total_amount || "0",
      2
    )}</strong>（${rows.length} ${unitLabel}）</td></tr>`;
    if (!rows.length) {
      html += `<tr><td colspan="${colSpan}" class="empty-cell">该月暂无到期</td></tr>`;
      return html;
    }
    let seq = 0;
    rows.forEach((row) => {
      seq += 1;
      html += `<tr class="ledger-due-row"><td class="list-td-seq">${seq}</td>${cols
        .map((c) => `<td class="${listTdClass(c)}">${outlookRowCell(row, c)}</td>`)
        .join("")}<td class="action-cell"><button type="button" class="btn btn-sm btn-outline ${btnClass}" ${dataNameAttr}="${esc(
        row[nameField]
      )}" data-month="${esc(row[monthField])}">查看明细</button></td></tr>`;
    });
    return html;
  }

  const monthSections = outlook.months || [];
  tbody.innerHTML = monthSections.map((section) => sectionHtml(section)).join("");
  tbody.querySelectorAll("tr.ledger-due-row td:not(:first-child)").forEach(bindHoverTip);
  if (summaryEl) {
    const total = outlook.total_amount || "0";
    const n = monthSections.length || 6;
    summaryEl.textContent = `${SUBMODULES[viewKey].listTitle}：近 ${n} 月合计 ¥${fmtSmart(total, 2)}`;
  }
}

function updateDueOutlookSummary(viewKey, outlook) {
  const el =
    viewKey === "reconcile"
      ? document.getElementById("reconcileAmountSummary")
      : document.getElementById("payableAmountSummary");
  if (!el || !outlook) return;
  const total = outlook.total_amount || "0";
  const n = outlook.month_count || (outlook.months || []).length || 6;
  el.textContent = `近 ${n} 月合计 ¥${fmtSmart(total, 2)}`;
}

async function openReconcileDetail(customer, month) {
  reconcileDetailMode = true;
  reconcileDetailCustomer = customer;
  reconcileDetailMonth = month;
  listColFilters.reconcile = {};
  setSubmodulePageTitle(`对账明细 · ${customer} · ${month}`);
  updateReconcileToolbarState();
  renderHead("listHead", ["序号"]);
  await loadLines();
}

function closeReconcileDetail() {
  reconcileDetailMode = false;
  reconcileDetailCustomer = "";
  reconcileDetailMonth = "";
  dueOutlookCache = null;
  listColFilters.reconcile = {};
  setSubmodulePageTitle(SUBMODULES.reconcile.listTitle);
  updateReconcileToolbarState();
  renderHead("listHead", ["序号"]);
  loadLines();
}

function payableCellValue(row, col) {
  if (col.type === "datetime") return fmtCreatedAt(row.received_at);
  if (col.type === "date") return fmtDateOnly(row[col.f]);
  if (col.type === "decimal") {
    if (col.f === "amount" && row.price_missing) return "待补BOM";
    return fmtSmart(row[col.f], col.dp || 2);
  }
  return esc(row[col.f]) || "-";
}

function buildPayableSummaryGroupedRows(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    const key = row.supplier || "(未填供应商)";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  });
  const supplierKeys = [...groups.keys()].sort((a, b) => {
    const sum = (rs) => rs.reduce((s, r) => s + (parseFloat(r.total_amount) || 0), 0);
    const diff = sum(groups.get(b)) - sum(groups.get(a));
    return diff !== 0 ? diff : a.localeCompare(b, "zh-CN");
  });
  const display = [];
  supplierKeys.forEach((supplier) => {
    const monthRows = groups.get(supplier);
    let totalAmt = 0;
    monthRows.forEach((row) => {
      totalAmt += parseFloat(row.total_amount) || 0;
      display.push({ kind: "month", row });
    });
    display.push({
      kind: "supplier_summary",
      supplier,
      month_count: monthRows.length,
      total_amount: totalAmt,
    });
  });
  return display;
}

function payableSummaryMonthCell(row, col) {
  if (col.f === "total_amount") return fmtSmart(row[col.f], col.dp || 2);
  if (col.f === "line_count") return String(row.line_count ?? "-");
  if (col.f === "total_qty") return fmtSmart(row.total_qty, col.dp || 1);
  if (col.type === "date") return fmtDateOnly(row[col.f]);
  return esc(row[col.f]) || "-";
}

function payableSupplierMonthSubtotalCell(col, summary) {
  if (col.f === "supplier") {
    return `<strong>【小计】${esc(summary.supplier)}</strong>（${summary.month_count} 个月）`;
  }
  if (col.f === "total_amount") return `<strong>${fmtSmart(String(summary.total_amount), 2)}</strong>`;
  return "—";
}

function buildPayableGrandTotalRowHtml(cols, summary) {
  return `<tr class="reconcile-grand-total-row"><td class="list-td-seq">—</td>${cols
    .map((c) => {
      if (c.f === "supplier") {
        return `<td class="${listTdClass(c)}"><strong>【合计】</strong>（${summary.supplier_count} 个供应商）</td>`;
      }
      if (c.f === "line_count") return `<td class="${listTdClass(c)}"><strong>${summary.line_count}</strong></td>`;
      if (c.f === "total_amount") {
        return `<td class="${listTdClass(c)}"><strong>${fmtSmart(String(summary.total_amount), 2)}</strong></td>`;
      }
      return `<td class="${listTdClass(c)}">—</td>`;
    })
    .join("")}<td class="action-cell"></td></tr>`;
}

function updatePayableToolbarState() {
  const isPayable = currentSubmodule === "payable";
  document.querySelectorAll(".payable-summary-only").forEach((el) => {
    el.classList.add("is-hidden");
  });
  document.querySelectorAll(".payable-detail-only").forEach((el) => {
    el.classList.toggle("is-hidden", !isPayable || !payableDetailMode);
  });
  const backBtn = document.getElementById("payableBackBtn");
  const badge = document.getElementById("payableDetailBadge");
  if (!isPayable) return;
  backBtn?.classList.toggle("is-hidden", !payableDetailMode);
  badge?.classList.toggle("is-hidden", !payableDetailMode);
  if (badge && payableDetailMode) {
    badge.textContent = `${payableDetailSupplier} · ${payableDetailMonth}`;
  }
}

async function openPayableDetail(supplier, month) {
  payableDetailMode = true;
  payableDetailSupplier = supplier;
  payableDetailMonth = month;
  listColFilters.payable = {};
  setSubmodulePageTitle(`应付明细 · ${supplier} · ${month}`);
  updatePayableToolbarState();
  renderHead("listHead", ["序号"]);
  await loadLines();
}

function closePayableDetail() {
  payableDetailMode = false;
  payableDetailSupplier = "";
  payableDetailMonth = "";
  dueOutlookCache = null;
  listColFilters.payable = {};
  setSubmodulePageTitle(SUBMODULES.payable.listTitle);
  updatePayableToolbarState();
  renderHead("listHead", ["序号"]);
  loadLines();
}

function shipmentCellValue(ev, col) {
  if (col.type === "datetime") return fmtCreatedAt(ev.shipped_at);
  if (col.type === "decimal") return fmtSmart(ev[col.f], col.dp || 1);
  return esc(ev[col.f]) || "-";
}

function fmtCreatedAt(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return esc(String(iso));
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fmtDateOnly(val) {
  if (!val) return "-";
  const s = String(val).trim();
  const m = s.match(/^(\d{4}-\d{2}-\d{2})/);
  if (m) return esc(m[1]);
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return esc(s);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** 本地日历「今天」的年月日（用于今日高亮，次日自动熄灭） */
function getLocalTodayParts() {
  const now = new Date();
  return { y: now.getFullYear(), m: now.getMonth(), d: now.getDate() };
}

function isTodayLocal(val) {
  if (!val) return false;
  const s = String(val).trim();
  const today = getLocalTodayParts();
  const dateOnly = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (dateOnly) {
    const y = Number(dateOnly[1]);
    const mo = Number(dateOnly[2]) - 1;
    const day = Number(dateOnly[3]);
    return y === today.y && mo === today.m && day === today.d;
  }
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return false;
  return d.getFullYear() === today.y && d.getMonth() === today.m && d.getDate() === today.d;
}

/** 订单行列表：今日高亮（订单明细/未结=录入日；结案=今日出货或今日录入且已结） */
function isOrderLineTodayHighlight(ln, viewKey) {
  if (!ln) return false;
  if (viewKey === "closed") {
    if (isTodayLocal(ln.last_shipped_at)) return true;
    if (isTodayLocal(ln.created_at) && calcOpen(ln.po_qty, ln.shipped_qty) <= 0) return true;
    return false;
  }
  if (viewKey === "closedForced") {
    return isTodayLocal(ln.updated_at);
  }
  if (viewKey === "detail" || viewKey === "open") {
    return isTodayLocal(ln.created_at);
  }
  return isTodayLocal(ln.created_at);
}

function isShipmentTodayHighlight(ev) {
  return isTodayLocal(ev?.shipped_at);
}

let todayHighlightRefreshTimer = null;

function scheduleTodayHighlightRefresh() {
  if (todayHighlightRefreshTimer) clearTimeout(todayHighlightRefreshTimer);
  const now = new Date();
  const next = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 5);
  const ms = next.getTime() - now.getTime();
  if (ms <= 0) return;
  todayHighlightRefreshTimer = setTimeout(() => {
    if (document.getElementById("lineListBody")) renderListFromCache();
    scheduleTodayHighlightRefresh();
  }, ms);
}

function demoTagHtml(isDemo) {
  if (!isDemo) return "";
  return '<span class="inv-data-tag is-demo" style="margin-right:0.35rem">测</span>';
}

function cellValue(ln, col) {
  if (col.f === "customer_part_no") {
    const tag = demoTagHtml(ln.is_demo);
    const val = esc(ln.customer_part_no) || "-";
    return tag + val;
  }
  if (col.f === "product_spec" && ln.is_demo) {
    return demoTagHtml(true) + (esc(ln.product_spec) || "-");
  }
  if (col.f === "last_shipped_at") return ln.last_shipped_at ? fmtCreatedAt(ln.last_shipped_at) : "-";
  if (col.f === "last_delivery_doc_no") return esc(ln.last_delivery_doc_no) || "-";
  if (col.type === "datetime") return fmtDateOnly(ln.created_at);
  if (col.f === "open_qty") return calcOpenDisplay(ln.po_qty, ln.shipped_qty);
  if (col.f === "tax_rate") return fmtTax(ln.tax_rate);
  if (col.f === "unit_weight_g") return fmtWeightDisplay(ln.unit_weight_g);
  if (col.type === "amount") return fmtSmart(ln.amount, col.dp || 2);
  if (col.type === "decimal") return fmtSmart(ln[col.f], col.dp || 2);
  return esc(ln[col.f]) || "-";
}

function previewInputValue(ln, col) {
  if (col.f === "open_qty") return String(calcOpen(ln.po_qty, ln.shipped_qty));
  if (col.f === "tax_rate") {
    const r = parseFloat(ln.tax_rate);
    return isNaN(r) ? "" : Math.round(r * 100);
  }
  return ln[col.f] != null ? ln[col.f] : "";
}

let master = { customers: [], parts: [] };

/** 新录入行在订单明细中的高亮时长（秒级渐隐，便于定位刚提交的行） */
const NEW_LINE_HIGHLIGHT_MS = 15000;
const highlightedLineIds = new Set();
const highlightTimers = new Map();

function markNewLines(ids) {
  const valid = (ids || []).map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0);
  if (!valid.length) return;
  valid.forEach((id) => {
    highlightedLineIds.add(id);
    if (highlightTimers.has(id)) clearTimeout(highlightTimers.get(id));
    highlightTimers.set(
      id,
      setTimeout(() => {
        highlightedLineIds.delete(id);
        highlightTimers.delete(id);
        document
          .querySelector(`#lineListBody tr[data-line-id="${id}"]`)
          ?.classList.remove("row-new-highlight");
      }, NEW_LINE_HIGHLIGHT_MS)
    );
  });
}

function isLineHighlighted(lineId) {
  return highlightedLineIds.has(Number(lineId));
}

function showNewLinesHighlightHint(count) {
  const sec = Math.round(NEW_LINE_HIGHLIGHT_MS / 1000);
  showListMsg(
    count === 1
      ? `新录入 1 条已高亮，约 ${sec} 秒内渐隐`
      : `新录入 ${count} 条已高亮，约 ${sec} 秒内渐隐`,
    true
  );
}

function scrollToFirstHighlighted() {
  const first = [...highlightedLineIds][0];
  if (!first) return;
  requestAnimationFrame(() => {
    document
      .querySelector(`#lineListBody tr[data-line-id="${first}"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}

async function switchToDetailWithNewLines(ids, hintText) {
  const valid = (ids || []).map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0);
  if (valid.length) {
    markNewLines(valid);
    if (hintText) showListMsg(hintText, true);
    else showNewLinesHighlightHint(valid.length);
  }
  await switchSubmodule("detail");
  requestAnimationFrame(() => scrollToFirstHighlighted());
  setTimeout(scrollToFirstHighlighted, 200);
}

/* ========== 订单管理子模块切换 ========== */
function resolveSubmoduleKey(key) {
  const k = (key || "").trim();
  if (k === "home" && !FEATURE_HOME_DASHBOARD) return "entry";
  if (k === "ai" && !FEATURE_AI_ASSISTANT) return "entry";
  if (k === "customerInfo") return "delivery";
  if (k === "customer") return "delivery";
  if (k === "shipped" && !FEATURE_SHIPPED_MODULE) return "detail";
  return SUBMODULES[k] ? k : "entry";
}

function parseSubmoduleFromHash() {
  const key = (location.hash || "").replace(/^#/, "").trim();
  if (!key) return FEATURE_HOME_DASHBOARD ? "home" : "entry";
  return resolveSubmoduleKey(key);
}

async function switchSubmodule(key) {
  key = resolveSubmoduleKey(key);
  currentSubmodule = key;
  const meta = SUBMODULES[key];
  const isHome = FEATURE_HOME_DASHBOARD && key === "home";
  const isEntry = key === "entry";
  const isDelivery = key === "delivery";
  const isSupplier = key === "supplier";
  const isAi = key === "ai";
  const isReconcile = key === "reconcile";
  const isPayable = key === "payable";
  const isList = !isHome && !isEntry && !isDelivery && !isSupplier && !isAi && !isReconcile && !isPayable;

  document.getElementById("submoduleHome")?.classList.toggle("is-hidden", !isHome);
  document.getElementById("submoduleEntry")?.classList.toggle("is-hidden", !isEntry);
  document.getElementById("submoduleList")?.classList.toggle("is-hidden", !isList && !isReconcile && !isPayable);
  document.getElementById("submoduleDelivery")?.classList.toggle("is-hidden", !isDelivery);
  document.getElementById("submoduleSupplier")?.classList.toggle("is-hidden", !isSupplier);
  document.getElementById("submoduleAi")?.classList.toggle("is-hidden", !isAi);
  document.getElementById("reconcileToolbar")?.classList.toggle("is-hidden", !isReconcile);
  document.getElementById("payableToolbar")?.classList.toggle("is-hidden", !isPayable);

  const titleEl = document.getElementById("pageTitle");
  const descEl = document.getElementById("pageDesc");
  if (titleEl) titleEl.textContent = meta.title;
  if (descEl) descEl.textContent = meta.desc;

  setSubmodulePageTitle(isList || isReconcile || isPayable ? meta.listTitle || meta.title : meta.title);

  document.querySelectorAll("[data-submodule]").forEach((el) => {
    const on = el.dataset.submodule === key;
    el.classList.toggle("active", on);
    if (el.classList.contains("sidebar-module-head-link") || el.classList.contains("top-nav-head-link")) {
      el.classList.toggle("is-active", on);
    }
  });

  if (typeof window.syncSidebarSubgroups === "function") {
    window.syncSidebarSubgroups(key);
  }

  if (location.hash !== "#" + key) {
    history.replaceState(null, "", "#" + key);
  }

  if (isList || isReconcile || isPayable) {
    if (key !== "open") openShipSelectedIds.clear();
    if (isReconcile) {
      reconcileDetailMode = false;
      reconcileDetailCustomer = "";
      reconcileDetailMonth = "";
      dueOutlookCache = null;
      updateReconcileToolbarState();
    }
    if (isPayable) {
      payableDetailMode = false;
      payableDetailSupplier = "";
      payableDetailMonth = "";
      dueOutlookCache = null;
      updatePayableToolbarState();
    }
    renderHead("listHead", ["序号"]);
    await loadLines();
  } else if (isHome && typeof loadOrderDashboard === "function") {
    await loadOrderDashboard(false);
  } else if (isDelivery && typeof loadDeliveryNoteAdmin === "function") {
    await loadDeliveryNoteAdmin();
  } else if (isSupplier && typeof loadSupplierAdmin === "function") {
    await loadSupplierAdmin();
  } else if (isAi && typeof window.focusAiAssistant === "function") {
    window.focusAiAssistant();
  }
  if (typeof window.updateSidebarOrdersActiveState === "function") {
    window.updateSidebarOrdersActiveState();
  }
}

window.switchSubmodule = switchSubmodule;

document.querySelectorAll("[data-submodule]").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    switchSubmodule(el.dataset.submodule);
  });
});

window.addEventListener("hashchange", () => {
  switchSubmodule(parseSubmoduleFromHash());
});

/* ========== 录入方式切换 ========== */
function hidePreview() {
  const area = document.getElementById("previewArea");
  area.classList.add("is-hidden");
  document.getElementById("previewBody").innerHTML = "";
  renderVerifySummary(null);
  revokeOcrSourceUrls();
  const viewer = document.getElementById("ocrSourceViewer");
  if (viewer) viewer.innerHTML = "";
}

function showPreview() {
  document.getElementById("previewArea").classList.remove("is-hidden");
}

function switchEntryMode(mode) {
  if (mode === "excel" && !FEATURE_EXCEL_IMPORT) return;
  const ocrPanel = document.getElementById("ocrPanel");
  const manualPanel = document.getElementById("manualPanel");
  const excelPanel = document.getElementById("excelPanel");
  const modeHint = document.getElementById("modeHint");
  const isOcr = mode === "ocr";
  const isManual = mode === "manual";
  const isExcel = FEATURE_EXCEL_IMPORT && mode === "excel";

  ocrPanel.classList.toggle("is-hidden", !isOcr);
  manualPanel.classList.toggle("is-hidden", !isManual);
  if (excelPanel) excelPanel.classList.toggle("is-hidden", !isExcel);
  modeHint.classList.toggle("is-hidden", isOcr || isManual || isExcel);

  document.getElementById("modeOcrBtn").classList.toggle("active", isOcr);
  document.getElementById("modeManualBtn").classList.toggle("active", isManual);
  document.getElementById("modeExcelBtn")?.classList.toggle("active", isExcel);
  document.getElementById("modeOcrBtn").setAttribute("aria-selected", isOcr ? "true" : "false");
  document.getElementById("modeManualBtn").setAttribute("aria-selected", isManual ? "true" : "false");
  document.getElementById("modeExcelBtn")?.setAttribute("aria-selected", isExcel ? "true" : "false");

  if (isOcr) hidePreview();
}

document.getElementById("modeOcrBtn").addEventListener("click", () => switchEntryMode("ocr"));
document.getElementById("modeManualBtn").addEventListener("click", () => switchEntryMode("manual"));
if (FEATURE_EXCEL_IMPORT) {
  document.getElementById("modeExcelBtn")?.classList.remove("is-hidden");
  document.getElementById("modeExcelBtn")?.removeAttribute("hidden");
  document.getElementById("excelPanel")?.removeAttribute("hidden");
  document.getElementById("modeExcelBtn")?.addEventListener("click", () => switchEntryMode("excel"));
}

/* ========== Excel 导入 ========== */
let excelImportPreview = null;
let excelPreviewFilter = "passed";

function hideExcelPreview() {
  document.getElementById("excelPreviewArea").classList.add("is-hidden");
  document.getElementById("excelPreviewBody").innerHTML = "";
  document.getElementById("excelBlockedPanel").classList.add("is-hidden");
  document.getElementById("excelPendingPanel")?.classList.add("is-hidden");
  document.getElementById("excelPendingCard")?.classList.add("is-hidden");
  excelImportPreview = null;
}

function excelStatusLabel(row) {
  const s = row.review_status || (row.importable ? "passed" : "blocked");
  if (s === "passed") return "已通过";
  if (s === "pending") return "待确认";
  return "阻断";
}

function excelRowTier(row) {
  return row.review_status || (row.importable ? (row.issues?.some((i) => i.level === "warn") ? "pending" : "passed") : "blocked");
}

function renderExcelImportHead() {
  const head = document.getElementById("excelPreviewHead");
  if (!head) return;
  head.innerHTML =
    "<tr><th>Excel行</th><th>状态</th><th class=\"issue-col\">校验说明</th>" +
    COLS.map((c) => `<th>${c.label}</th>`).join("") +
    "</tr>";
}

function excelPreviewCellValue(d, col, row) {
  if (col.f === "open_qty") {
    return esc(row.calc_open_qty != null ? fmtSmart(row.calc_open_qty, QTY_DP) : calcOpenDisplay(d.po_qty, d.shipped_qty));
  }
  if (col.f === "tax_rate") {
    const v = parseFloat(d.tax_rate);
    if (!Number.isFinite(v)) return esc(d.tax_rate);
    return esc(v <= 1 ? (v * 100).toFixed(2).replace(/\.?0+$/, "") + "%" : d.tax_rate);
  }
  return esc(d[col.f]);
}

function renderExcelBlockedPanel(summary) {
  const panel = document.getElementById("excelBlockedPanel");
  if (!panel) return;
  const list = summary.blocked_list || [];
  const report = summary.blocked_report || "";
  if (!list.length) {
    panel.classList.add("is-hidden");
    panel.innerHTML = "";
    return;
  }
  panel.classList.remove("is-hidden");
  const items = list
    .map(
      (b) =>
        `<li><strong>第 ${b.row_no} 行</strong>（${esc(b.customer)} / ${esc(b.order_no)} / ${esc(b.product_spec)}）<br/>
        PO=${esc(b.po_qty)} 已出货=${esc(b.shipped_qty)}${b.excel_open_qty ? ` 未结(Excel)=${esc(b.excel_open_qty)} 应为=${esc(b.calc_open_qty)}` : ""}<br/>
        ${(b.errors || []).map((e) => esc(e)).join("<br/>")}</li>`
    )
    .join("");
  panel.innerHTML =
    `<h4>阻断明细（共 ${list.length} 行，请改 Excel 后重新解析）</h4>` +
    `<p class="excel-blocked-hint">以下为完整阻断原因（可下载/复制）。已通过的行请先点「导入已通过」；待确认行在「待确认」栏。</p>` +
    `<ol>${items}</ol>` +
    `<pre class="excel-blocked-report" id="excelBlockedReportText">${esc(report)}</pre>` +
    `<button type="button" class="btn btn-outline btn-sm" id="excelCopyBlockedBtn">复制全部阻断原因</button>`;
}

function renderExcelPendingPanel(summary) {
  const panel = document.getElementById("excelPendingPanel");
  const card = document.getElementById("excelPendingCard");
  const cardBody = document.getElementById("excelPendingCardBody");
  const cardHint = document.getElementById("excelPendingCardHint");
  const list = summary.pending_list || [];
  if (!list.length) {
    panel?.classList.add("is-hidden");
    if (panel) panel.innerHTML = "";
    card?.classList.add("is-hidden");
    return;
  }
  panel?.classList.remove("is-hidden");
  if (panel) {
    const items = list
      .map(
        (p) =>
          `<li>第 ${p.row_no} 行 ${esc(p.customer)} / ${esc(p.order_no)}：${(p.warnings || []).map(esc).join("；")}</li>`
      )
      .join("");
    panel.innerHTML =
      `<h4>待确认（共 ${list.length} 行）</h4>` +
      `<p>这些行可导入但存在警告，请核对后点「确认导入待确认」。</p><ul>${items}</ul>`;
  }
  card?.classList.remove("is-hidden");
  if (cardHint) cardHint.textContent = `共 ${list.length} 条待确认，核对无误后点击「确认导入待确认」。`;
  if (cardBody) {
    cardBody.innerHTML = list
      .map(
        (p) =>
          `<tr class="row-warn"><td>${p.row_no}</td><td>${esc(p.customer)}</td><td>${esc(p.order_no)}</td>` +
          `<td>${esc(p.product_spec)}</td><td>${(p.warnings || []).map(esc).join("；")}</td></tr>`
      )
      .join("");
  }
}

function excelRowMatchesFilter(row) {
  const tier = excelRowTier(row);
  if (excelPreviewFilter === "all") return true;
  return tier === excelPreviewFilter;
}

function renderExcelPreviewTable() {
  const body = document.getElementById("excelPreviewBody");
  if (!body || !excelImportPreview) return;
  const rows = (excelImportPreview.rows || []).filter(excelRowMatchesFilter);
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="${COLS.length + 3}" class="empty-cell">当前筛选下无数据</td></tr>`; // +3: 行号/状态/说明
    return;
  }
  body.innerHTML = rows
    .map((row) => {
      const d = row.data || {};
      const issues = (row.issues || [])
        .map((i) => `${i.level === "error" ? "✗" : "△"} ${humanizeIssueMessage(i.message)}`)
        .join("；") || "通过";
      const tier = excelRowTier(row);
      const cls = tier === "blocked" ? "row-error" : tier === "pending" ? "row-warn" : "";
      const status = excelStatusLabel(row);
      const dataCells = COLS.map((c) => `<td>${excelPreviewCellValue(d, c, row)}</td>`).join("");
      const issueTitle = issues.replace(/"/g, "&quot;");
      return `<tr class="${cls}">
        <td>${row.row_no}</td>
        <td>${status}</td>
        <td class="issue-cell" title="${issueTitle}">${esc(issues)}</td>
        ${dataCells}
      </tr>`;
    })
    .join("");
}

function updateExcelToolbarCounts(summary) {
  const passed = summary.passed ?? 0;
  const pending = summary.pending ?? 0;
  const blocked = summary.blocked ?? 0;
  document.querySelectorAll(".excel-filter-btn").forEach((btn) => {
    const f = btn.dataset.filter;
    const labels = {
      passed: `已通过 (${passed})`,
      pending: `待确认 (${pending})`,
      blocked: `阻断 (${blocked})`,
      all: `全部 (${summary.total})`,
    };
    if (labels[f]) btn.textContent = labels[f];
  });
  const passBtn = document.getElementById("excelImportPassedBtn");
  const pendBtn = document.getElementById("excelImportPendingBtn");
  if (passBtn) passBtn.textContent = `导入已通过 (${passed})`;
  if (pendBtn) pendBtn.textContent = `确认导入待确认 (${pending})`;
  if (pendBtn) pendBtn.disabled = pending === 0;
}

async function stageExcelPending(summary) {
  const pendingRows = (summary.rows || []).filter((r) => excelRowTier(r) === "pending");
  if (!pendingRows.length) return;
  await fetch("/api/lines/import/stage-pending", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rows: pendingRows }),
  });
}

function renderExcelPreview(summary) {
  excelImportPreview = summary;
  excelPreviewFilter = (summary.passed ?? 0) > 0 ? "passed" : (summary.blocked > 0 ? "blocked" : "all");
  document.querySelectorAll(".excel-filter-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.filter === excelPreviewFilter);
  });
  const area = document.getElementById("excelPreviewArea");
  const sumEl = document.getElementById("excelSummary");
  renderExcelImportHead();
  area.classList.remove("is-hidden");
  const headerWarn = (summary.header_warnings || [])
    .map((w) => `<p class="excel-header-warn">△ ${esc(w)}</p>`)
    .join("");
  sumEl.innerHTML =
    `<p><strong>解析结果：</strong>共 ${summary.total} 行 → ` +
    `<strong style="color:#15803d">已通过 ${summary.passed ?? 0}</strong>（可先导入） · ` +
    `<strong style="color:#a16207">待确认 ${summary.pending ?? 0}</strong> · ` +
    `<strong style="color:#b91c1c">阻断 ${summary.blocked ?? 0}</strong></p>` +
    `<p class="excel-blocked-hint">建议：先点「导入已通过」；待确认在「待确认」栏核对；阻断原因见下方红框或「阻断」栏。</p>` +
    headerWarn;
  updateExcelToolbarCounts(summary);
  renderExcelBlockedPanel(summary);
  renderExcelPendingPanel(summary);
  renderExcelPreviewTable();
  stageExcelPending(summary);
}

function removeImportedRowsFromPreview(tier) {
  if (!excelImportPreview?.rows) return;
  excelImportPreview.rows = excelImportPreview.rows.filter((r) => excelRowTier(r) !== tier);
  excelImportPreview.total = excelImportPreview.rows.length;
  excelImportPreview.passed = excelImportPreview.rows.filter((r) => excelRowTier(r) === "passed").length;
  excelImportPreview.pending = excelImportPreview.rows.filter((r) => excelRowTier(r) === "pending").length;
  excelImportPreview.blocked = excelImportPreview.rows.filter((r) => excelRowTier(r) === "blocked").length;
  excelImportPreview.importable = excelImportPreview.passed + excelImportPreview.pending;
  excelImportPreview.pending_list = excelImportPreview.rows
    .filter((r) => excelRowTier(r) === "pending")
    .map((r) => ({
      row_no: r.row_no,
      customer: r.data?.customer || "",
      order_no: r.data?.order_no || "",
      product_spec: r.data?.product_spec || "",
      warnings: (r.issues || []).filter((i) => i.level === "warn").map((i) => i.message),
    }));
  excelImportPreview.blocked_list = excelImportPreview.rows
    .filter((r) => excelRowTier(r) === "blocked")
    .map((r) => ({
      row_no: r.row_no,
      customer: r.data?.customer || "",
      order_no: r.data?.order_no || "",
      product_spec: r.data?.product_spec || "",
      po_qty: r.data?.po_qty || "",
      shipped_qty: r.data?.shipped_qty || "",
      excel_open_qty: r.excel_open_qty,
      calc_open_qty: r.calc_open_qty,
      errors: (r.issues || []).filter((i) => i.level === "error").map((i) => i.message),
    }));
  if (excelImportPreview.blocked_report && excelImportPreview.blocked_list.length) {
    excelImportPreview.blocked_report = excelImportPreview.blocked_list
      .map((b) => {
        const lines = [
          `【Excel 第 ${b.row_no} 行】`,
          `  客户：${b.customer}`,
          `  订单号：${b.order_no}`,
          `  品名规格：${b.product_spec}`,
          `  PO数量：${b.po_qty}  已出货：${b.shipped_qty}`,
        ];
        if (b.excel_open_qty) lines.push(`  未结(Excel)：${b.excel_open_qty}  应为：${b.calc_open_qty}`);
        (b.errors || []).forEach((e) => lines.push(`  ✗ ${e}`));
        return lines.join("\n");
      })
      .join("\n\n");
  } else {
    excelImportPreview.blocked_report = "";
  }
  updateExcelToolbarCounts(excelImportPreview);
  renderExcelBlockedPanel(excelImportPreview);
  renderExcelPendingPanel(excelImportPreview);
  renderExcelPreviewTable();
}

document.querySelectorAll(".excel-filter-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    excelPreviewFilter = btn.dataset.filter || "all";
    document.querySelectorAll(".excel-filter-btn").forEach((b) => {
      b.classList.toggle("active", b === btn);
    });
    renderExcelPreviewTable();
  });
});

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function humanizeIssueMessage(msg) {
  const s = String(msg || "");
  if (/conversionsyntax|class\s*['"]decimal|invalidoperation/i.test(s)) {
    return "数字列含有无法识别的内容，请检查：PO数量、已出货、未结数量、税率、人民币单价（含税）";
  }
  return s;
}

async function checkServerExcelFeatures() {
  try {
    const res = await fetch("/api/health");
    const h = await res.json();
    if (!h.features?.includes("humanized_errors")) {
      return "当前网页服务版本较旧，请关闭旧窗口后双击「一键启动网页.bat」重启，再 Ctrl+F5 刷新。";
    }
  } catch {
    return "无法连接最新服务，请重启「一键启动网页.bat」。";
  }
  return "";
}

const SHIP_API_STALE_MSG =
  "出货接口未就绪（多为旧版网页服务仍在运行）。请关闭旧的 PowerShell/命令行窗口后，双击「一键启动网页.bat」重新启动，再 Ctrl+F5 强刷本页。";

async function checkServerShipmentApi() {
  try {
    const res = await fetch("/api/health");
    const h = await res.json();
    if (
      h.features?.includes("open_order_ship") &&
      h.features?.includes("ship_delivery_confirm")
    ) {
      return "";
    }
    const probe = await fetch("/api/shipment-events");
    if (probe.ok && h.features?.includes("ship_delivery_confirm")) return "";
    const sc = await fetch("/delivery-note/ship-confirm?line_id=0&qty=1");
    if (sc.status !== 404) return "";
  } catch {
    return "无法连接网页服务，请运行「一键启动网页.bat」。";
  }
  return SHIP_API_STALE_MSG;
}

async function readApiJson(res, staleHint) {
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    const isHtml = /^\s*</.test(text);
    if (res.status === 404 || (isHtml && res.status >= 400)) {
      throw new Error(
        staleHint ||
          "Excel 导入接口未就绪（多为旧版服务仍在运行）。请关闭旧的黑/蓝命令行窗口后，双击「一键启动网页.bat」重新启动，再刷新本页重试。"
      );
    }
    if (isHtml) {
      throw new Error(`服务器返回异常页面 (HTTP ${res.status})，请重启网页服务后重试。`);
    }
    throw new Error("服务器响应格式错误");
  }
}

document.getElementById("excelPreviewBtn").addEventListener("click", async () => {
  const input = document.getElementById("excelFile");
  const msg = document.getElementById("excelMsg");
  const btn = document.getElementById("excelPreviewBtn");
  if (!input.files?.length) {
    showMsg(msg, "请先选择 Excel 文件", false);
    return;
  }
  const fd = new FormData();
  fd.append("file", input.files[0]);
  btn.disabled = true;
  hideExcelPreview();
  showMsg(msg, "正在解析…", true);
  try {
    const stale = await checkServerExcelFeatures();
    if (stale) {
      showMsg(msg, stale, false);
      return;
    }
    const res = await fetch("/api/lines/import/preview", { method: "POST", body: fd });
    const data = await readApiJson(res);
    if (!res.ok) {
      showMsg(msg, data.error || "解析失败", false);
      return;
    }
    renderExcelPreview(data);
    const p = data.passed ?? 0;
    const pend = data.pending ?? 0;
    const blk = data.blocked ?? 0;
    showMsg(
      msg,
      `✓ 解析完成：已通过 ${p} · 待确认 ${pend} · 阻断 ${blk}（阻断原因见下方）`,
      p > 0 || pend > 0
    );
  } catch (err) {
    showMsg(msg, "解析异常：" + err.message, false);
  } finally {
    btn.disabled = false;
  }
});

async function importExcelTier(tier) {
  if (!excelImportPreview?.rows?.length) return 0;
  const rows = excelImportPreview.rows.filter((r) => excelRowTier(r) === tier);
  if (!rows.length) {
    alert(tier === "passed" ? "没有已通过的行" : "没有待确认的行");
    return 0;
  }
  const res = await fetch("/api/lines/import/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rows, tier }),
  });
  const data = await readApiJson(res);
  const msg = document.getElementById("excelMsg");
  if (!res.ok) {
    showMsg(msg, data.error || "导入失败", false);
    return 0;
  }
  removeImportedRowsFromPreview(tier);
  if (tier === "pending") {
    document.getElementById("excelPendingCard")?.classList.add("is-hidden");
  }
  showMsg(msg, `✓ 已导入${tier === "passed" ? "已通过" : "待确认"} ${data.imported} 条，已写入本地数据库`, true);
  await loadMaster();
  await switchToDetailWithNewLines(data.line_ids || []);
  return data.imported;
}

document.getElementById("excelImportPassedBtn")?.addEventListener("click", () => importExcelTier("passed"));
document.getElementById("excelImportPendingBtn")?.addEventListener("click", () => importExcelTier("pending"));

document.getElementById("excelDownloadBlockedBtn")?.addEventListener("click", () => {
  const text = excelImportPreview?.blocked_report || "";
  if (!text) {
    alert("当前没有阻断行");
    return;
  }
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "Excel导入阻断报告.txt";
  a.click();
  URL.revokeObjectURL(a.href);
});

async function loadMaster() {
  const res = await fetch("/api/master");
  master = await res.json();
  const customerNames = master.customers || [];
  fillSelect("customerSelect", customerNames);
  fillSelect("partSelect", master.parts.map((p) => p.product_spec));
}

function fillSelect(id, items, defaultVal, emptyLabel) {
  const sel = document.getElementById(id);
  if (!sel) return;
  sel.innerHTML = items
    .map((it, i) => {
      if (i === 0 && emptyLabel && it === "") return `<option value="">${emptyLabel}</option>`;
      return `<option value="${esc(it)}"${it === defaultVal ? " selected" : ""}>${esc(it)}</option>`;
    })
    .join("");
}

document.getElementById("partSelect").addEventListener("change", async () => {
  const spec = document.getElementById("partSelect").value;
  if (!spec) return;
  const res = await fetch("/api/master/lookup?product_spec=" + encodeURIComponent(spec));
  const data = await res.json();
  if (data.customer_part_no) document.getElementById("customerPartNo").value = data.customer_part_no;
  if (data.product_spec && !entryForm.product_spec.value) entryForm.product_spec.value = data.product_spec;
  if (data.material && !entryForm.material.value) entryForm.material.value = data.material;
  if (data.unit_weight_g && !entryForm.unit_weight_g.value) entryForm.unit_weight_g.value = data.unit_weight_g;
});

async function lookupOrderPartFromBom() {
  const cpn = (document.getElementById("customerPartNo")?.value || "").trim();
  if (cpn.length < 2) return;
  const res = await fetch("/api/bom/lookup?" + new URLSearchParams({ customer_part_no: cpn }));
  const data = await res.json();
  if (!res.ok || !data.found) {
    if (formMsg) formMsg.textContent = data.error || `料号「${cpn}」未在 BOM 中建档，请先在「BOM 录入」中维护`;
    return;
  }
  if (formMsg) formMsg.textContent = "";
  if (data.product_spec && entryForm.product_spec) entryForm.product_spec.value = data.product_spec;
  if (data.material && entryForm.material) entryForm.material.value = data.material;
  if (data.unit_weight_g && entryForm.unit_weight_g) entryForm.unit_weight_g.value = data.unit_weight_g;
}

document.getElementById("customerPartNo")?.addEventListener("change", lookupOrderPartFromBom);
document.getElementById("customerPartNo")?.addEventListener("blur", lookupOrderPartFromBom);

document.getElementById("addCustomerBtn").addEventListener("click", async () => {
  const name = prompt("请输入新客户名称：");
  if (!name || !name.trim()) return;
  const res = await fetch("/api/master/customer", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name.trim() }),
  });
  if (res.ok) {
    await loadMaster();
    document.getElementById("customerSelect").value = name.trim();
  } else { alert((await res.json()).error || "新增失败"); }
});

document.getElementById("addPartBtn").addEventListener("click", () => {
  alert("料号主数据请在顶部菜单「BOM分析 → BOM录入」中维护。");
});

/* ========== 手动录入 ========== */
const entryForm = document.getElementById("entryForm");
const formMsg = document.getElementById("formMsg");

["po_qty", "shipped_qty", "rmb_tax_incl_price"].forEach((name) => {
  const el = entryForm[name];
  if (el) {
    const dp = name === "rmb_tax_incl_price" ? 4 : name === "po_qty" || name === "shipped_qty" ? 1 : 4;
    attachDecimalLimit(el, dp);
  }
});
attachDecimalLimit(entryForm.tax_rate_pct, 2);

function collectFormBody() {
  const pct = parseFloat(entryForm.tax_rate_pct.value);
  return {
    customer: entryForm.customer.value,
    order_date: entryForm.order_date.value,
    delivery_date: entryForm.delivery_date.value,
    order_no: entryForm.order_no.value.trim(),
    payment_terms: (entryForm.payment_terms?.value || "").trim(),
    product_spec: entryForm.product_spec.value,
    customer_part_no: entryForm.customer_part_no.value.trim(),
    unit_weight_g: entryForm.unit_weight_g.value || "0",
    material: entryForm.material.value.trim(),
    po_qty: entryForm.po_qty.value,
    shipped_qty: entryForm.shipped_qty.value || "0",
    unit: entryForm.unit.value.trim(),
    tax_rate: isNaN(pct) ? "0" : String(pct / 100),
    rmb_tax_incl_price: entryForm.rmb_tax_incl_price.value || "0",
  };
}

entryForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const editId = document.getElementById("editId").value;
  const body = collectFormBody();
  const url = editId ? `/api/lines/${editId}` : "/api/lines";
  const res = await fetch(url, {
    method: editId ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (res.status === 409 && data.duplicate_id) {
    showMsg(formMsg, data.error || "该料号行已存在", false);
    await switchToDetailWithNewLines(
      [data.duplicate_id],
      "该料号行已存在，已定位并高亮原记录（未新建重复行）"
    );
    return;
  }
  if (!res.ok) { showMsg(formMsg, data.error || "提交失败", false); return; }
  showMsg(formMsg, editId ? "✓ 修改成功" : "✓ 录入成功", true);
  clearForm();
  await loadMaster();
  if (!editId && data.id) {
    await switchToDetailWithNewLines([data.id]);
  } else if (currentSubmodule === "entry") {
    await switchSubmodule("detail");
  } else {
    await loadLines();
  }
});

document.getElementById("clearBtn").addEventListener("click", clearForm);

function clearForm() {
  entryForm.reset();
  document.getElementById("editId").value = "";
  document.getElementById("submitBtn").textContent = "提交录入";
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById("orderDate").value = today;
  entryForm.tax_rate_pct.value = "13";
  entryForm.shipped_qty.value = "0";
  entryForm.unit_weight_g.value = "0";
  entryForm.rmb_tax_incl_price.value = "0";
  if (entryForm.payment_terms) entryForm.payment_terms.value = "";
}

function loadToForm(ln) {
  document.getElementById("editId").value = ln.id;
  entryForm.customer.value = ln.customer;
  entryForm.order_date.value = ln.order_date;
  entryForm.delivery_date.value = ln.delivery_date || "";
  entryForm.order_no.value = ln.order_no;
  if (entryForm.payment_terms) entryForm.payment_terms.value = ln.payment_terms || "";
  entryForm.product_spec.value = ln.product_spec;
  entryForm.customer_part_no.value = ln.customer_part_no || "";
  entryForm.unit_weight_g.value = ln.unit_weight_g;
  entryForm.material.value = ln.material || "";
  entryForm.po_qty.value = ln.po_qty;
  entryForm.shipped_qty.value = ln.shipped_qty;
  entryForm.unit.value = ln.unit || "";
  entryForm.tax_rate_pct.value = Math.round(parseFloat(ln.tax_rate) * 100) || 0;
  entryForm.rmb_tax_incl_price.value = ln.rmb_tax_incl_price;
  document.getElementById("submitBtn").textContent = "保存修改";
  switchSubmodule("entry");
  switchEntryMode("manual");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ========== 订单明细 · 行内修改 ========== */
let listEditingId = null;

function lineInputValue(ln, col) {
  if (col.f === "open_qty") return String(calcOpen(ln.po_qty, ln.shipped_qty));
  if (col.f === "tax_rate") {
    const r = parseFloat(ln.tax_rate);
    return isNaN(r) ? "" : String(Math.round(r * 100));
  }
  if (col.type === "amount") return ln.amount != null ? String(ln.amount) : "";
  return ln[col.f] != null ? String(ln[col.f]) : "";
}

function renderListEditCell(ln, col) {
  if (col.f === "open_qty" || col.type === "readonly" || col.type === "amount" || col.type === "datetime") {
    const display =
      col.type === "datetime"
        ? fmtDateOnly(ln.created_at)
        : col.f === "open_qty" || col.type === "readonly"
          ? calcOpenDisplay(ln.po_qty, ln.shipped_qty)
          : fmtSmart(ln.amount, col.dp || 2);
    return `<td class="ro"><span class="list-edit-open" data-open-for="${ln.id}">${display}</span></td>`;
  }
  const type = col.type === "date" ? "date" : "text";
  const val = lineInputValue(ln, col);
  return `<td><input class="le" data-f="${col.f}" type="${type}" value="${esc(val)}" /></td>`;
}

function collectListRowBody(tr) {
  const row = {};
  tr.querySelectorAll(".le").forEach((inp) => {
    if (inp.dataset.f === "tax_rate") {
      const pct = parseFloat(inp.value);
      row.tax_rate = isNaN(pct) ? "0" : String(pct / 100);
    } else {
      row[inp.dataset.f] = inp.value;
    }
  });
  return row;
}

function bindListEditRow(tr) {
  tr.querySelectorAll(".le").forEach((inp) => {
    const col = COLS.find((c) => c.f === inp.dataset.f);
    if (col?.type === "decimal") attachDecimalLimit(inp, col.dp || 2);
    if (col?.f === "tax_rate") attachDecimalLimit(inp, 2);
    bindHoverTip(inp);
    if (inp.dataset.f === "po_qty" || inp.dataset.f === "shipped_qty") {
      inp.addEventListener("input", () => {
        const po = tr.querySelector('[data-f="po_qty"]')?.value;
        const sh = tr.querySelector('[data-f="shipped_qty"]')?.value;
        const openEl = tr.querySelector(".list-edit-open");
        if (openEl) openEl.textContent = calcOpenDisplay(po, sh);
      });
    }
  });
}

function showListMsg(text, ok) {
  const el = document.getElementById("listMsg");
  if (!el) return;
  el.className = "msg list-msg " + (ok ? "ok" : "error");
  el.textContent = text;
  if (text && ok && typeof window.showSaveSuccess === "function" && /已保存/.test(text)) {
    window.showSaveSuccess(text);
  }
  if (text && !ok) el.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function cancelListEdit() {
  listEditingId = null;
  showListMsg("", true);
  loadLines();
}

async function saveListRow(lineId, tr) {
  const body = collectListRowBody(tr);
  const res = await fetch("/api/lines/" + lineId, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    showListMsg(data.error || "保存失败", false);
    return;
  }
  listEditingId = null;
  showListMsg("✓ 已保存", true);
  await loadMaster();
  await loadLines();
}

function startListEdit(lineId) {
  listEditingId = lineId;
  loadLines().then(() => {
    const tr = document.querySelector(`#lineListBody tr[data-line-id="${lineId}"]`);
    tr?.scrollIntoView({ behavior: "smooth", block: "center" });
    tr?.querySelector(".le")?.focus();
  });
}

function isOrderDateOlderThanMonths(orderDate, months = OPEN_ORDER_STALE_MONTHS) {
  if (!orderDate) return false;
  const d = new Date(String(orderDate).trim() + "T12:00:00");
  if (Number.isNaN(d.getTime())) return false;
  const cutoff = new Date();
  cutoff.setHours(12, 0, 0, 0);
  cutoff.setMonth(cutoff.getMonth() - months);
  return d < cutoff;
}

function parseLocalDateOnly(str) {
  if (!str) return null;
  const s = String(str).trim();
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), 12, 0, 0, 0);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** 距客户交期剩余天数（本地日历）；无交期返回 null */
function daysUntilDelivery(deliveryDate) {
  const d = parseLocalDateOnly(deliveryDate);
  if (!d) return null;
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  return Math.round((d.getTime() - today.getTime()) / 86400000);
}

/** 未结订单：客户交期预警 class（仍有未结数量时） */
function openDeliveryWarningClass(ln) {
  if (!ln || calcOpen(ln.po_qty, ln.shipped_qty) <= 0) return "";
  const days = daysUntilDelivery(ln.delivery_date);
  if (days === null) return "";
  if (days <= 0) return "row-delivery-overdue";
  if (days <= OPEN_DELIVERY_WARN_DAYS) return "row-delivery-warning";
  return "";
}

function renderOpenSeqCell(ln, idx) {
  if (!FEATURE_BATCH_SHIP || currentSubmodule !== "open") {
    return `<td class="list-td-seq">${idx + 1}</td>`;
  }
  const checked = openShipSelectedIds.has(ln.id) ? " checked" : "";
  return `<td class="list-td-seq open-ship-seq-cell"><label class="open-ship-check-wrap"><input type="checkbox" class="open-ship-check" data-id="${ln.id}" aria-label="选择合并出货"${checked} /><span class="open-ship-seq-num">${idx + 1}</span></label></td>`;
}

function renderListActions(ln, viewKey) {
  if (viewKey === "open") {
    return `<button type="button" class="btn btn-sm btn-primary ship-open-btn" data-id="${ln.id}">出货</button>
            <button type="button" class="btn btn-sm btn-outline force-close-btn" data-id="${ln.id}">结案</button>`;
  }
  return `<button type="button" class="btn btn-sm btn-primary edit-btn" data-id="${ln.id}">修改</button>
           <button type="button" class="btn btn-sm btn-danger delete-btn" data-id="${ln.id}">删除</button>`;
}

let _shipDnLine = null;
let _shipDnMode = "single";
let _shipDnBatchLines = [];
let _shipDnUiMode = "wkt_standard";
let _shipDnCustomUrl = "";
const openShipSelectedIds = new Set();

async function fetchShipUiMode(customer) {
  const res = await fetch(
    "/api/delivery-templates/ship-ui?customer=" + encodeURIComponent(customer || "")
  );
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "无法读取送货单配置");
  return data;
}

function applyShipDnUiMode(ui) {
  _shipDnUiMode = ui.mode || "wkt_standard";
  _shipDnCustomUrl = ui.raw_download_url || "";
  const frame = document.getElementById("shipDnFrame");
  const customPanel = document.getElementById("shipDnCustomPanel");
  const simplePanel = document.getElementById("shipDnSimplePanel");
  const reloadBtn = document.getElementById("shipDnReloadDraft");
  const confirmBtn = document.getElementById("shipDnConfirm");
  const tplName = document.getElementById("shipDnCustomTplName");
  const previewLink = document.getElementById("shipDnCustomOpenTpl");
  const msg = document.getElementById("shipDnMsg");

  const isWkt = _shipDnUiMode === "wkt_standard";
  const isCustom = _shipDnUiMode === "custom_excel";

  frame?.classList.toggle("is-hidden", !isWkt);
  customPanel?.classList.toggle("is-hidden", !isCustom);
  simplePanel?.classList.toggle("is-hidden", _shipDnUiMode !== "none");
  reloadBtn?.classList.toggle("is-hidden", !isWkt);

  if (confirmBtn) {
    if (isCustom) confirmBtn.textContent = "确认出货并打开模板";
    else if (_shipDnUiMode === "none") confirmBtn.textContent = "确认出货";
    else confirmBtn.textContent = "确认出货并生成送货单";
  }

  if (tplName) tplName.textContent = ui.template_file || "—";
  if (previewLink) {
    previewLink.href = ui.raw_download_url || "#";
    previewLink.classList.toggle("is-hidden", !isCustom || !ui.raw_download_url || ui.template_missing);
  }

  if (msg) {
    if (isCustom && ui.template_missing) {
      msg.textContent = "专用模板尚未上传，请先在「客户信息维护」上传 Excel 模板。";
      msg.className = "msg ship-dn-msg error";
    } else if (!isWkt) {
      msg.textContent = "";
      msg.className = "msg ship-dn-msg";
    }
  }
}

function openDeliveryNoteAfterShip(data) {
  if (data.delivery_note_mode === "custom_excel") {
    const eventId = data.shipment_event_id || (data.shipment_event_ids && data.shipment_event_ids[0]);
    if (eventId) {
      openCustomExcelLocally(eventId, data.shipment_event_ids).catch((err) => {
        alert(err.message || "无法打开 Excel 模板");
      });
    }
    return;
  }
  const dnUrl = data.delivery_note_print_url || data.delivery_note_download_url;
  if (dnUrl) window.open(dnUrl, "_blank", "noopener");
}

async function openCustomExcelLocally(eventId, batchEventIds, regenerate) {
  const res = await fetch("/api/delivery-notes/" + eventId + "/open-local", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      batch_event_ids: (batchEventIds || []).map((x) => Number(x)).filter((x) => x > 0),
      regenerate: regenerate !== false,
    }),
  });
  const data = await readApiJson(res, "无法打开 Excel");
  if (!res.ok) throw new Error(data.error || "无法打开 Excel");
  showListMsg(data.message || "已在 Excel 中打开；保存后将自动写入出货明细", true);
  watchCustomExcelSaved(eventId);
  return data;
}

function watchCustomExcelSaved(eventId) {
  let elapsed = 0;
  const poll = async () => {
    elapsed += 2;
    if (elapsed > 600) return;
    try {
      const res = await fetch("/api/delivery-notes/" + eventId + "/attachment-status");
      const data = await res.json();
      if (res.ok && data.saved_at) {
        showListMsg("✓ 送货单已保存到出货明细", true);
        if (currentSubmodule === "shipped") await loadLines();
        return;
      }
    } catch {
      /* ignore */
    }
    setTimeout(poll, 2000);
  };
  setTimeout(poll, 2000);
}

function shipmentDeliveryAction(ev) {
  if (ev.delivery_note_mode === "none") return "";
  if (ev.delivery_note_mode === "custom_excel") {
    const label = ev.saved_at ? "打开送货单" : "打开Excel";
    return `<button type="button" class="btn btn-sm btn-outline custom-excel-open-btn" data-event-id="${ev.id}" data-regenerate="${ev.saved_at ? "0" : "1"}">${label}</button>`;
  }
  return `<a class="btn btn-sm btn-outline" href="/delivery-note/print/${ev.id}" target="_blank" rel="noopener">送货单</a>`;
}

function shipmentRowActions(ev) {
  const parts = [];
  const dn = shipmentDeliveryAction(ev);
  if (dn) parts.push(dn);
  parts.push(
    `<button type="button" class="btn btn-sm btn-outline shipment-return-btn" data-event-id="${ev.id}" title="撤销本次出货，料号回到未结订单">一键返回</button>`
  );
  return parts.join(" ");
}

async function returnShipmentToOpen(eventId) {
  const ev = listRowsCache.find((row) => Number(row.id) === Number(eventId));
  if (!ev) {
    alert("找不到出货记录");
    return;
  }
  const lines = [
    "确认撤销本次出货？",
    "",
    `客户：${ev.customer || ""}`,
    `订单号：${ev.order_no || ""}`,
    `本次出货：${ev.ship_qty || ""}`,
    ev.source_label ? `来源：${ev.source_label}` : "",
    "",
    "撤销后该料号回到「未结订单」，本条出货明细会删除。",
    "已保存的送货单附件不再关联此记录。",
  ].filter(Boolean);
  if (!confirm(lines.join("\n"))) return;
  let res;
  try {
    res = await fetch(`/api/shipment-events/${eventId}/return-open`, { method: "POST" });
  } catch (err) {
    alert(err.message || "无法连接服务器，请确认服务已启动");
    return;
  }
  const raw = await res.text();
  let data = {};
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = {};
  }
  if (!res.ok) {
    const hint =
      res.status === 404
        ? "接口不存在，请重启 Web 服务后再试（python test_impl/web/app.py）"
        : "";
    alert([data.error || `撤销失败（HTTP ${res.status}）`, hint].filter(Boolean).join("\n\n"));
    return;
  }
  const openQty = data.open_qty != null ? data.open_qty : "";
  showListMsg(`✓ 已撤销出货，未结数量 ${openQty}，料号已回到「未结订单」`, true);
  await loadLines();
}

function getOpenShipSelectedLines() {
  const ids = new Set(openShipSelectedIds);
  return listRowsCache.filter((ln) => ids.has(ln.id));
}

function canBatchShipSelection(lines) {
  if (!lines || lines.length < 2) {
    return { ok: false, reason: "请至少勾选两条料号" };
  }
  const customer = (lines[0].customer || "").trim();
  const mismatch = lines.find((ln) => (ln.customer || "").trim() !== customer);
  if (mismatch) {
    return { ok: false, reason: "合并出货须为同一客户" };
  }
  return { ok: true };
}

function updateOpenBatchShipUi() {
  const btn = document.getElementById("openBatchShipBtn");
  const hint = document.getElementById("openBatchShipHint");
  if (!FEATURE_BATCH_SHIP || currentSubmodule !== "open") {
    btn?.classList.add("is-hidden");
    hint?.classList.add("is-hidden");
    return;
  }
  const lines = getOpenShipSelectedLines();
  const n = lines.length;
  if (n >= 2) {
    const check = canBatchShipSelection(lines);
    if (check.ok) {
      btn?.classList.remove("is-hidden");
      if (btn) btn.textContent = `合并出货（${n} 条）`;
      hint?.classList.add("is-hidden");
    } else {
      btn?.classList.add("is-hidden");
      if (hint) {
        hint.textContent = check.reason || "无法合并出货";
        hint.classList.remove("is-hidden");
      }
    }
  } else {
    btn?.classList.add("is-hidden");
    hint?.classList.add("is-hidden");
  }
}

function renderShipDnBatchTable(lines) {
  const tbody = document.getElementById("shipDnBatchBody");
  if (!tbody) return;
  tbody.innerHTML = lines
    .map((ln) => {
      const openVal = calcOpen(ln.po_qty, ln.shipped_qty);
      const openDisp = calcOpenDisplay(ln.po_qty, ln.shipped_qty);
      return `<tr data-line-id="${ln.id}">
        <td>${esc(ln.order_no) || "—"}</td>
        <td>${esc(ln.product_spec) || "—"}</td>
        <td>${openDisp}</td>
        <td><input type="text" class="ship-dn-batch-qty" data-line-id="${ln.id}" data-open="${openVal}" value="${openDisp === "-" ? "" : openVal}" /></td>
      </tr>`;
    })
    .join("");
  tbody.querySelectorAll(".ship-dn-batch-qty").forEach((inp) => {
    inp.addEventListener("input", syncBatchQtyToShipDnFrame);
    inp.addEventListener("change", syncBatchQtyToShipDnFrame);
  });
}

function collectBatchShipItems() {
  const items = [];
  document.querySelectorAll("#shipDnBatchBody tr[data-line-id]").forEach((tr) => {
    const lineId = Number(tr.dataset.lineId);
    const inp = tr.querySelector(".ship-dn-batch-qty");
    const qty = inp?.value.trim().replace(/,/g, "") || "";
    if (lineId && qty) items.push({ line_id: lineId, qty });
  });
  return items;
}

function batchShipItemsParam(items) {
  return items.map((i) => `${i.line_id}:${i.qty}`).join(",");
}

function getShipDnFrameWin() {
  const frame = document.getElementById("shipDnFrame");
  return frame?.contentWindow || null;
}

function syncBatchQtyToShipDnFrame() {
  const items = collectBatchShipItems();
  const win = getShipDnFrameWin();
  if (win?.syncLineQtyFromParent && items.length) {
    win.syncLineQtyFromParent(items.map((i) => i.qty));
  }
}

function collectShipDnPayload() {
  if (_shipDnMode === "batch") {
    syncBatchQtyToShipDnFrame();
  }
  const qty = document.getElementById("shipDnQty")?.value.trim().replace(/,/g, "") || "";
  const win = getShipDnFrameWin();
  if (win && typeof win.collectDeliveryNoteDoc === "function") {
    const doc = win.collectDeliveryNoteDoc();
    if (_shipDnMode === "batch") {
      const items = collectBatchShipItems();
      if (doc.lines && items.length) {
        items.forEach((it, i) => {
          if (doc.lines[i]) doc.lines[i].qty = it.qty;
        });
        let sum = 0;
        items.forEach((it) => {
          const n = parseFloat(String(it.qty || "").replace(/,/g, ""));
          if (!isNaN(n)) sum += n;
        });
        if (sum > 0) doc.total_qty = String(sum);
      }
      doc.ship_qty = items.map((i) => i.qty).join(",");
      return doc;
    }
    doc.ship_qty = qty;
    if (doc.lines && doc.lines[0]) doc.lines[0].qty = doc.lines[0].qty || qty;
    doc.total_qty = doc.total_qty || qty;
    return doc;
  }
  return { ship_qty: qty, lines: [{ qty }] };
}

function closeShipDnModal() {
  const frame = document.getElementById("shipDnFrame");
  if (frame) frame.src = "about:blank";
  document.getElementById("shipDnBackdrop")?.classList.add("is-hidden");
  _shipDnLine = null;
  _shipDnMode = "single";
  _shipDnBatchLines = [];
  _shipDnUiMode = "wkt_standard";
  _shipDnCustomUrl = "";
  document.getElementById("shipDnSinglePanel")?.classList.remove("is-hidden");
  document.getElementById("shipDnBatchPanel")?.classList.add("is-hidden");
  document.getElementById("shipDnCustomPanel")?.classList.add("is-hidden");
  document.getElementById("shipDnSimplePanel")?.classList.add("is-hidden");
  document.getElementById("shipDnFrame")?.classList.remove("is-hidden");
  document.getElementById("shipDnReloadDraft")?.classList.remove("is-hidden");
  const title = document.getElementById("shipDnTitle");
  if (title) title.textContent = "出货确认 · 送货单";
  const confirmBtn = document.getElementById("shipDnConfirm");
  if (confirmBtn) confirmBtn.textContent = "确认出货并生成送货单";
}

function loadShipDnDraft(lineId, qty) {
  const msg = document.getElementById("shipDnMsg");
  const frame = document.getElementById("shipDnFrame");
  if (!frame) return Promise.reject(new Error("预览框未就绪"));
  if (msg) {
    msg.textContent = "正在载入送货单版式…";
    msg.className = "msg ship-dn-msg";
  }
  return new Promise((resolve, reject) => {
    frame.onload = () => {
      try {
        const doc = frame.contentDocument;
        const bodyText = doc?.body?.innerText || "";
        if (/not found/i.test(bodyText) && doc?.title?.toLowerCase().includes("not found")) {
          const err = new Error(SHIP_API_STALE_MSG);
          if (msg) {
            msg.textContent = err.message;
            msg.className = "msg ship-dn-msg error";
          }
          reject(err);
          return;
        }
        if (!doc?.getElementById("shipConfirmForm")) {
          const err = new Error(SHIP_API_STALE_MSG);
          if (msg) {
            msg.textContent = err.message;
            msg.className = "msg ship-dn-msg error";
          }
          reject(err);
          return;
        }
      } catch {
        /* 跨域时无法读 iframe，忽略 */
      }
      if (msg) msg.textContent = "";
      const win = getShipDnFrameWin();
      if (win?.syncLineQtyFromParent) win.syncLineQtyFromParent(qty);
      resolve();
    };
    frame.onerror = () => {
      const err = new Error("无法载入送货单");
      if (msg) {
        msg.textContent = err.message;
        msg.className = "msg ship-dn-msg error";
      }
      reject(err);
    };
    frame.src =
      "/delivery-note/ship-confirm?line_id=" +
      encodeURIComponent(lineId) +
      "&qty=" +
      encodeURIComponent(qty);
  });
}

function loadShipDnDraftBatch() {
  const msg = document.getElementById("shipDnMsg");
  const frame = document.getElementById("shipDnFrame");
  if (!frame) return Promise.reject(new Error("预览框未就绪"));
  const items = collectBatchShipItems();
  if (items.length < 2) {
    return Promise.reject(new Error("合并出货至少需要两条有效数量"));
  }
  if (msg) {
    msg.textContent = "正在载入送货单版式…";
    msg.className = "msg ship-dn-msg";
  }
  return new Promise((resolve, reject) => {
    frame.onload = () => {
      try {
        const doc = frame.contentDocument;
        const bodyText = doc?.body?.innerText || "";
        if (/not found/i.test(bodyText) && doc?.title?.toLowerCase().includes("not found")) {
          const err = new Error(SHIP_API_STALE_MSG);
          if (msg) {
            msg.textContent = err.message;
            msg.className = "msg ship-dn-msg error";
          }
          reject(err);
          return;
        }
        if (!doc?.getElementById("shipConfirmForm")) {
          const err = new Error(SHIP_API_STALE_MSG);
          if (msg) {
            msg.textContent = err.message;
            msg.className = "msg ship-dn-msg error";
          }
          reject(err);
          return;
        }
      } catch {
        /* 跨域时无法读 iframe，忽略 */
      }
      if (msg) msg.textContent = "";
      const win = getShipDnFrameWin();
      if (win?.syncLineQtyFromParent) win.syncLineQtyFromParent(items.map((i) => i.qty));
      resolve();
    };
    frame.onerror = () => {
      const err = new Error("无法载入送货单");
      if (msg) {
        msg.textContent = err.message;
        msg.className = "msg ship-dn-msg error";
      }
      reject(err);
    };
    frame.src =
      "/delivery-note/batch-ship-confirm?items=" + encodeURIComponent(batchShipItemsParam(items));
  });
}

async function openShipDnModal(lineId, ln) {
  const stale = await checkServerShipmentApi();
  if (stale) {
    showListMsg(stale, false);
    return;
  }
  _shipDnMode = "single";
  _shipDnBatchLines = [];
  document.getElementById("shipDnSinglePanel")?.classList.remove("is-hidden");
  document.getElementById("shipDnBatchPanel")?.classList.add("is-hidden");
  const title = document.getElementById("shipDnTitle");
  if (title) title.textContent = "出货确认 · 送货单";
  _shipDnLine = ln;
  const openVal = calcOpen(ln.po_qty, ln.shipped_qty);
  const openDisplay = calcOpenDisplay(ln.po_qty, ln.shipped_qty);
  document.getElementById("shipDnLineId").value = String(lineId);
  document.getElementById("shipDnSubtitle").textContent =
    `客户：${ln.customer}　订单号：${ln.order_no || "—"}　品名：${ln.product_spec || "—"}　当前未结：${openDisplay}`;
  document.getElementById("shipDnQty").value =
    openDisplay === "-" ? "" : String(openVal);
  document.getElementById("shipDnOpenQty").value = openDisplay;
  document.getElementById("shipDnMsg").textContent = "";
  document.getElementById("shipDnBackdrop")?.classList.remove("is-hidden");
  try {
    const ui = await fetchShipUiMode(ln.customer);
    applyShipDnUiMode(ui);
    if (ui.mode === "custom_excel" && ui.template_missing) {
      return;
    }
    if (_shipDnUiMode === "wkt_standard") {
      await loadShipDnDraft(lineId, document.getElementById("shipDnQty").value.trim() || openVal);
    }
  } catch (err) {
    alert(err.message || "无法载入送货单配置");
  }
}

async function openBatchShipModal() {
  const stale = await checkServerShipmentApi();
  if (stale) {
    showListMsg(stale, false);
    return;
  }
  const lines = getOpenShipSelectedLines();
  const check = canBatchShipSelection(lines);
  if (!check.ok) {
    alert(check.reason || "无法合并出货");
    return;
  }
  _shipDnMode = "batch";
  _shipDnBatchLines = lines;
  _shipDnLine = null;
  document.getElementById("shipDnSinglePanel")?.classList.add("is-hidden");
  document.getElementById("shipDnBatchPanel")?.classList.remove("is-hidden");
  const title = document.getElementById("shipDnTitle");
  if (title) title.textContent = "合并出货确认 · 送货单";
  document.getElementById("shipDnSubtitle").textContent =
    `客户：${lines[0].customer}　共 ${lines.length} 条料号`;
  document.getElementById("shipDnLineId").value = "";
  document.getElementById("shipDnMsg").textContent = "";
  renderShipDnBatchTable(lines);
  document.getElementById("shipDnBackdrop")?.classList.remove("is-hidden");
  try {
    const ui = await fetchShipUiMode(lines[0].customer);
    applyShipDnUiMode(ui);
    if (ui.mode === "custom_excel" && ui.template_missing) {
      return;
    }
    if (_shipDnUiMode === "wkt_standard") {
      await loadShipDnDraftBatch();
    }
  } catch (err) {
    alert(err.message || "无法载入送货单配置");
  }
}

async function confirmShipFromModal() {
  if (_shipDnMode === "batch") {
    await confirmBatchShipFromModal();
    return;
  }
  const lineId = Number(document.getElementById("shipDnLineId")?.value);
  const qty = document.getElementById("shipDnQty")?.value.trim().replace(/,/g, "");
  const msg = document.getElementById("shipDnMsg");
  if (!lineId || !qty) {
    if (msg) {
      msg.textContent = "请填写本次出货数量";
      msg.className = "msg ship-dn-msg error";
    }
    return;
  }
  if (_shipDnUiMode === "custom_excel") {
    const ui = await fetchShipUiMode(_shipDnLine?.customer || "").catch(() => ({}));
    if (ui.template_missing) {
      if (msg) {
        msg.textContent = "请先上传专用 Excel 模板";
        msg.className = "msg ship-dn-msg error";
      }
      return;
    }
  }
  const delivery_note = _shipDnUiMode === "wkt_standard" ? collectShipDnPayload() : undefined;
  const btn = document.getElementById("shipDnConfirm");
  if (btn) btn.disabled = true;
  if (msg) {
    msg.textContent = "正在出货…";
    msg.className = "msg ship-dn-msg";
  }
  let res;
  let data;
  try {
    const body = { qty };
    if (delivery_note !== undefined) body.delivery_note = delivery_note;
    res = await fetch("/api/lines/" + lineId + "/ship", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    data = await readApiJson(res, SHIP_API_STALE_MSG);
  } catch (err) {
    if (msg) {
      msg.textContent = err.message || "出货失败";
      msg.className = "msg ship-dn-msg error";
    }
    if (btn) btn.disabled = false;
    return;
  }
  if (btn) btn.disabled = false;
  if (!res.ok) {
    const errText = data.error || "出货失败";
    if (msg) {
      msg.textContent = errText;
      msg.className = "msg ship-dn-msg error";
    }
    alert(errText);
    return;
  }
  closeShipDnModal();
  if (data.closed) {
    showListMsg("✓ 已出货；未结已为 0，该料号已归入「正常结案订单」", true);
  } else {
    showListMsg(`✓ 已出货；剩余未结 ${fmtSmart(data.open_qty, QTY_DP)}`, true);
  }
  await loadLines();
  openDeliveryNoteAfterShip(data);
}

async function confirmBatchShipFromModal() {
  const items = collectBatchShipItems();
  const msg = document.getElementById("shipDnMsg");
  if (items.length < 2) {
    if (msg) {
      msg.textContent = "合并出货至少需要两条有效数量";
      msg.className = "msg ship-dn-msg error";
    }
    return;
  }
  if (_shipDnUiMode === "custom_excel") {
    const ui = await fetchShipUiMode(_shipDnBatchLines[0]?.customer || "").catch(() => ({}));
    if (ui.template_missing) {
      if (msg) {
        msg.textContent = "请先上传专用 Excel 模板";
        msg.className = "msg ship-dn-msg error";
      }
      return;
    }
  }
  const delivery_note = _shipDnUiMode === "wkt_standard" ? collectShipDnPayload() : undefined;
  const btn = document.getElementById("shipDnConfirm");
  if (btn) btn.disabled = true;
  if (msg) {
    msg.textContent = "正在合并出货…";
    msg.className = "msg ship-dn-msg";
  }
  let res;
  let data;
  try {
    const body = { items };
    if (delivery_note !== undefined) body.delivery_note = delivery_note;
    res = await fetch("/api/lines/batch-ship", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    data = await readApiJson(res, SHIP_API_STALE_MSG);
  } catch (err) {
    if (msg) {
      msg.textContent = err.message || "出货失败";
      msg.className = "msg ship-dn-msg error";
    }
    if (btn) btn.disabled = false;
    return;
  }
  if (btn) btn.disabled = false;
  if (!res.ok) {
    const errText = data.error || "出货失败";
    if (msg) {
      msg.textContent = errText;
      msg.className = "msg ship-dn-msg error";
    }
    alert(errText);
    return;
  }
  closeShipDnModal();
  openShipSelectedIds.clear();
  const closedCount = (data.lines || []).filter((ln) => ln.closed).length;
  showListMsg(
    `✓ 已合并出货 ${items.length} 条料号（客户：${data.customer || ""}）${closedCount ? `，其中 ${closedCount} 条已结案` : ""}`,
    true
  );
  await loadLines();
  openDeliveryNoteAfterShip(data);
}

function bindShipDnModal() {
  document.getElementById("openBatchShipBtn")?.addEventListener("click", () => {
    openBatchShipModal();
  });
  document.getElementById("shipDnCancel")?.addEventListener("click", closeShipDnModal);
  document.getElementById("shipDnConfirm")?.addEventListener("click", confirmShipFromModal);
  document.getElementById("shipDnBackdrop")?.addEventListener("click", (e) => {
    if (e.target?.id === "shipDnBackdrop") closeShipDnModal();
  });
  document.getElementById("shipDnReloadDraft")?.addEventListener("click", async () => {
    if (_shipDnUiMode !== "wkt_standard") return;
    if (_shipDnMode === "batch") {
      try {
        await loadShipDnDraftBatch();
      } catch (err) {
        alert(err.message || "刷新失败");
      }
      return;
    }
    const lineId = Number(document.getElementById("shipDnLineId")?.value);
    const qty = document.getElementById("shipDnQty")?.value.trim().replace(/,/g, "");
    if (!lineId || !qty) {
      alert("请先填写本次出货数量");
      return;
    }
    try {
      await loadShipDnDraft(lineId, qty);
    } catch (err) {
      alert(err.message || "刷新失败");
    }
  });
  document.getElementById("shipDnQty")?.addEventListener("change", () => {
    const q = document.getElementById("shipDnQty")?.value.trim().replace(/,/g, "");
    const win = getShipDnFrameWin();
    if (win?.syncLineQtyFromParent && q) win.syncLineQtyFromParent(q);
  });
}

async function shipOpenLine(lineId, ln) {
  await openShipDnModal(lineId, ln);
}

async function forceCloseOpenLine(lineId, ln) {
  const openDisp = calcOpenDisplay(ln.po_qty, ln.shipped_qty);
  const msg =
    `确认对以下料号强制结案？\n\n客户：${ln.customer || "—"}\n订单号：${ln.order_no || "—"}\n品名：${ln.product_spec || "—"}\n当前未结：${openDisp}\n\n强制结案不记出货、不纳入对账，将归入「强制结案订单」。`;
  if (!confirm(msg)) return;
  const res = await fetch("/api/lines/" + lineId + "/force-close", { method: "POST" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    alert(data.error || "强制结案失败");
    return;
  }
  openShipSelectedIds.delete(lineId);
  showListMsg("✓ 已强制结案，该料号已归入「强制结案订单」", true);
  await loadLines();
}

/* ========== 对账 ========== */
async function initReconcileFilters() {
  const dueSel = document.getElementById("reconcileDueMonthFilter");
  const shipSel = document.getElementById("reconcileShipMonthFilter");
  if (!dueSel || !shipSel) return;
  try {
    const res = await fetch("/api/reconciliation/due-months");
    const data = await res.json();
    if (res.ok && Array.isArray(data.months)) {
      const currentDue = dueSel.value;
      dueSel.innerHTML = "<option value=\"\">全部</option>";
      data.months.forEach((m) => {
        dueSel.appendChild(new Option(m, m));
      });
      if (currentDue) dueSel.value = currentDue;
    }
    const linesRes = await fetch("/api/reconciliation/lines");
    const linesData = await linesRes.json();
    if (linesRes.ok && Array.isArray(linesData.lines)) {
      const currentShip = shipSel.value;
      const shipMonths = [...new Set(linesData.lines.map((r) => r.ship_month).filter(Boolean))]
        .sort()
        .reverse();
      shipSel.innerHTML = "<option value=\"\">全部</option>";
      shipMonths.forEach((m) => {
        shipSel.appendChild(new Option(m, m));
      });
      if (currentShip) shipSel.value = currentShip;
    }
  } catch (e) {
    /* ignore */
  }
}

async function updateReconcileSummary(params, detailTotal) {
  const el = document.getElementById("reconcileAmountSummary");
  if (!el) return;
  if (reconcileDetailMode && detailTotal != null) {
    el.textContent = `本组应收 ¥${fmtSmart(String(detailTotal), 2)}`;
    return;
  }
  try {
    const res = await fetch("/api/reconciliation/customer-months?" + params.toString());
    const data = await res.json();
    if (!res.ok || !data.ok) {
      el.textContent = "";
      return;
    }
    const total = data.total_amount || "0";
    const n = new Set((data.rows || []).map((r) => r.customer)).size;
    el.textContent = `应收合计 ¥${total}（${n} 个客户）`;
  } catch (e) {
    el.textContent = "";
  }
}

async function initPayableFilters() {
  const settlementSel = document.getElementById("payableSettlementMonthFilter");
  const paymentSel = document.getElementById("payablePaymentMonthFilter");
  if (!settlementSel || !paymentSel) return;
  try {
    const [setRes, payRes] = await Promise.all([
      fetch("/api/payable/settlement-months"),
      fetch("/api/payable/payment-months"),
    ]);
    const setData = await setRes.json();
    const payData = await payRes.json();
    if (setRes.ok && Array.isArray(setData.months)) {
      const current = settlementSel.value;
      settlementSel.innerHTML = "<option value=\"\">全部</option>";
      setData.months.forEach((m) => settlementSel.appendChild(new Option(m, m)));
      if (current) settlementSel.value = current;
    }
    if (payRes.ok && Array.isArray(payData.months)) {
      const current = paymentSel.value;
      paymentSel.innerHTML = "<option value=\"\">全部</option>";
      payData.months.forEach((m) => paymentSel.appendChild(new Option(m, m)));
      if (current) paymentSel.value = current;
    }
  } catch (_e) {
    /* ignore */
  }
}

async function updatePayableSummary(params, detailTotal) {
  const el = document.getElementById("payableAmountSummary");
  if (!el) return;
  if (payableDetailMode && detailTotal != null) {
    el.textContent = `本组应付 ¥${fmtSmart(String(detailTotal), 2)}`;
    return;
  }
  try {
    const res = await fetch("/api/payable/supplier-months?" + params.toString());
    const data = await res.json();
    if (!res.ok || !data.ok) {
      el.textContent = "";
      return;
    }
    const total = data.total_amount || "0";
    const n = new Set((data.rows || []).map((r) => r.supplier)).size;
    el.textContent = `应付合计 ¥${total}（${n} 个供应商）`;
  } catch (_e) {
    el.textContent = "";
  }
}

/* ========== 已录入列表 ========== */
async function loadLines() {
  const meta = SUBMODULES[currentSubmodule] || SUBMODULES.detail;
  const view = meta.view || "all";
  const viewKey = currentSubmodule;
  const isShippedView = viewKey === "shipped";
  const isReconcileView = viewKey === "reconcile";
  const isPayableView = viewKey === "payable";
  let lines = [];
  if (isPayableView) {
    updatePayableToolbarState();
    if (payableDetailMode) {
      const params = new URLSearchParams();
      const receiveFrom = document.getElementById("payableReceiveFrom")?.value || "";
      const receiveTo = document.getElementById("payableReceiveTo")?.value || "";
      params.set("supplier", payableDetailSupplier);
      params.set("payment_month", payableDetailMonth);
      if (receiveFrom) params.set("receive_from", receiveFrom);
      if (receiveTo) params.set("receive_to", receiveTo);
      const res = await fetch("/api/payable/lines?" + params.toString());
      if (res.ok) {
        const raw = await res.json();
        lines = Array.isArray(raw.lines) ? raw.lines : [];
      }
      dueOutlookCache = null;
      const detailTotal = lines.reduce((s, r) => s + (parseFloat(r.amount) || 0), 0);
      const el = document.getElementById("payableAmountSummary");
      if (el) el.textContent = `本组应付 ¥${fmtSmart(String(detailTotal), 2)}`;
    } else {
      const res = await fetch("/api/payable/due-outlook");
      if (res.ok) {
        const raw = await res.json();
        if (raw.ok) {
          dueOutlookCache = raw;
          updateDueOutlookSummary("payable", raw);
        }
      }
      lines = [];
    }
  } else if (isReconcileView) {
    updateReconcileToolbarState();
    if (reconcileDetailMode) {
      const params = new URLSearchParams();
      params.set("customer", reconcileDetailCustomer);
      params.set("collection_month", reconcileDetailMonth);
      const res = await fetch("/api/reconciliation/lines?" + params.toString());
      if (res.ok) {
        const raw = await res.json();
        lines = Array.isArray(raw.lines) ? raw.lines : [];
      }
      dueOutlookCache = null;
      const detailTotal = lines.reduce((s, r) => s + (parseFloat(r.amount) || 0), 0);
      const el = document.getElementById("reconcileAmountSummary");
      if (el) el.textContent = `本组应收 ¥${fmtSmart(String(detailTotal), 2)}`;
    } else {
      const res = await fetch("/api/reconciliation/due-outlook");
      if (res.ok) {
        const raw = await res.json();
        if (raw.ok) {
          dueOutlookCache = raw;
          updateDueOutlookSummary("reconcile", raw);
        }
      }
      lines = [];
    }
  } else if (isShippedView) {
    const res = await fetch("/api/shipment-events");
    if (res.ok) {
      const raw = await res.json();
      lines = Array.isArray(raw) ? raw.filter(isShipmentRecord) : [];
    }
  } else {
    const params = new URLSearchParams();
    if (view && view !== "all") params.set("view", view);
    const res = await fetch("/api/lines?" + params.toString());
    lines = await res.json();
  }
  listRowsCache = lines;
  pruneListColFilters();
  updateListFilterBtnStates();
  renderListFromCache();
}

function pruneListColFilters() {
  const viewKey = currentSubmodule;
  const cols = listTableCols(viewKey);
  const filters = getListColFilters();
  cols.forEach((col) => {
    const set = filters[col.f];
    if (!(set instanceof Set)) return;
    const all = new Set(getColumnUniqueValues(col, viewKey));
    const next = new Set([...set].filter((v) => all.has(v)));
    if (!next.size || next.size >= all.size) delete filters[col.f];
    else filters[col.f] = next;
  });
}

function renderListFromCache() {
  const meta = SUBMODULES[currentSubmodule] || SUBMODULES.detail;
  const viewKey = currentSubmodule;
  const isShippedView = viewKey === "shipped";
  const isReconcileView = viewKey === "reconcile";
  const isPayableView = viewKey === "payable";
  const cols = listTableCols(viewKey);
  const filtered = applyListColFilters(listRowsCache, viewKey);
  const tbody = document.getElementById("lineListBody");
  const label = meta.summary || "记录";
  const total = listRowsCache.length;
  const shown = filtered.length;
  const filterNote = hasActiveListColFilters() && shown !== total ? `，筛选后 ${shown} 条` : "";
  const summaryEl = document.getElementById("listSummary");
  if (summaryEl && !isReconcileView && !isPayableView) {
    const sortNote = isShippedView
      ? "（最新出货在上）"
      : viewKey === "closed"
        ? "（最新出货在上）"
        : viewKey === "closedForced"
          ? "（最新强制结案在上）"
          : "（最新录入在最上）";
    summaryEl.textContent = isShippedView
      ? `${meta.title}：共 ${total} 条${label}${filterNote}${sortNote}`
      : `${meta.title}：共 ${total} 条${label}${filterNote}${sortNote}`;
  }
  if (isReconcileView && !reconcileDetailMode && dueOutlookCache) {
    renderDueOutlook("reconcile", dueOutlookCache);
    return;
  }
  if (isPayableView && !payableDetailMode && dueOutlookCache) {
    renderDueOutlook("payable", dueOutlookCache);
    return;
  }
  if (!filtered.length) {
    listEditingId = null;
    const emptyMsg = total
      ? "当前筛选下无匹配记录，请调整表头 ▾ 或点「清空筛选」。"
      : isShippedView
        ? "暂无出货记录。请在「未结订单」点「出货」登记；历史出货导入功能待上线。"
        : isReconcileView
          ? "暂无应收数据（无出货记录或当前筛选无匹配）。"
          : isPayableView
            ? "暂无应付数据（无回货记录或当前筛选无匹配）。"
            : "暂无记录";
    const colSpan = listTableColSpan(viewKey, cols.length);
    tbody.innerHTML = `<tr><td colspan="${colSpan}" class="empty-cell">${emptyMsg}</td></tr>`;
    return;
  }
  if (isReconcileView) {
    if (reconcileDetailMode) {
      let lineSeq = 0;
      tbody.innerHTML = filtered
        .map((row) => {
          lineSeq += 1;
          const rowCls = [
            isShipmentTodayHighlight(row) ? "row-today-highlight" : "",
            "reconcile-detail-row",
          ]
            .filter(Boolean)
            .join(" ");
          return `<tr data-shipment-id="${row.id}"${rowCls ? ` class="${rowCls}"` : ""}><td class="list-td-seq">${lineSeq}</td>${cols
            .map((c) => `<td class="${listTdClass(c)}">${reconcileCellValue(row, c)}</td>`)
            .join("")}</tr>`;
        })
        .join("");
      if (summaryEl) {
        summaryEl.textContent = `${meta.title}：共 ${total} 条明细${filterNote}（${reconcileDetailCustomer} · ${reconcileDetailMonth}）`;
      }
      tbody.querySelectorAll("tr.reconcile-detail-row td:not(:first-child)").forEach(bindHoverTip);
      return;
    }
  }
  if (isPayableView) {
    if (payableDetailMode) {
      let lineSeq = 0;
      tbody.innerHTML = filtered
        .map((row) => {
          lineSeq += 1;
          const rowCls = [
            isShipmentTodayHighlight(row) ? "row-today-highlight" : "",
            "reconcile-detail-row",
          ]
            .filter(Boolean)
            .join(" ");
          return `<tr data-movement-id="${row.id}"${rowCls ? ` class="${rowCls}"` : ""}><td class="list-td-seq">${lineSeq}</td>${cols
            .map((c) => `<td class="${listTdClass(c)}">${payableCellValue(row, c)}</td>`)
            .join("")}</tr>`;
        })
        .join("");
      if (summaryEl) {
        summaryEl.textContent = `${meta.title}：共 ${total} 条明细${filterNote}（${payableDetailSupplier} · ${payableDetailMonth}）`;
      }
      tbody.querySelectorAll("tr.reconcile-detail-row td:not(:first-child)").forEach(bindHoverTip);
      return;
    }
  }
  if (isShippedView) {
    tbody.innerHTML = filtered
      .map((ev, idx) => {
        const rowCls = isShipmentTodayHighlight(ev) ? "row-today-highlight" : "";
        return `<tr data-shipment-id="${ev.id}"${rowCls ? ` class="${rowCls}"` : ""}><td class="list-td-seq">${idx + 1}</td>${cols
          .map((c) => `<td class="${listTdClass(c)}">${shipmentCellValue(ev, c)}</td>`)
          .join("")}<td class="action-cell">${shipmentRowActions(ev)}</td></tr>`;
      })
      .join("");
    tbody.querySelectorAll("tr td:not(:first-child)").forEach(bindHoverTip);
    return;
  }
  tbody.innerHTML = filtered
    .map((ln, idx) => {
      const editing = listEditingId === ln.id;
      const cells = editing
        ? LIST_DETAIL_COLS.map((c) => renderListEditCell(ln, c)).join("")
        : cols.map((c) => `<td class="${listTdClass(c)}">${cellValue(ln, c)}</td>`).join("");
      const actions = editing
        ? `<button type="button" class="btn btn-sm btn-primary save-list-btn" data-id="${ln.id}">保存</button>
           <button type="button" class="btn btn-sm btn-outline cancel-list-btn" data-id="${ln.id}">取消</button>`
        : renderListActions(ln, viewKey);
      const rowCls = [
        editing ? "row-editing" : "",
        isOrderLineTodayHighlight(ln, viewKey) ? "row-today-highlight" : "",
        viewKey === "open" ? openDeliveryWarningClass(ln) : "",
        viewKey === "open" && isOrderDateOlderThanMonths(ln.order_date) ? "row-order-overdue" : "",
      ]
        .filter(Boolean)
        .join(" ");
      return `<tr data-line-id="${ln.id}"${rowCls ? ` class="${rowCls}"` : ""}>
      ${renderOpenSeqCell(ln, idx)}${cells}${listShowsActionColumn(viewKey) ? `<td class="action-cell">${actions}</td>` : ""}</tr>`;
    })
    .join("");

  const lineById = Object.fromEntries(filtered.map((ln) => [ln.id, ln]));
  tbody.querySelectorAll(".ship-open-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = Number(btn.dataset.id);
      const ln = lineById[id];
      if (ln) shipOpenLine(id, ln);
    });
  });
  tbody.querySelectorAll(".force-close-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = Number(btn.dataset.id);
      const ln = lineById[id];
      if (ln) forceCloseOpenLine(id, ln);
    });
  });
  tbody.querySelectorAll(".edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (listEditingId && listEditingId !== Number(btn.dataset.id)) {
        if (!confirm("当前有未保存的修改，是否放弃并编辑另一行？")) return;
      }
      startListEdit(Number(btn.dataset.id));
    });
  });
  tbody.querySelectorAll(".save-list-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tr = btn.closest("tr");
      if (tr) saveListRow(Number(btn.dataset.id), tr);
    });
  });
  tbody.querySelectorAll(".cancel-list-btn").forEach((btn) => {
    btn.addEventListener("click", cancelListEdit);
  });
  tbody.querySelectorAll(".delete-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("确认删除 ID=" + btn.dataset.id + "？")) return;
      if (listEditingId === Number(btn.dataset.id)) listEditingId = null;
      const res = await fetch("/api/lines/" + btn.dataset.id, { method: "DELETE" });
      if (res.ok) loadLines();
      else alert((await res.json()).error || "删除失败");
    });
  });
  if (viewKey === "open" && FEATURE_BATCH_SHIP) {
    tbody.querySelectorAll(".open-ship-check").forEach((cb) => {
      cb.addEventListener("change", () => {
        const id = Number(cb.dataset.id);
        if (cb.checked) openShipSelectedIds.add(id);
        else openShipSelectedIds.delete(id);
        updateOpenBatchShipUi();
      });
    });
    updateOpenBatchShipUi();
  }
  tbody.querySelectorAll("tr:not(.row-editing) td:not(.action-cell)").forEach(bindHoverTip);
  tbody.querySelectorAll("tr.row-editing").forEach((tr) => bindListEditRow(tr));
  if (highlightedLineIds.size) scrollToFirstHighlighted();
}

document.getElementById("clearListFiltersBtn")?.addEventListener("click", clearListColFilters);
document.getElementById("reconcileDueMonthFilter")?.addEventListener("change", () => {
  if (currentSubmodule === "reconcile") loadLines();
});
document.getElementById("reconcileShipMonthFilter")?.addEventListener("change", () => {
  if (currentSubmodule === "reconcile") loadLines();
});
document.getElementById("reconcileRefreshBtn")?.addEventListener("click", () => {
  if (currentSubmodule === "reconcile") loadLines();
});
document.getElementById("reconcileBackBtn")?.addEventListener("click", () => {
  if (currentSubmodule === "reconcile" && reconcileDetailMode) closeReconcileDetail();
});
document.getElementById("payableSettlementMonthFilter")?.addEventListener("change", () => {
  if (currentSubmodule === "payable") loadLines();
});
document.getElementById("payablePaymentMonthFilter")?.addEventListener("change", () => {
  if (currentSubmodule === "payable") loadLines();
});
document.getElementById("payableReceiveFrom")?.addEventListener("change", () => {
  if (currentSubmodule === "payable" && payableDetailMode) loadLines();
});
document.getElementById("payableReceiveTo")?.addEventListener("change", () => {
  if (currentSubmodule === "payable" && payableDetailMode) loadLines();
});
document.getElementById("payableRefreshBtn")?.addEventListener("click", () => {
  if (currentSubmodule === "payable") loadLines();
});
document.getElementById("payableBackBtn")?.addEventListener("click", () => {
  if (currentSubmodule === "payable" && payableDetailMode) closePayableDetail();
});
document.getElementById("lineListBody")?.addEventListener("click", (e) => {
  const payableBtn = e.target.closest(".payable-detail-btn");
  if (payableBtn && currentSubmodule === "payable") {
    e.preventDefault();
    openPayableDetail(payableBtn.dataset.supplier || "", payableBtn.dataset.month || "");
    return;
  }
  const returnBtn = e.target.closest(".shipment-return-btn");
  if (returnBtn && currentSubmodule === "shipped") {
    e.preventDefault();
    const eventId = Number(returnBtn.dataset.eventId);
    if (eventId) {
      returnShipmentToOpen(eventId).catch((err) => alert(err.message || "撤销失败"));
    }
    return;
  }
  const openBtn = e.target.closest(".custom-excel-open-btn");
  if (openBtn && currentSubmodule === "shipped") {
    e.preventDefault();
    const eventId = Number(openBtn.dataset.eventId);
    const regenerate = openBtn.dataset.regenerate !== "0";
    if (eventId) {
      openCustomExcelLocally(eventId, null, regenerate).catch((err) => alert(err.message || "无法打开 Excel"));
    }
    return;
  }
  const btn = e.target.closest(".reconcile-detail-btn");
  if (!btn || currentSubmodule !== "reconcile") return;
  e.preventDefault();
  openReconcileDetail(btn.dataset.customer || "", btn.dataset.month || "");
});

/* ========== OCR 预览 ========== */
function setRecognizeProgress(pct, msg) {
  const box = document.getElementById("recognizeProgress");
  if (!box) return;
  box.classList.remove("is-hidden");
  document.getElementById("progressFill").style.width = Math.min(100, Math.max(0, pct)) + "%";
  document.getElementById("progressLabel").textContent = msg || "";
}

function hideRecognizeProgress() {
  const box = document.getElementById("recognizeProgress");
  if (box) box.classList.add("is-hidden");
  const fill = document.getElementById("progressFill");
  if (fill) fill.style.width = "0%";
}

function fieldLabel(f) {
  return (COLS.find((c) => c.f === f) || {}).label || f;
}

function fmtFieldDisplay(field, val) {
  if (val == null || val === "") return "（空）";
  if (field === "tax_rate") {
    const r = parseFloat(val);
    if (!isNaN(r)) return r <= 1 ? `${Math.round(r * 100)}%` : `${val}%`;
  }
  return String(val);
}

function scrollToValidation(row, field) {
  const tr = document.querySelector(`#previewBody tr[data-idx="${row - 1}"]`);
  if (!tr) return;
  const td = tr.querySelector(`[data-f="${field}"]`)?.closest("td") || tr;
  td.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
  td.classList.add("pv-flash-warn");
  setTimeout(() => td.classList.remove("pv-flash-warn"), 1600);
}

function hidePreview() {
  const area = document.getElementById("previewArea");
  area.classList.add("is-hidden");
  document.getElementById("previewBody").innerHTML = "";
  renderValidationSummary(null);
  renderOcrRawPanel(null);
}

function renderOcrRawPanel(ocr, expanded) {
  const el = document.getElementById("ocrRawPanel");
  if (!el) return;
  if (!ocr) {
    el.classList.add("is-hidden");
    el.innerHTML = "";
    return;
  }
  const show = expanded !== false;
  el.classList.toggle("is-hidden", !show);
  if (!show) {
    el.innerHTML = "";
    return;
  }
  const truncNote = ocr.truncated
    ? `<p class="ocr-raw-trunc">原文较长，仅显示前 20000 字符。</p>`
    : "";
  el.innerHTML =
    `<div class="ocr-raw-head">` +
    `<strong>OCR 识别原文</strong>` +
    `<span class="ocr-raw-hint">${esc(ocr.scheme || "RapidOCR")}</span>` +
    `<button type="button" class="btn btn-ghost btn-sm" id="ocrRawCloseBtn">收起</button>` +
    `</div>` +
    truncNote +
    `<pre class="ocr-raw-pre ocr-raw-pre-single">${esc(ocr.text || "（空）")}</pre>`;
  document.getElementById("ocrRawCloseBtn")?.addEventListener("click", () => {
    _ocrRawExpanded = false;
    renderOcrRawPanel(ocr, false);
    const toggle = document.getElementById("ocrRawToggleBtn");
    if (toggle) toggle.textContent = "查看 OCR 原文";
  });
}

let _lastOcrText = null;
let _ocrRawExpanded = false;
let _ocrSourceFiles = [];
let _ocrSourceIndex = 0;
let _ocrZoom = 1;

function revokeOcrSourceUrls() {
  _ocrSourceFiles.forEach((f) => {
    if (f.blobUrl) URL.revokeObjectURL(f.blobUrl);
  });
  _ocrSourceFiles = [];
  _ocrSourceIndex = 0;
  _ocrZoom = 1;
}

function buildOcrSourceEntriesFromFiles(files) {
  revokeOcrSourceUrls();
  _ocrSourceFiles = files.map((file) => {
    const name = file.name || "未命名";
    const type = file.type || "";
    const isPdf = /\.pdf$/i.test(name) || type === "application/pdf";
    const isImage =
      /^image\//i.test(type) ||
      /\.(png|jpe?g|bmp|gif|tif?f|webp)$/i.test(name);
    return {
      name,
      blobUrl: URL.createObjectURL(file),
      previewUrls: null,
      isPdf,
      isImage,
      pageIndex: 0,
    };
  });
  return _ocrSourceFiles;
}

function setOcrSourceEntries(entries) {
  revokeOcrSourceUrls();
  _ocrSourceFiles = (entries || []).map((e) => ({
    name: e.name || "未命名",
    blobUrl: e.blobUrl || "",
    previewUrls: e.previewUrls || null,
    isPdf: !!e.isPdf,
    isImage: !!e.isImage,
    pageIndex: 0,
  }));
}

function getOcrSourceViewerEl() {
  return document.getElementById("ocrSourceViewer");
}

function getOcrSourceWrapEl() {
  return document.getElementById("ocrSourceViewerWrap");
}

function applyOcrZoomToImage() {
  const img = getOcrSourceViewerEl()?.querySelector("img.preview-page");
  if (!img || !img.naturalWidth) return;
  img.style.width = Math.round(img.naturalWidth * _ocrZoom) + "px";
  img.style.height = Math.round(img.naturalHeight * _ocrZoom) + "px";
}

function fitOcrSourceWidth() {
  const img = getOcrSourceViewerEl()?.querySelector("img.preview-page");
  const wrap = getOcrSourceWrapEl();
  if (!img || !wrap || !img.naturalWidth) return;
  const available = wrap.clientWidth - 32;
  _ocrZoom = Math.max(0.3, Math.min(3, available / img.naturalWidth));
  applyOcrZoomToImage();
}

function changeOcrZoom(delta) {
  _ocrZoom = Math.max(0.3, Math.min(3, _ocrZoom + delta));
  applyOcrZoomToImage();
}

function openOcrSourceInNewTab() {
  const item = _ocrSourceFiles[_ocrSourceIndex];
  const url = item?.blobUrl || item?.previewUrls?.[item.pageIndex || 0];
  if (url) window.open(url, "_blank", "noopener");
}

function updateOcrPageSelect(item) {
  const pageSel = document.getElementById("ocrSourcePageSelect");
  if (!pageSel) return;
  const urls = item?.previewUrls;
  if (urls && urls.length > 1) {
    pageSel.classList.remove("is-hidden");
    pageSel.innerHTML = urls
      .map((_, i) => `<option value="${i}">第 ${i + 1} 页 / 共 ${urls.length} 页</option>`)
      .join("");
    pageSel.value = String(item.pageIndex || 0);
    if (!pageSel.dataset.bound) {
      pageSel.dataset.bound = "1";
      pageSel.addEventListener("change", () => {
        const idx = _ocrSourceIndex;
        if (_ocrSourceFiles[idx]) {
          _ocrSourceFiles[idx].pageIndex = Number(pageSel.value) || 0;
          _ocrZoom = 1;
          showOcrSourceAt(idx);
        }
      });
    }
  } else {
    pageSel.classList.add("is-hidden");
    pageSel.innerHTML = "";
  }
}

function mountOcrPreviewImage(viewer, item, src) {
  const img = document.createElement("img");
  img.className = "preview-page";
  img.alt = item.name || "订单原件";
  img.src = src;
  const inner = document.createElement("div");
  inner.className = "ocr-source-inner";
  inner.appendChild(img);
  viewer.innerHTML = "";
  viewer.appendChild(inner);
  const onReady = () => {
    _ocrZoom = 1;
    applyOcrZoomToImage();
  };
  img.addEventListener("load", onReady, { once: true });
  if (img.complete) onReady();
}

function bindOcrSourceTools() {
  document.getElementById("ocrZoomIn")?.addEventListener("click", () => changeOcrZoom(0.15));
  document.getElementById("ocrZoomOut")?.addEventListener("click", () => changeOcrZoom(-0.15));
  document.getElementById("ocrZoomReset")?.addEventListener("click", fitOcrSourceWidth);
  document.getElementById("ocrOpenNew")?.addEventListener("click", openOcrSourceInNewTab);
  document.getElementById("ocrSourceToggle")?.addEventListener("click", () => {
    const block = document.getElementById("ocrSourceAside");
    const btn = document.getElementById("ocrSourceToggle");
    if (!block || !btn) return;
    block.classList.toggle("is-collapsed");
    btn.textContent = block.classList.contains("is-collapsed") ? "展开原件" : "收起原件";
  });
}

function showOcrSourceAt(index) {
  const viewer = getOcrSourceViewerEl();
  const select = document.getElementById("ocrSourceSelect");
  if (!viewer || !_ocrSourceFiles.length) {
    if (viewer) viewer.innerHTML = '<p class="ocr-source-empty">暂无原件</p>';
    return;
  }
  index = Math.max(0, Math.min(index, _ocrSourceFiles.length - 1));
  _ocrSourceIndex = index;
  if (select && select.value !== String(index)) select.value = String(index);
  const item = _ocrSourceFiles[index];
  updateOcrPageSelect(item);
  const pageIdx = item.pageIndex || 0;
  const previewSrc = item.previewUrls?.[pageIdx];
  if (previewSrc) {
    mountOcrPreviewImage(viewer, item, previewSrc);
  } else if (item.isPdf && item.blobUrl) {
    viewer.innerHTML =
      `<div class="ocr-source-inner"><iframe title="${esc(item.name)}" src="${item.blobUrl}"></iframe></div>`;
  } else if (item.isImage && item.blobUrl) {
    mountOcrPreviewImage(viewer, item, item.blobUrl);
  } else if (item.blobUrl) {
    viewer.innerHTML =
      `<p class="ocr-source-empty">此格式无法在浏览器内预览<br/>` +
      `<a href="${item.blobUrl}" download="${esc(item.name)}">下载 ${esc(item.name)}</a></p>`;
  } else {
    viewer.innerHTML = '<p class="ocr-source-empty">暂无原件预览</p>';
  }
}

function renderOcrSourcePanel(entries) {
  if (Array.isArray(entries) && entries.length && entries[0].previewUrls !== undefined) {
    setOcrSourceEntries(entries);
  } else {
    buildOcrSourceEntriesFromFiles(entries || []);
  }
  const select = document.getElementById("ocrSourceSelect");
  if (select) {
    if (_ocrSourceFiles.length > 1) {
      select.classList.remove("is-hidden");
      select.innerHTML = _ocrSourceFiles
        .map((f, i) => `<option value="${i}">${esc(f.name)}</option>`)
        .join("");
      if (!select.dataset.bound) {
        select.dataset.bound = "1";
        select.addEventListener("change", () => {
          showOcrSourceAt(Number(select.value) || 0);
        });
      }
    } else {
      select.classList.add("is-hidden");
      select.innerHTML = "";
    }
  }
  showOcrSourceAt(0);
}

function focusOcrSourceByName(fileName) {
  if (!fileName || !_ocrSourceFiles.length) return;
  const idx = _ocrSourceFiles.findIndex((f) => f.name === fileName);
  if (idx >= 0) {
    showOcrSourceAt(idx);
    document.getElementById("ocrSourceAside")?.classList.remove("is-collapsed");
    const toggle = document.getElementById("ocrSourceToggle");
    if (toggle) toggle.textContent = "收起原件";
    document.getElementById("ocrSourceAside")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function renderValidationSummary(v, lines, ocrText) {
  const el = document.getElementById("validationSummary");
  if (!el) return;
  if (!v) {
    el.classList.add("is-hidden");
    el.innerHTML = "";
    _lastOcrText = null;
    _ocrRawExpanded = false;
    return;
  }
  if (ocrText) _lastOcrText = ocrText;
  el.classList.remove("is-hidden");
  let details = v.warn_details || [];
  if (!details.length && lines) {
    lines.forEach((ln, i) => {
      COLS.forEach((c) => {
        const fv = ln._validate?.fields?.[c.f];
        if (fv?.status === "warn") {
          details.push({
            row: i + 1,
            field: c.f,
            value: fv.value ?? ln[c.f],
            message: fv.message ?? "",
            source_file: ln._source_file || "",
          });
        }
      });
    });
  }
  const hasIssue = details.length > 0;
  el.className = "verify-summary " + (hasIssue ? "verify-warn" : "verify-ok");
  let html =
    `<div class="verify-summary-head">` +
    `<strong>识别校验结果</strong> ` +
    (v.file_count > 1 ? `共 ${v.file_count} 个文件 · ` : "") +
    `${esc(v.ocr_scheme || "RapidOCR")} · ` +
    `${v.ok_rows ?? 0}/${v.total_rows ?? 0} 行通过规则校验` +
    (_lastOcrText
      ? ` · <button type="button" class="verify-link-btn" id="ocrRawToggleBtn">` +
        `${_ocrRawExpanded ? "收起 OCR 原文" : "查看 OCR 原文"}</button>`
      : "") +
    `</div>`;
  if (details.length) {
    html += `<p class="verify-mismatch-title">以下 ${details.length} 处需重点核对（点击可定位到表格）：</p>`;
    html += `<ul class="verify-mismatch-list">`;
    details.forEach((d) => {
      const label = fieldLabel(d.field);
      const val = fmtFieldDisplay(d.field, d.value);
      const src = d.source_file ? `（${d.source_file}）` : "";
      html +=
        `<li><button type="button" class="verify-mismatch-item" data-row="${d.row}" data-field="${esc(d.field)}">` +
        `第 ${d.row} 行${esc(src)} · ${esc(label)}：「${esc(val)}」— ${esc(d.message || "请核对")}` +
        `</button></li>`;
    });
    html += `</ul>`;
  } else {
    html += `<p class="verify-ok-note">关键字段格式校验通过，请快速浏览后提交。</p>`;
  }
  (v.warnings || []).forEach((w) => {
    html += `<div class="verify-note">${esc(w)}</div>`;
  });
  el.innerHTML = html;
  el.querySelectorAll(".verify-mismatch-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      scrollToValidation(parseInt(btn.dataset.row, 10), btn.dataset.field);
    });
  });
  document.getElementById("ocrRawToggleBtn")?.addEventListener("click", () => {
    _ocrRawExpanded = !_ocrRawExpanded;
    renderOcrRawPanel(_lastOcrText, _ocrRawExpanded);
    const toggle = document.getElementById("ocrRawToggleBtn");
    if (toggle) toggle.textContent = _ocrRawExpanded ? "收起 OCR 原文" : "查看 OCR 原文";
  });
  if (_ocrRawExpanded && _lastOcrText) {
    renderOcrRawPanel(_lastOcrText, true);
  }
}

function validateCellClass(ln, field) {
  const st = ln._validate?.fields?.[field]?.status;
  if (st === "warn") return "pv-cell pv-warn";
  return "pv-cell";
}

function mergeValidationBatch(acc, one, rowOffset, filename) {
  if (!one) return acc;
  const details = (one.warn_details || []).map((d) => ({
    ...d,
    row: d.row + rowOffset,
    source_file: filename,
  }));
  if (!acc) {
    return {
      ...one,
      warn_details: details,
      file_count: 1,
      source_files: [filename],
    };
  }
  return {
    ocr_scheme: acc.ocr_scheme || one.ocr_scheme,
    total_rows: (acc.total_rows || 0) + (one.total_rows || 0),
    ok_rows: (acc.ok_rows || 0) + (one.ok_rows || 0),
    warn_rows: (acc.warn_rows || 0) + (one.warn_rows || 0),
    warn_fields: (acc.warn_fields || 0) + (one.warn_fields || 0),
    warn_details: [...(acc.warn_details || []), ...details],
    warnings: [...(acc.warnings || []), ...(one.warnings || []).map((w) => `${filename}：${w}`)],
    file_count: (acc.file_count || 0) + 1,
    source_files: [...(acc.source_files || []), filename],
  };
}

function mergeOcrTextBatch(acc, one, filename) {
  if (!one) return acc;
  const block = `===== ${filename} · ${one.scheme || "OCR"} =====\n${one.text || ""}`;
  if (!acc) {
    return {
      scheme: one.scheme,
      text: block,
      truncated: !!one.truncated,
      file_count: 1,
    };
  }
  return {
    scheme: acc.scheme || one.scheme,
    text: `${acc.text || ""}\n\n${block}`,
    truncated: acc.truncated || one.truncated,
    file_count: (acc.file_count || 0) + 1,
  };
}

async function pollRecognizeJob(jobId, onProgress) {
  while (true) {
    await new Promise((r) => setTimeout(r, 450));
    const stRes = await fetch("/api/lines/recognize/" + encodeURIComponent(jobId));
    const data = await stRes.json();
    if (!stRes.ok) throw new Error(data.error || "查询进度失败");
    if (onProgress) onProgress(data.progress || 0, data.message || "识别中…");
    if (data.status === "done") return data;
    if (data.status === "error") throw new Error(data.error || data.message || "识别失败");
  }
}

async function recognizeOneFile(file, fileIndex, totalFiles, onProgress) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/api/lines/recognize", { method: "POST", body: fd });
  const start = await res.json();
  if (!res.ok) throw new Error(start.error || "识别失败");
  if (!start.job_id) throw new Error("未收到任务编号");
  return pollRecognizeJob(start.job_id, (pct, msg) => {
    if (onProgress) {
      const overall = Math.round((fileIndex / totalFiles) * 100 + pct / totalFiles);
      onProgress(overall, `[${fileIndex + 1}/${totalFiles}] ${file.name} — ${msg}`);
    }
  });
}

function renderPreview(lines, validation, ocrText, batchMeta) {
  const tbody = document.getElementById("previewBody");
  const batchHint = document.getElementById("previewBatchHint");
  const multiFile = (batchMeta?.fileCount || 0) > 1;
  if (batchMeta?.sourceEntries?.length) {
    renderOcrSourcePanel(batchMeta.sourceEntries);
  } else if (batchMeta?.files?.length) {
    renderOcrSourcePanel(batchMeta.files);
  }
  if (batchHint) {
    batchHint.textContent = multiFile ? ` · 共 ${batchMeta.fileCount} 个文件` : "";
  }
  showPreview();
  if (ocrText) _lastOcrText = ocrText;
  renderValidationSummary(validation, lines, ocrText);
  tbody.innerHTML = lines.map((ln, i) => {
    const rowWarn = ln._validate?.status === "warn";
    const cells = COLS.map((c, ci) => {
      const tdCls = validateCellClass(ln, c.f);
      if (c.f === "open_qty") {
        return `<td class="ro ${tdCls}">${calcOpenDisplay(ln.po_qty, ln.shipped_qty)}</td>`;
      }
      if (c.type === "readonly") {
        return `<td class="ro ${tdCls}">${calcOpenDisplay(ln.po_qty, ln.shipped_qty)}</td>`;
      }
      const type = c.type === "date" ? "date" : "text";
      const val = previewInputValue(ln, c);
      const fv = ln._validate?.fields?.[c.f];
      const isWarn = fv?.status === "warn";
      const hintHtml = isWarn
        ? `<span class="pv-hint">${esc(fv.message || "请核对")}</span>`
        : "";
      const sourceHtml = multiFile && ln._source_file && ci === 0
        ? `<span class="pv-source" data-file="${esc(ln._source_file)}" title="点击查看对应原件">${esc(ln._source_file)}</span>`
        : "";
      return `<td class="${tdCls}" data-verify-row="${i + 1}" data-verify-field="${c.f}">` +
        sourceHtml +
        (isWarn ? `<span class="pv-warn-badge">需核对</span>` : "") +
        `<input class="pv${isWarn ? " pv-warn-input" : ""}" data-f="${c.f}" type="${type}" value="${esc(String(val))}" />` +
        hintHtml +
        `</td>`;
    }).join("");
    return `<tr data-idx="${i}" class="${rowWarn ? "pv-row-warn" : ""}">${cells}<td><button type="button" class="btn-remove pv-remove">×</button></td></tr>`;
  }).join("");
  tbody.querySelectorAll(".pv").forEach((inp) => {
    const col = COLS.find((c) => c.f === inp.dataset.f);
    const tr = inp.closest("tr");
    const idx = tr ? parseInt(tr.dataset.idx, 10) : -1;
    const ln = idx >= 0 ? lines[idx] : null;
    const fv = ln?._validate?.fields?.[inp.dataset.f];
    if (fv?.status === "warn") {
      inp.dataset.hoverText = `${fieldLabel(inp.dataset.f)}：${fmtFieldDisplay(inp.dataset.f, inp.value)}\n${fv.message || "请核对"}`;
    }
    if (col && col.type === "decimal") attachDecimalLimit(inp, col.dp || 4);
    if (col && col.f === "tax_rate") attachDecimalLimit(inp, 2);
    bindHoverTip(inp);
    inp.addEventListener("input", () => {
      const tr = inp.closest("tr");
      const po = tr.querySelector('[data-f="po_qty"]')?.value;
      const sh = tr.querySelector('[data-f="shipped_qty"]')?.value;
      const openCell = tr.querySelector(".ro");
      if (openCell) openCell.textContent = calcOpenDisplay(po, sh);
    });
  });
  tbody.querySelectorAll(".ro").forEach(bindHoverTip);
  tbody.querySelectorAll(".pv-source").forEach((span) => {
    span.addEventListener("click", () => {
      focusOcrSourceByName(span.dataset.file || "");
    });
  });
  tbody.querySelectorAll(".pv-remove").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest("tr").remove();
      if (!tbody.querySelector("tr")) hidePreview();
    });
  });
}

function collectPreviewRows() {
  const rows = [];
  document.querySelectorAll("#previewBody tr").forEach((tr) => {
    const row = {};
    tr.querySelectorAll(".pv").forEach((inp) => {
      if (inp.dataset.f === "tax_rate") {
        const pct = parseFloat(inp.value);
        row.tax_rate = isNaN(pct) ? "0" : String(pct / 100);
      } else {
        row[inp.dataset.f] = inp.value;
      }
    });
    rows.push(row);
  });
  return rows;
}

document.getElementById("recognizeBtn").addEventListener("click", async () => {
  const fileInput = document.getElementById("orderFile");
  const msg = document.getElementById("recognizeMsg");
  const files = Array.from(fileInput.files || []);
  if (!files.length) { showMsg(msg, "请先选择文件", false); return; }
  const btn = document.getElementById("recognizeBtn");
  btn.disabled = true;
  showMsg(msg, "", true);
  setRecognizeProgress(0, "准备识别…");

  let allLines = [];
  let validation = null;
  let ocrText = null;
  const errors = [];
  let successCount = 0;
  const archivedPaths = [];
  const sourceEntries = [];

  try {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        const fd = new FormData();
        fd.append("file", file);
        const startRes = await fetch("/api/lines/recognize", { method: "POST", body: fd });
        const start = await startRes.json();
        if (!startRes.ok) throw new Error(start.error || "识别失败");
        if (!start.job_id) throw new Error("未收到任务编号");
        const result = await pollRecognizeJob(start.job_id, (pct, msg) => {
          setRecognizeProgress(
            Math.round((i / files.length) * 100 + pct / files.length),
            `[${i + 1}/${files.length}] ${file.name} — ${msg}`
          );
        });
        const previewPages = result.preview_pages || 0;
        const previewUrls =
          previewPages > 0
            ? Array.from(
                { length: previewPages },
                (_, p) => `/api/lines/recognize/${start.job_id}/preview/${p}`
              )
            : null;
        sourceEntries.push({
          name: file.name,
          blobUrl: URL.createObjectURL(file),
          previewUrls,
          isPdf: /\.pdf$/i.test(file.name),
          isImage:
            /^image\//i.test(file.type) ||
            /\.(png|jpe?g|bmp|gif|tif?f|webp)$/i.test(file.name),
        });
        if (result.archived_path) archivedPaths.push(result.archived_path);
        const lines = (result.lines || []).map((ln) => ({ ...ln, _source_file: file.name }));
        if (!lines.length) {
          errors.push(`${file.name}：未识别到料号行`);
          continue;
        }
        const rowOffset = allLines.length;
        allLines = allLines.concat(lines);
        validation = mergeValidationBatch(validation, result.validation, rowOffset, file.name);
        ocrText = mergeOcrTextBatch(ocrText, result.ocr_text, file.name);
        successCount++;
      } catch (err) {
        errors.push(`${file.name}：${err.message}`);
      }
    }

    if (!allLines.length) {
      showMsg(msg, errors.length ? errors.join("；") : "未识别到料号行", false);
      return;
    }

    renderPreview(allLines, validation || {}, ocrText, {
      fileCount: successCount,
      files,
      sourceEntries,
    });

    const valNote = (validation?.warn_fields || 0) > 0
      ? `，${validation.warn_fields} 处需核对（黄标记）`
      : "，规则校验通过";
    const fileNote = files.length > 1 ? `（${successCount}/${files.length} 个文件）` : "";
    let text = `✓ 共识别 ${allLines.length} 个料号${fileNote}${valNote}`;
    if (archivedPaths.length) {
      text += `；已归档 ${archivedPaths.length} 个文件到 orders/`;
    }
    if (errors.length) text += `；失败：${errors.join("；")}`;
    showMsg(msg, text, !errors.length || successCount > 0);
    fileInput.value = "";
  } catch (err) {
    showMsg(msg, "识别异常：" + err.message, false);
  } finally {
    btn.disabled = false;
    hideRecognizeProgress();
  }
});

document.getElementById("batchSubmitBtn")?.addEventListener("click", async () => {
  const rows = collectPreviewRows();
  if (!rows.length) return;
  let ok = 0, err = "", dupIds = [];
  const newIds = [];
  for (const row of rows) {
    const res = await fetch("/api/lines", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...row, notify_source: "OCR识别" }),
    });
    const created = await res.json();
    if (res.ok) {
      ok++;
      if (created.id) newIds.push(created.id);
    } else if (res.status === 409 && created.duplicate_id) {
      dupIds.push(created.duplicate_id);
      err = created.error || "存在重复料号行";
    } else {
      err = created.error || "提交失败";
      break;
    }
  }
  if (err && !ok) {
    alert(err + (dupIds.length ? "（已定位到已有记录）" : ""));
    if (dupIds.length) await switchToDetailWithNewLines(dupIds, "批量提交失败：以下料号行已存在，已高亮原记录");
    return;
  }
  if (err) alert("部分失败：" + err + "（已成功 " + ok + " 条）");
  else {
    hidePreview();
    document.getElementById("recognizeMsg").textContent = "✓ 已批量提交 " + ok + " 条";
    document.getElementById("recognizeMsg").className = "msg ok";
    await loadMaster();
    await switchToDetailWithNewLines(newIds);
  }
});

/* ========== 初始化 ========== */
renderHead("previewHead");
renderHead("listHead", ["序号"]);
renderExcelImportHead();

document.getElementById("excelPreviewArea")?.addEventListener("click", (e) => {
  if (e.target?.id !== "excelCopyBlockedBtn") return;
  const text = excelImportPreview?.blocked_report || "";
  if (!text) return;
  navigator.clipboard?.writeText(text).then(
    () => alert("已复制到剪贴板"),
    () => prompt("请手动复制：", text)
  );
});

(async () => {
  if (typeof bindDeliveryNoteAdmin === "function") bindDeliveryNoteAdmin();
  bindShipDnModal();
  scheduleTodayHighlightRefresh();
  bindOcrSourceTools();
  initListColFilterPanel();
  await loadMaster();
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById("orderDate").value = today;
  bindHoverTipAll(document.querySelector(".entry-card"));
  await switchSubmodule(parseSubmoduleFromHash());
})();
