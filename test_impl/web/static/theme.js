/** WKT 主题：localStorage 持久化，默认 classic（经典浅色） */
(function () {
  var KEY = "wkt-theme";
  var VER_KEY = "wkt-theme-ver";
  var THEME_VER = "2"; /* bump when changing site-wide default */
  var DEFAULT = "hp";
  var VALID = ["classic", "stripe", "ibm", "notion", "hp", "minimal-white"];

  function normalize(id) {
    return VALID.indexOf(id) >= 0 ? id : DEFAULT;
  }

  function readTheme() {
    try {
      if (localStorage.getItem(VER_KEY) !== THEME_VER) {
        localStorage.setItem(KEY, DEFAULT);
        localStorage.setItem(VER_KEY, THEME_VER);
      }
      return normalize(localStorage.getItem(KEY) || DEFAULT);
    } catch (e) {
      return DEFAULT;
    }
  }

  window.WKTTheme = {
    key: KEY,
    default: DEFAULT,
    valid: VALID,
    current: function () {
      return readTheme();
    },
    apply: function (id) {
      var theme = normalize(id);
      document.documentElement.setAttribute("data-theme", theme);
      try {
        localStorage.setItem(KEY, theme);
      } catch (e) { /* ignore */ }
      window.dispatchEvent(new CustomEvent("wkt-theme-change", { detail: theme }));
      return theme;
    },
    label: function (id) {
      var map = {
        classic: "经典 WKT",
        stripe: "Stripe 金融紫",
        ibm: "IBM 企业蓝",
        notion: "Notion 协作",
        hp: "HP 科技蓝",
        "minimal-white": "极简纯白",
      };
      return map[normalize(id)] || id;
    },
  };

  document.documentElement.setAttribute("data-theme", WKTTheme.current());
})();
