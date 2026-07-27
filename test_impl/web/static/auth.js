(function () {
  function qs(name) {
    var m = location.search.match(new RegExp("[?&]" + name + "=([^&]+)"));
    return m ? decodeURIComponent(m[1]) : "";
  }

  async function apiFetch(url, options) {
    var res = await fetch(url, Object.assign({ credentials: "same-origin" }, options || {}));
    var data = {};
    try {
      data = await res.json();
    } catch (e) {
      data = {};
    }
    if (res.status === 401 && !String(url).includes("/api/auth/login")) {
      location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search);
      throw new Error("auth_required");
    }
    return { res: res, data: data };
  }

  window.wktAuth = { apiFetch: apiFetch };

  var form = document.getElementById("loginForm");
  if (form) {
    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      var msg = document.getElementById("loginMsg");
      if (msg) msg.textContent = "登录中…";
      var username = document.getElementById("loginUsername").value.trim();
      var password = document.getElementById("loginPassword").value;
      try {
        var out = await apiFetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: username, password: password }),
        });
        if (!out.res.ok) {
          if (msg) msg.textContent = out.data.error || "登录失败";
          return;
        }
        var next = qs("next") || "/";
        if (out.data.user && out.data.user.must_change_password) {
          sessionStorage.setItem("wkt_must_change_pw", "1");
        }
        location.href = next;
      } catch (err) {
        if (msg) msg.textContent = "网络错误，请重试";
      }
    });
    return;
  }

  var logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async function () {
      await apiFetch("/api/auth/logout", { method: "POST" });
      location.href = "/login";
    });
  }

  if (sessionStorage.getItem("wkt_must_change_pw") === "1") {
    sessionStorage.removeItem("wkt_must_change_pw");
    showChangePasswordModal();
  }

  function showChangePasswordModal() {
    var backdrop = document.createElement("div");
    backdrop.className = "auth-modal-backdrop";
    backdrop.innerHTML =
      '<div class="auth-modal" role="dialog">' +
      "<h3>请修改初始密码</h3>" +
      '<label class="field"><span>原密码</span><input type="password" id="cpOld" /></label>' +
      '<label class="field"><span>新密码</span><input type="password" id="cpNew" minlength="6" /></label>' +
      '<p id="cpMsg" class="msg"></p>' +
      '<button type="button" class="btn btn-primary" id="cpSubmit">确认修改</button>' +
      "</div>";
    document.body.appendChild(backdrop);
    backdrop.querySelector("#cpSubmit").addEventListener("click", async function () {
      var msg = backdrop.querySelector("#cpMsg");
      var out = await apiFetch("/api/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          old_password: backdrop.querySelector("#cpOld").value,
          new_password: backdrop.querySelector("#cpNew").value,
        }),
      });
      if (!out.res.ok) {
        msg.textContent = out.data.error || "修改失败";
        return;
      }
      backdrop.remove();
    });
  }
})();
