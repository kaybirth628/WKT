/** 全局保存成功/失败提示（各模块保存后调用） */
(function () {
  let hideTimer = null;

  function ensureToast() {
    let el = document.getElementById("wktSaveToast");
    if (!el) {
      el = document.createElement("div");
      el.id = "wktSaveToast";
      el.className = "wkt-save-toast is-hidden";
      el.setAttribute("role", "status");
      el.setAttribute("aria-live", "polite");
      document.body.appendChild(el);
    }
    return el;
  }

  function showToast(text, ok) {
    const el = ensureToast();
    el.textContent = text;
    el.className = "wkt-save-toast " + (ok ? "ok" : "error");
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      el.classList.add("is-hidden");
    }, 2800);
  }

  window.showSaveSuccess = function (msg) {
    showToast(msg || "✓ 已保存", true);
  };

  window.showSaveError = function (msg) {
    showToast(msg || "保存失败", false);
  };
})();
