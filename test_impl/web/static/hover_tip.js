/** 全局悬停全文 tooltip（§7.6：禁止 title 属性） */
window.HoverTip = (function () {
  let _el = null;

  function ensure() {
    if (!_el) {
      _el = document.createElement("div");
      _el.id = "hoverTip";
      _el.className = "hover-tip";
      document.body.appendChild(_el);
    }
    return _el;
  }

  function getText(el) {
    if (el.dataset.hoverText) return el.dataset.hoverText;
    if (el.tagName === "SELECT") {
      const opt = el.options[el.selectedIndex];
      return opt ? opt.text : el.value;
    }
    return el.value != null ? String(el.value) : el.textContent || "";
  }

  function needsTip(el) {
    if (!el) return false;
    if (el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA") return true;
    if (el.dataset.hoverText) return true;
    return el.scrollWidth > el.clientWidth + 1;
  }

  function positionNearEl(el) {
    if (!_el || _el.style.display === "none") return;
    const pad = 6;
    const cellRect = el.getBoundingClientRect();
    const tipRect = _el.getBoundingClientRect();
    let x = cellRect.left;
    let y = cellRect.bottom + pad;
    if (x + tipRect.width > window.innerWidth - 8) {
      x = Math.max(8, window.innerWidth - tipRect.width - 8);
    }
    if (y + tipRect.height > window.innerHeight - 8) {
      y = cellRect.top - tipRect.height - pad;
    }
    _el.style.left = x + "px";
    _el.style.top = y + "px";
  }

  function positionAtCursor(e) {
    if (!_el || _el.style.display === "none") return;
    const pad = 12;
    let x = e.clientX + pad;
    let y = e.clientY + pad;
    const rect = _el.getBoundingClientRect();
    if (x + rect.width > window.innerWidth - 8) x = e.clientX - rect.width - pad;
    if (y + rect.height > window.innerHeight - 8) y = e.clientY - rect.height - pad;
    _el.style.left = x + "px";
    _el.style.top = y + "px";
  }

  function bind(el) {
    if (!el || el.dataset.hoverBound) return;
    el.dataset.hoverBound = "1";
    el.removeAttribute("title");
    const followCursor =
      el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA";
    if (el.tagName === "TD") {
      el.classList.toggle("has-ellipsis-tip", needsTip(el));
    }
    el.addEventListener("mouseenter", (e) => {
      const text = getText(el).trim();
      if (!text || !needsTip(el)) return;
      el.removeAttribute("title");
      const tip = ensure();
      tip.textContent = text;
      tip.style.display = "block";
      if (followCursor) {
        positionAtCursor(e);
      } else {
        requestAnimationFrame(() => positionNearEl(el));
      }
    });
    if (followCursor) {
      el.addEventListener("mousemove", positionAtCursor);
    }
    el.addEventListener("mouseleave", () => {
      if (_el) _el.style.display = "none";
    });
  }

  function bindAll(root, selector) {
    (root || document)
      .querySelectorAll(
        selector ||
          ".pv, .entry-card input, .entry-card select, .list-table td:not(.action-cell), .data-table td:not(.action-cell)"
      )
      .forEach(bind);
  }

  function bindEllipsis(root, selector) {
    (root || document).querySelectorAll(selector || "[data-hover-text]").forEach((el) => {
      const text = (el.dataset.hoverText || el.textContent || "").trim();
      if (!text || text === "—") return;
      el.removeAttribute("title");
      el.classList.add("has-ellipsis-tip");
      bind(el);
    });
  }

  return { bind, bindAll, bindEllipsis, needsTip };
})();

window.bindHoverTip = window.HoverTip.bind;
window.bindHoverTipAll = window.HoverTip.bindAll;
