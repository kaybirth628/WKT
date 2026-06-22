(function () {
  var root = document.getElementById("aiAssistantRoot");
  if (!root) return;

  var memoryToggle = document.getElementById("aiAssistantMemoryToggle");
  var memoryPanel = document.getElementById("aiAssistantMemoryPanel");
  var memoryRules = document.getElementById("aiMemoryRules");
  var memoryGlossary = document.getElementById("aiMemoryGlossary");
  var memoryCustom = document.getElementById("aiMemoryCustom");
  var memorySave = document.getElementById("aiMemorySave");
  var memorySaveStatus = document.getElementById("aiMemorySaveStatus");
  var form = document.getElementById("aiAssistantForm");
  var input = document.getElementById("aiAssistantInput");
  var messagesEl = document.getElementById("aiAssistantMessages");
  var statusEl = document.getElementById("aiAssistantStatus");
  var sendBtn = document.getElementById("aiAssistantSend");

  var history = [];
  var busy = false;

  var REMEMBER_PREFIXES = ["记住：", "记住:", "记忆：", "记忆:"];

  function setStatus(text, isError) {
    if (!statusEl) return;
    statusEl.textContent = text || "";
    statusEl.classList.toggle("is-error", Boolean(isError));
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function appendMessage(role, html) {
    var welcome = messagesEl.querySelector(".ai-assistant-welcome");
    if (welcome) welcome.remove();
    var div = document.createElement("div");
    div.className = "ai-assistant-msg ai-assistant-msg-" + role;
    div.innerHTML = html;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function formatAnswer(data) {
    var parts = ["<div class=\"ai-assistant-answer\">" + escHtml(data.answer || "") + "</div>"];
    if (data.sql) {
      parts.push(
        "<details class=\"ai-assistant-sql\"><summary>查看 SQL（" +
          (data.row_count || 0) +
          " 行）</summary><pre>" +
          escHtml(data.sql) +
          "</pre></details>"
      );
    }
    if (data.rows && data.rows.length && data.columns && data.columns.length) {
      var head = data.columns.map(function (c) {
        return "<th>" + escHtml(c) + "</th>";
      }).join("");
      var body = data.rows
        .slice(0, 15)
        .map(function (row) {
          return (
            "<tr>" +
            data.columns
              .map(function (c) {
                var v = row[c];
                return "<td>" + escHtml(v == null ? "" : v) + "</td>";
              })
              .join("") +
            "</tr>"
          );
        })
        .join("");
      parts.push(
        "<div class=\"ai-assistant-table-wrap\"><table class=\"ai-assistant-table\"><thead><tr>" +
          head +
          "</tr></thead><tbody>" +
          body +
          "</tbody></table></div>"
      );
      if (data.row_count > 15) {
        parts.push("<p class=\"ai-assistant-table-hint\">预览前 15 行</p>");
      }
    }
    return parts.join("");
  }

  function isRememberCommand(text) {
    var t = (text || "").trim();
    for (var i = 0; i < REMEMBER_PREFIXES.length; i++) {
      if (t.indexOf(REMEMBER_PREFIXES[i]) === 0) return true;
    }
    return false;
  }

  function extractRememberText(text) {
    var t = (text || "").trim();
    for (var i = 0; i < REMEMBER_PREFIXES.length; i++) {
      var p = REMEMBER_PREFIXES[i];
      if (t.indexOf(p) === 0) return t.slice(p.length).trim();
    }
    return t;
  }

  function glossaryToText(glossary) {
    if (!glossary) return "";
    return Object.keys(glossary)
      .map(function (k) {
        return k + "=" + glossary[k];
      })
      .join("\n");
  }

  function textToGlossary(text) {
    var map = {};
    (text || "").split("\n").forEach(function (line) {
      line = line.trim();
      if (!line || line.indexOf("=") < 1) return;
      var idx = line.indexOf("=");
      var k = line.slice(0, idx).trim();
      var v = line.slice(idx + 1).trim();
      if (k && v) map[k] = v;
    });
    return map;
  }

  async function loadMemoryForm() {
    try {
      var res = await fetch("/api/ai/memory");
      var data = await res.json();
      if (!res.ok || !data.ok) return;
      memoryRules.value = (data.business_rules || []).join("\n");
      memoryGlossary.value = glossaryToText(data.glossary);
      memoryCustom.value = data.custom_prompt || "";
    } catch (e) {
      /* ignore */
    }
  }

  async function saveMemoryForm() {
    memorySaveStatus.textContent = "保存中…";
    try {
      var res = await fetch("/api/ai/memory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_rules: (memoryRules.value || "")
            .split("\n")
            .map(function (s) {
              return s.trim();
            })
            .filter(Boolean),
          glossary: textToGlossary(memoryGlossary.value),
          custom_prompt: (memoryCustom.value || "").trim(),
        }),
      });
      var data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "保存失败");
      memorySaveStatus.textContent = "已保存（重启后仍有效）";
      if (window.showSaveSuccess) window.showSaveSuccess("✓ 已保存");
      setTimeout(function () {
        memorySaveStatus.textContent = "";
      }, 2500);
    } catch (err) {
      memorySaveStatus.textContent = err.message || "保存失败";
    }
  }

  async function rememberRule(text) {
    busy = true;
    sendBtn.disabled = true;
    setStatus("写入业务记忆…");
    appendMessage("user", "<div class=\"ai-assistant-bubble\">" + escHtml(text) + "</div>");
    try {
      var res = await fetch("/api/ai/memory/remember", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "rule", text: extractRememberText(text) }),
      });
      var data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "保存失败");
      await loadMemoryForm();
      if (window.showSaveSuccess) window.showSaveSuccess("✓ 已保存");
      appendMessage(
        "assistant",
        "<div class=\"ai-assistant-answer\">已写入业务记忆，下次开机仍会参考这条规则。</div>"
      );
      setStatus("");
    } catch (err) {
      appendMessage(
        "assistant",
        "<div class=\"ai-assistant-error\">" + escHtml(err.message || String(err)) + "</div>"
      );
      setStatus(err.message || "保存失败", true);
    } finally {
      busy = false;
      sendBtn.disabled = false;
    }
  }

  async function checkStatus() {
    try {
      var res = await fetch("/api/ai/status");
      var data = await res.json();
      if (!data.configured) {
        setStatus("DeepSeek 未配置，请在 config/secrets.local.json 填写 API Key", true);
      }
    } catch (e) {
      setStatus("无法连接 AI 服务", true);
    }
  }

  async function sendMessage(text) {
    if (busy || !text) return;
    if (isRememberCommand(text)) {
      await rememberRule(text);
      return;
    }
    busy = true;
    sendBtn.disabled = true;
    setStatus("思考中…（网络不稳时会自动重试）");
    appendMessage("user", "<div class=\"ai-assistant-bubble\">" + escHtml(text) + "</div>");

    try {
      var res = await fetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: history }),
      });
      var data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error(data.error || "请求失败");
      }
      history.push({ role: "user", content: text });
      history.push({ role: "assistant", content: data.answer || "" });
      if (history.length > 20) history = history.slice(-20);
      appendMessage("assistant", formatAnswer(data));
      setStatus("");
    } catch (err) {
      appendMessage(
        "assistant",
        "<div class=\"ai-assistant-error\">" +
          escHtml(err.message || String(err)) +
          "<br><button type=\"button\" class=\"btn btn-sm ai-assistant-retry\">重试</button></div>"
      );
      var retryBtn = messagesEl.querySelector(".ai-assistant-retry:last-of-type");
      if (retryBtn) {
        retryBtn.addEventListener("click", function () {
          retryBtn.parentElement.remove();
          sendMessage(text);
        });
      }
      setStatus(err.message || "发送失败", true);
    } finally {
      busy = false;
      sendBtn.disabled = false;
    }
  }

  window.focusAiAssistant = function () {
    setTimeout(function () {
      input?.focus();
    }, 80);
  };

  memoryToggle.addEventListener("click", function () {
    memoryPanel.classList.toggle("is-hidden");
    if (!memoryPanel.classList.contains("is-hidden")) loadMemoryForm();
  });
  memorySave.addEventListener("click", saveMemoryForm);

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = (input.value || "").trim();
    if (!text) return;
    input.value = "";
    sendMessage(text);
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  checkStatus();
  loadMemoryForm();
})();
