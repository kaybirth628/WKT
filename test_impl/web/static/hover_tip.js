/** 全局悬停全文 tooltip（§7.6：禁止 title 属性；可移入框内拖选或双击复制） */
window.HoverTip = (function () {
  let _el = null;
  let _body = null;
  let _hint = null;
  let hideTimer = null;
  let suppressUntil = 0;
  let pointerDown = false;

  function hideNow() {
    if (_el) {
      _el.style.display = "none";
      _el.classList.remove("is-copied");
    }
    cancelHide();
  }

  function bumpSuppress(ms) {
    suppressUntil = Math.max(suppressUntil, Date.now() + (ms || 0));
  }

  function isSuppressed() {
    if (pointerDown) return true;
    if (Date.now() < suppressUntil) return true;
    const sel = window.getSelection();
    return !!(sel && sel.toString().trim());
  }

  if (!document.documentElement.dataset.hoverTipGlobalBound) {
    document.documentElement.dataset.hoverTipGlobalBound = "1";
    document.addEventListener(
      "mousedown",
      () => {
        pointerDown = true;
        hideNow();
        bumpSuppress(400);
      },
      true
    );
    document.addEventListener(
      "mouseup",
      () => {
        pointerDown = false;
        bumpSuppress(350);
      },
      true
    );
    document.addEventListener("selectionchange", () => {
      if (isSuppressed()) hideNow();
    });
  }

  function ensure() {
    if (!_el) {
      _el = document.createElement("div");
      _el.id = "hoverTip";
      _el.className = "hover-tip";
      _body = document.createElement("div");
      _body.className = "hover-tip-body";
      _hint = document.createElement("div");
      _hint.className = "hover-tip-hint";
      _hint.textContent = "拖选复制 · 双击复制全文";
      _el.appendChild(_body);
      _el.appendChild(_hint);
      document.body.appendChild(_el);
      _el.addEventListener("mouseenter", cancelHide);
      _el.addEventListener("mouseleave", scheduleHide);
      _el.addEventListener("dblclick", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        copyTipText();
      });
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
    if (el.closest(".no-hover-tip")) return false;
    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
      if (el.readOnly || el.disabled) {
        return el.scrollWidth > el.clientWidth + 1;
      }
      return false;
    }
    if (el.tagName === "SELECT") return true;
    if (el.dataset.hoverText) return true;
    return el.scrollWidth > el.clientWidth + 1;
  }

  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      if (isSuppressed()) return;
      hideNow();
    }, 180);
  }

  function cancelHide() {
    clearTimeout(hideTimer);
  }

  function copyTipText() {
    const text = (_body && _body.textContent ? _body.textContent : "").trim();
    if (!text) return;
    function showCopied() {
      if (_hint) _hint.textContent = "已复制到剪贴板";
      if (_el) {
        _el.classList.add("is-copied");
        setTimeout(() => {
          if (_el) _el.classList.remove("is-copied");
          if (_hint) _hint.textContent = "拖选复制 · 双击复制全文";
        }, 1400);
      }
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(showCopied).catch(fallbackSelect);
    } else {
      fallbackSelect();
    }
    function fallbackSelect() {
      const range = document.createRange();
      range.selectNodeContents(_body);
      const sel = window.getSelection();
      if (!sel) return;
      sel.removeAllRanges();
      sel.addRange(range);
      try {
        if (document.execCommand("copy")) showCopied();
      } catch (_e) {
        /* 用户可 Ctrl+C */
      }
    }
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

  function showTip(el, e, followCursor) {
    if (isSuppressed()) return;
    const text = getText(el).trim();
    if (!text || !needsTip(el)) return;
    el.removeAttribute("title");
    const tip = ensure();
    if (_body) _body.textContent = text;
    if (_hint) _hint.textContent = "拖选复制 · 双击复制全文";
    tip.classList.remove("is-copied");
    tip.style.display = "block";
    cancelHide();
    if (followCursor) {
      positionAtCursor(e);
    } else {
      requestAnimationFrame(() => positionNearEl(el));
    }
  }

  function bind(el) {
    if (!el || el.dataset.hoverBound) return;
    if (el.closest(".no-hover-tip")) return;
    el.dataset.hoverBound = "1";
    el.removeAttribute("title");
    const followCursor = false;
    if (el.tagName === "TD") {
      el.classList.toggle("has-ellipsis-tip", needsTip(el));
    }
    el.addEventListener("mouseenter", (e) => showTip(el, e, followCursor));
    if (followCursor) {
      el.addEventListener("mousemove", positionAtCursor);
    }
    el.addEventListener("mouseleave", scheduleHide);
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

  return { bind, bindAll, bindEllipsis, needsTip, hide: hideNow };
})();

window.bindHoverTip = window.HoverTip.bind;
window.bindHoverTipAll = window.HoverTip.bindAll;
