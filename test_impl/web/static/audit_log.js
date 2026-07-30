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

  function deployHoverText(row) {
    var d = row.detail || {};
    var lines = [];
    var clTrans = d.cl_transition || row.summary || "";
    if (clTrans) lines.push(String(clTrans));
    if (d.triggered_by) lines.push("推送人：" + d.triggered_by);
    var prev = d.previous || {};
    var cur = d.current || {};
    if (prev.top_cl || cur.top_cl) {
      lines.push("CL：" + (prev.top_cl || "—") + " → " + (cur.top_cl || "—"));
    }
    if (prev.version || cur.version) {
      lines.push("版本：" + (prev.version || "—") + " → " + (cur.version || "—"));
    }
    if (prev.build || cur.build) {
      lines.push("Build：" + (prev.build || "—") + " → " + (cur.build || "—"));
    }
    var changes = d.changes || [];
    if (changes.length) {
      lines.push("本次更新：");
      changes.forEach(function (item) {
        lines.push("· " + item);
      });
    }
    return lines.join("\n");
  }

  function bindSummaryCell(td, row) {
    if (!td || !window.HoverTip) return;
    var tip = row.action === "system.deploy" ? deployHoverText(row) : (td.textContent || "").trim();
    if (!tip) return;
    if (row.action === "system.deploy" || window.HoverTip.needsTip(td)) {
      td.dataset.hoverText = tip;
      window.HoverTip.bind(td);
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
          '<td class="audit-summary-cell">' + esc(row.summary) + "</td>" +
          "<td>" + esc(row.ip_address || "—") + "</td>" +
          "</tr>"
        );
      })
      .join("");
    body.querySelectorAll("tr").forEach(function (tr, idx) {
      bindSummaryCell(tr.querySelector("td.audit-summary-cell"), items[idx] || {});
    });
  }

  document.getElementById("auditSearchBtn")?.addEventListener("click", loadAudit);
  loadAudit();
})();
