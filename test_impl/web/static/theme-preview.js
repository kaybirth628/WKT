(function () {
  var OPTIONS = [
    {
      id: "classic",
      name: "经典 WKT",
      desc: "原演示版浅色蓝，熟悉、稳重，适合日常录入。",
      swatches: ["#2563eb", "#fafbfc", "#ffffff", "#1a1a1f"],
    },
    {
      id: "stripe",
      name: "Stripe 金融紫",
      desc: "支付大厂风格：冷灰底 + 电感紫，精致偏金融 SaaS。",
      swatches: ["#533afd", "#f6f9fc", "#ffffff", "#0d253d"],
    },
    {
      id: "ibm",
      name: "IBM 企业蓝",
      desc: "Carbon 设计：直角、高对比、黑白表头，传统企业 ERP 感。",
      swatches: ["#0f62fe", "#f4f4f4", "#ffffff", "#161616"],
    },
    {
      id: "notion",
      name: "Notion 协作",
      desc: "暖白纸张感 + 协作紫，柔和、阅读友好。",
      swatches: ["#5645d4", "#f7f7f5", "#ffffff", "#37352f"],
    },
    {
      id: "hp",
      name: "HP 科技蓝",
      desc: "惠普企业官网：电光蓝 CTA + 干净白底，制造业气质。",
      swatches: ["#024ad8", "#f7f7f7", "#ffffff", "#1a1a1a"],
    },
    {
      id: "minimal-white",
      name: "极简纯白",
      desc: "大面积纯白 + 细灰线；表头深蓝、按钮与当前菜单仍为 HP 科技蓝。",
      swatches: ["#024ad8", "#ffffff", "#e5e5e5", "#1a1a1a"],
    },
  ];

  var grid = document.getElementById("themeGrid");
  var banner = document.getElementById("themeCurrentBanner");
  var toast = document.getElementById("themeToast");

  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add("is-visible");
    clearTimeout(showToast._t);
    showToast._t = setTimeout(function () {
      toast.classList.remove("is-visible");
    }, 2200);
  }

  function updateBanner() {
    if (!banner) return;
    banner.innerHTML =
      "当前全站主题：<strong>" +
      WKTTheme.label(WKTTheme.current()) +
      "</strong> · 选用后刷新任意页面即可生效";
  }

  function markActive() {
    var cur = WKTTheme.current();
    document.querySelectorAll(".theme-option").forEach(function (el) {
      el.classList.toggle("is-active", el.dataset.themeId === cur);
    });
    updateBanner();
  }

  function miniPreviewHtml() {
    return (
      '<div class="theme-mini-frame">' +
      '<div class="theme-mini-sidebar">' +
      '<div class="theme-mini-logo">W</div>' +
      '<div class="theme-mini-nav">' +
      '<span class="theme-mini-pill">订单</span>' +
      '<span class="theme-mini-pill muted">列表</span>' +
      "</div></div>" +
      '<div class="theme-mini-body">' +
      '<div class="theme-mini-row">' +
      '<span class="theme-mini-input">客户名称</span>' +
      '<button type="button" class="theme-mini-btn">提交</button>' +
      "</div>" +
      '<table class="theme-mini-table"><thead><tr><th>订单号</th><th>账期</th></tr></thead>' +
      "<tbody><tr><td>PO-001</td><td>月结90天</td></tr></tbody></table>" +
      "</div></div>"
    );
  }

  OPTIONS.forEach(function (opt) {
    var card = document.createElement("article");
    card.className = "theme-option";
    card.dataset.themeId = opt.id;
    card.innerHTML =
      '<div class="theme-option-head">' +
      "<h3>" +
      opt.name +
      "</h3>" +
      "<p>" +
      opt.desc +
      "</p>" +
      '<div class="theme-swatches">' +
      opt.swatches
        .map(function (c) {
          return '<span class="theme-swatch" style="background:' + c + '" title="' + c + '"></span>';
        })
        .join("") +
      "</div></div>" +
      '<div class="theme-mini" data-theme="' +
      opt.id +
      '">' +
      miniPreviewHtml() +
      "</div>" +
      '<div class="theme-option-actions">' +
      '<button type="button" class="btn btn-outline" data-action="preview">全站预览</button>' +
      '<button type="button" class="btn btn-primary" data-action="apply">选用此主题</button>' +
      "</div>";

    card.querySelector('[data-action="preview"]').addEventListener("click", function () {
      WKTTheme.apply(opt.id);
      markActive();
      showToast("已切换为「" + opt.name + "」，可继续浏览本页或返回订单录入");
    });

    card.querySelector('[data-action="apply"]').addEventListener("click", function () {
      WKTTheme.apply(opt.id);
      markActive();
      showToast("已选用「" + opt.name + "」");
    });

    grid.appendChild(card);
  });

  markActive();
  window.addEventListener("wkt-theme-change", markActive);
})();
