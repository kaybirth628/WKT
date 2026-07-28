# WKT · UI 设计文档（本地）

> **改 UI / 排版 / 布局前**：先读 **[`ui-layout-rules.md`](ui-layout-rules.md)（V3 全局规范全文）**，再读 **[`GLOBAL-RULES-INDEX.md`](GLOBAL-RULES-INDEX.md)** 确认无遗漏其他规则源。

## 核心文件

| 文件 | 用途 |
|------|------|
| **[`ui-layout-rules.md`](ui-layout-rules.md)** | **唯一权威** — 整合顶栏、主题、字体、间距、组件、list-table、录入模板、反模式 |
| [`GLOBAL-RULES-INDEX.md`](GLOBAL-RULES-INDEX.md) | 全仓库 UI 相关规则索引（AGENTS、.cursor、源码、用户规则、CL 里程碑） |
| [`UI-CHANGELOG.md`](UI-CHANGELOG.md) | UI 专用变更日志；**每次**改布局/样式/交互须登记 |
| [`DESIGN.md`](DESIGN.md) | 品牌色 / HP 主题 Token |
| [`ui-style-guide-v1.md`](ui-style-guide-v1.md) | 历史 V1（侧栏时代，已 superseded） |

## Agent 强制流程

1. 读 **`ui-layout-rules.md` 全文**（至少 §0–§9 + 对应页面类型）
2. 读 **`UI-CHANGELOG.md`** 最新 5 条
3. 对照 **参考页**（`ui-layout-rules.md` §16）实现
4. 登记 UI-CHANGELOG + 主 CHANGELOG（若用户可见）
5. bump `?v=` / `build`

## 参考实现

| 页面 | 模板 | 说明 |
|------|------|------|
| 订单录入 | `index.html` | mode-card、entry-grid、OCR、列表 |
| BOM 录入 | `cost_entry.html` | **清爽上传**标准 |
| BOM 查询 | `cost_query.html` | list-table |
| 全局样式 | `style.css` | 变量与组件 |
| 主题 | `themes.css` | 色彩 |
