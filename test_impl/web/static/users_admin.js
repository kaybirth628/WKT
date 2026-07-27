(function () {
  var apiFetch = window.wktAuth && window.wktAuth.apiFetch;
  if (!apiFetch) return;

  var body = document.getElementById("usersBody");
  var msg = document.getElementById("usersMsg");
  var editingId = null;
  var lastItems = [];

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setMsg(text, ok) {
    if (!msg) return;
    msg.textContent = text || "";
    msg.className = "msg" + (text ? (ok ? " ok" : " error") : "");
  }

  function renderUsers(items) {
    lastItems = items || [];
    if (!body) return;
    if (!lastItems.length) {
      body.innerHTML = '<tr><td colspan="6">暂无用户</td></tr>';
      return;
    }
    body.innerHTML = lastItems
      .map(function (u) {
        var status = u.is_active ? "启用" : "禁用";
        var role = u.role === "admin" ? "管理员" : "员工";
        var isAdminUser = u.username.toLowerCase() === "admin";
        var actions =
          '<button type="button" class="btn btn-outline btn-sm" data-edit="' +
          u.id +
          '">编辑</button> ' +
          '<button type="button" class="btn btn-outline btn-sm" data-reset="' +
          u.id +
          '">重置密码</button> ';
        if (!isAdminUser) {
          actions +=
            '<button type="button" class="btn btn-ghost btn-sm" data-toggle="' +
            u.id +
            '" data-active="' +
            (u.is_active ? "0" : "1") +
            '">' +
            (u.is_active ? "禁用" : "启用") +
            "</button> " +
            '<button type="button" class="btn btn-ghost btn-sm users-del-btn" data-delete="' +
            u.id +
            '" data-name="' +
            esc(u.display_name) +
            '">删除</button>';
        }
        var main =
          "<tr>" +
          "<td><code>" +
          esc(u.username) +
          "</code></td>" +
          "<td>" +
          esc(u.display_name) +
          "</td>" +
          "<td>" +
          esc(role) +
          "</td>" +
          "<td>" +
          esc(status) +
          "</td>" +
          "<td>" +
          esc((u.last_login_at || "—").replace("T", " ").slice(0, 19)) +
          "</td>" +
          "<td>" +
          actions +
          "</td>" +
          "</tr>";
        if (editingId !== u.id) return main;
        var roleOpts =
          '<option value="user"' +
          (u.role === "user" ? " selected" : "") +
          ">普通用户</option>" +
          '<option value="admin"' +
          (u.role === "admin" ? " selected" : "") +
          ">管理员</option>";
        if (isAdminUser) {
          roleOpts =
            '<option value="admin" selected>管理员</option>';
        }
        return (
          main +
          '<tr class="users-edit-row"><td colspan="6">' +
          '<form class="users-edit-form" data-id="' +
          u.id +
          '">' +
          '<label>姓名 <input name="display_name" type="text" required value="' +
          esc(u.display_name) +
          '" /></label> ' +
          '<label>角色 <select name="role"' +
          (isAdminUser ? " disabled" : "") +
          ">" +
          roleOpts +
          "</select></label> " +
          '<button type="submit" class="btn btn-primary btn-sm">保存</button> ' +
          '<button type="button" class="btn btn-outline btn-sm users-edit-cancel">取消</button>' +
          "</form></td></tr>"
        );
      })
      .join("");

    body.querySelectorAll("[data-edit]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        editingId = Number(btn.getAttribute("data-edit"));
        renderUsers(lastItems);
      });
    });

    body.querySelectorAll(".users-edit-cancel").forEach(function (btn) {
      btn.addEventListener("click", function () {
        editingId = null;
        renderUsers(lastItems);
      });
    });

    body.querySelectorAll(".users-edit-form").forEach(function (form) {
      form.addEventListener("submit", async function (e) {
        e.preventDefault();
        var id = Number(form.getAttribute("data-id"));
        var displayName = form.display_name.value.trim();
        var role = form.role.value;
        if (!displayName) {
          setMsg("姓名不能为空", false);
          return;
        }
        var out = await apiFetch("/api/users/" + id, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ display_name: displayName, role: role }),
        });
        if (!out.res.ok) {
          setMsg(out.data.error || "保存失败", false);
          return;
        }
        editingId = null;
        setMsg("已更新用户信息", true);
        loadUsers();
      });
    });

    body.querySelectorAll("[data-reset]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var pw = prompt("输入新密码（至少6位）：");
        if (!pw) return;
        var id = btn.getAttribute("data-reset");
        var out2 = await apiFetch("/api/users/" + id + "/reset-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: pw }),
        });
        setMsg(out2.res.ok ? "密码已重置" : out2.data.error || "失败", out2.res.ok);
      });
    });

    body.querySelectorAll("[data-toggle]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var id = btn.getAttribute("data-toggle");
        var active = btn.getAttribute("data-active") === "1";
        var out2 = await apiFetch("/api/users/" + id + "/active", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ active: active }),
        });
        if (out2.res.ok) loadUsers();
        else setMsg(out2.data.error || "操作失败", false);
      });
    });

    body.querySelectorAll("[data-delete]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var id = btn.getAttribute("data-delete");
        var name = btn.getAttribute("data-name") || id;
        if (!confirm("确定删除用户「" + name + "」？此操作不可恢复。")) return;
        var out2 = await apiFetch("/api/users/" + id, { method: "DELETE" });
        if (!out2.res.ok) {
          setMsg(out2.data.error || "删除失败", false);
          return;
        }
        if (editingId === Number(id)) editingId = null;
        setMsg("用户已删除", true);
        loadUsers();
      });
    });
  }

  async function loadUsers() {
    var out = await apiFetch("/api/users");
    if (!out.res.ok) {
      setMsg(out.data.error || "加载失败", false);
      return;
    }
    renderUsers(out.data.items || []);
  }

  document.getElementById("createUserForm")?.addEventListener("submit", async function (e) {
    e.preventDefault();
    var out = await apiFetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: document.getElementById("newUsername").value.trim(),
        display_name: document.getElementById("newDisplayName").value.trim(),
        password: document.getElementById("newPassword").value,
        role: document.getElementById("newRole").value,
      }),
    });
    setMsg(out.res.ok ? "用户已创建" : out.data.error || "创建失败", out.res.ok);
    if (out.res.ok) {
      e.target.reset();
      loadUsers();
    }
  });

  loadUsers();
})();
