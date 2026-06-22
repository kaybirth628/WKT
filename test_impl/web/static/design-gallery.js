(function () {
  var state = { items: [], summary: null, filter: { q: "", category: "", tone: "" } };
  var grid = document.getElementById("galleryGrid");
  var stats = document.getElementById("galleryStats");
  var search = document.getElementById("gallerySearch");
  var catSelect = document.getElementById("galleryCategory");
  var toneSelect = document.getElementById("galleryTone");
  var backdrop = document.getElementById("galleryModalBackdrop");
  var modalBody = document.getElementById("galleryModalBody");
  var modalTitle = document.getElementById("galleryModalTitle");

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function contrastText(hex) {
    if (!hex || hex.charAt(0) !== "#") return "#fff";
    var h = hex.slice(1);
    if (h.length === 3) h = h.split("").map(function (c) { return c + c; }).join("");
    var r = parseInt(h.slice(0, 2), 16);
    var g = parseInt(h.slice(2, 4), 16);
    var b = parseInt(h.slice(4, 6), 16);
    var lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return lum > 0.55 ? "#1a1a1a" : "#ffffff";
  }

  function miniPreview(item) {
    var bg = item.canvas || "#ffffff";
    var ink = item.ink || "#1a1a1a";
    var pri = item.primary || "#2563eb";
    var onPri = contrastText(pri);
    return (
      '<div class="gallery-mini" style="background:' + esc(bg) + ';color:' + esc(ink) + '">' +
      '<div class="gallery-mini-bar" style="border-bottom:1px solid rgba(0,0,0,0.08)">' +
      "<span>WKT</span><span>···</span></div>" +
      '<div class="gallery-mini-body">' +
      "<div>订单录入</div>" +
      '<span class="gallery-mini-btn" style="background:' + esc(pri) + ";color:" + esc(onPri) + '">提交</span>' +
      "</div></div>"
    );
  }

  function filtered() {
    var q = state.filter.q.toLowerCase();
    return state.items.filter(function (item) {
      if (state.filter.category && item.category !== state.filter.category) return false;
      if (state.filter.tone && item.tone !== state.filter.tone) return false;
      if (!q) return true;
      var hay = (item.name + " " + item.slug + " " + item.category + " " + item.description).toLowerCase();
      return hay.indexOf(q) >= 0;
    });
  }

  function renderCard(item) {
    var pills =
      '<span class="gallery-pill cat">' + esc(item.category) + "</span>" +
      '<span class="gallery-pill ' + item.tone + '">' + (item.tone === "light" ? "浅色" : "深色") + "</span>";
    if (item.wkt_enabled) {
      pills += '<span class="gallery-pill enabled">已接入 WKT</span>';
    }
    var swatches = (item.swatches || [])
      .map(function (c) {
        return '<div class="gallery-swatch" style="background:' + esc(c) + '" title="' + esc(c) + '"></div>';
      })
      .join("");
    return (
      '<article class="gallery-card" data-slug="' + esc(item.slug) + '" tabindex="0">' +
      '<div class="gallery-card-head">' +
      "<h3>" + esc(item.name) + "</h3>" +
      '<div class="gallery-card-meta">' + pills + "</div>" +
      '<p class="gallery-card-desc">' + esc(item.description) + "</p>" +
      "</div>" +
      '<div class="gallery-preview">' +
      miniPreview(item) +
      '<div class="gallery-swatches">' + swatches + "</div>" +
      "</div></article>"
    );
  }

  function renderGrid() {
    var list = filtered();
    if (!list.length) {
      grid.innerHTML = '<p class="gallery-empty">没有匹配的方案，请调整筛选条件。</p>';
      return;
    }
    grid.innerHTML = list.map(renderCard).join("");
    grid.querySelectorAll(".gallery-card").forEach(function (card) {
      card.addEventListener("click", function () {
        openModal(card.dataset.slug);
      });
      card.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openModal(card.dataset.slug);
        }
      });
    });
  }

  function openModal(slug) {
    var item = state.items.find(function (i) { return i.slug === slug; });
    if (!item) return;
    modalTitle.textContent = item.name;
    var colors = item.colors || {};
    var colorHtml = Object.keys(colors)
      .sort()
      .map(function (key) {
        var c = colors[key];
        return (
          '<div class="gallery-color-chip"><span style="background:' + esc(c) + '"></span>' +
          "<code>" + esc(key) + "<br>" + esc(c) + "</code></div>"
        );
      })
      .join("");
    var actions =
      item.wkt_enabled
        ? '<a class="btn btn-primary" href="/themes">在 WKT 中切换</a>'
        : '<span class="btn btn-outline" style="opacity:0.65;cursor:default">暂未接入 · 可联系开发选用</span>';
    modalBody.innerHTML =
      '<p style="margin:0;font-size:0.875rem;color:var(--text-secondary);line-height:1.5">' +
      esc(item.description) +
      "</p>" +
      '<p style="margin:0.65rem 0 0;font-size:0.75rem;color:var(--muted)">分类：' +
      esc(item.category) +
      " · slug: <code>" +
      esc(item.slug) +
      "</code></p>" +
      "<h4 style=\"margin:1rem 0 0.35rem;font-size:0.8125rem\">色彩 Token</h4>" +
      '<div class="gallery-color-grid">' +
      colorHtml +
      "</div>" +
      '<div class="gallery-modal-actions">' +
      actions +
      '<a class="btn btn-outline" href="https://github.com/VoltAgent/awesome-design-md/tree/main/design-md/' +
      encodeURIComponent(item.slug) +
      '" target="_blank" rel="noopener">GitHub 源文件</a>' +
      "</div>";
    backdrop.classList.add("is-open");
  }

  function closeModal() {
    backdrop.classList.remove("is-open");
  }

  function fillCategories() {
    if (!state.summary) return;
    state.summary.categories.forEach(function (c) {
      var opt = document.createElement("option");
      opt.value = c.name;
      opt.textContent = c.name + " (" + c.count + ")";
      catSelect.appendChild(opt);
    });
  }

  function updateStats() {
    var s = state.summary;
    var n = filtered().length;
    stats.innerHTML =
      "共 <strong>" +
      s.total +
      "</strong> 套方案（浅色 " +
      s.light +
      " · 深色 " +
      s.dark +
      " · 已接入 WKT " +
      s.wkt_enabled +
      "）· 当前显示 " +
      n +
      " 套 · 来源 <a href=\"" +
      s.source +
      '" target="_blank" rel="noopener">awesome-design-md</a>';
  }

  function bindFilters() {
    search.addEventListener("input", function () {
      state.filter.q = search.value.trim();
      updateStats();
      renderGrid();
    });
    catSelect.addEventListener("change", function () {
      state.filter.category = catSelect.value;
      updateStats();
      renderGrid();
    });
    toneSelect.addEventListener("change", function () {
      state.filter.tone = toneSelect.value;
      updateStats();
      renderGrid();
    });
  }

  backdrop.addEventListener("click", function (e) {
    if (e.target === backdrop) closeModal();
  });
  document.getElementById("galleryModalClose").addEventListener("click", closeModal);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeModal();
  });

  fetch("/api/design-catalog")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      state.items = data.items || [];
      state.summary = data.summary || {};
      fillCategories();
      bindFilters();
      updateStats();
      renderGrid();
    })
    .catch(function () {
      grid.innerHTML = '<p class="gallery-empty">加载失败，请确认服务已启动。</p>';
    });
})();
