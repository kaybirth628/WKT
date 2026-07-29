(function () {
  var apiFetch = window.wktAuth && window.wktAuth.apiFetch;
  if (!apiFetch) return;

  var body = document.getElementById("auditBody");
  var summary = document.getElementById("auditSummary");

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function fmtTime(iso) {
    if (!iso) return "—";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return iso.replace("T", " ").slice(0, 19);
      return d.toLocaleString("zh-CN", { hour12: false });
    } catch (e) {
      return iso;
    }
  }

  async function loadAudit() {
    var params = new URLSearchParams();
    var mod = document.getElementById("auditModule");
    var user = document.getElementById("auditUsername");
    var from = document.getElementById("auditFrom");
    var to = document.getElementById("auditTo");
    if (mod && mod.value) params.set("module", mod.value);
    if (user && user.value.trim()) params.set("username", user.value.trim());
    if (from && from.value) params.set("date_from", from.value + "T00:00:00+00:00");
    if (to && to.value) params.set("date_to", to.value + "T23:59:59+00:00");
    var out = await apiFetch("/api/audit-log?" + params.toString());
    if (!out.res.ok) {
      if (summary) summary.textContent = out.data.error || "加载失败";
      return;
    }
    var items = out.data.items || [];
    if (summary) summary.textContent = "共 " + (out.data.total || items.length) + " 条，显示最近 " + items.length + " 条";
    if (!body) return;
    body.innerHTML = items
      .map(function (row) {
        return (
          "<tr>" +
          "<td>" + esc(fmtTime(row.created_at)) + "</td>" +
          "<td>" + esc(row.display_name || row.username) + "</td>" +
          "<td>" + esc(row.module_label || row.module) + "</td>" +
          "<td>" + esc(row.action_label || row.action) + "</td>" +
          "<td>" + esc(row.summary) + "</td>" +
          "<td>" + esc(row.ip_address || "—") + "</td>" +
          "</tr>"
        );
      })
      .join("");
    if (window.HoverTip) {
      body.querySelectorAll("td:nth-child(5)").forEach(function (td) {
        var text = (td.textContent || "").trim();
        if (text && window.HoverTip.needsTip(td)) {
          td.dataset.hoverText = text;
          td.classList.add("list-td-text");
          window.HoverTip.bind(td);
        }
      });
    }
  }

  document.getElementById("auditSearchBtn")?.addEventListener("click", loadAudit);
  loadAudit();
})();
