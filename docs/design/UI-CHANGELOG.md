# WKT · UI 布局变更日志

> **规则**：凡改动页面结构、CSS 布局、间距、录入/列表交互、字体层级，**必须**在本文件登记 **UI-XXXX**（递增不复用）。  
> 若同时影响用户可见功能，**同一任务**内同步主 [`CHANGELOG.md`](../change/CHANGELOG.md)（CL-XXXX）。  
> **设计规则权威文档**：[`ui-layout-rules.md`](ui-layout-rules.md)

---

## 登记格式

| 字段 | 说明 |
|------|------|
| UI 编号 | UI-XXXX |
| 日期 | 完成日期 |
| 类型 | 布局 / 交互 / 样式 / 文档 |
| 涉及 | 模板 / CSS / JS |
| 内容 | 做了什么、用户可见变化 |
| 规则 | 是否更新 `ui-layout-rules.md` |
| 关联 CL | 主 CHANGELOG 编号（如有） |

---

## 变更记录

### UI-0006 · 2026-07-28 · 文档

| 字段 | 内容 |
|------|------|
| 涉及 | `ui-layout-rules.md`（V3）、`GLOBAL-RULES-INDEX.md`、`README.md`、`.cursor/rules/wkt-ui-design.mdc`、`.cursor/skills/wkt-ui-design/`、`AGENTS.md` |
| 内容 | 合并 **全部** 全局 UI 规则（非仅近期）：顶栏 CL-0103、themes 色彩、 typography 全层级、组件、list-table 行色、间距变量、录入/列表/客商/成本模板 |
| 规则 | 是（V3 全文） |
| 关联 CL | CL-0199 |

### UI-0005 · 2026-07-28 · 文档

| 字段 | 内容 |
|------|------|
| 涉及 | `docs/design/ui-layout-rules.md`、`UI-CHANGELOG.md`、`README.md`、`.cursor/rules/wkt-ui-design.mdc`、`.cursor/skills/wkt-ui-design/`、`AGENTS.md` |
| 内容 | 用户要求固化「清爽布局」偏好；建立本地 UI 规则与专用 changelog；Agent 新功能必须 follow |
| 规则 | 是（V2 首版） |
| 关联 CL | CL-0198 |

### UI-0004 · 2026-07-28 · 布局 + 交互

| 字段 | 内容 |
|------|------|
| 涉及 | `cost_entry.html`、`cost_entry.js`、`cost_bom_import.js`、`cost.css` |
| 内容 | BOM 录入对齐订单录入：mode-card +「请先选择录入方式」；去除上传区长说明；初始不展开子面板；导入成功后重置为干净上传页 |
| 规则 | 是（写入 §3 清爽录入标准） |
| 关联 CL | CL-0197、CL-0195、CL-0196 |

### UI-0003 · 2026-07-28 · 布局

| 字段 | 内容 |
|------|------|
| 涉及 | `cost_bom_import.js`、`cost.css`、`cost_entry.html` |
| 内容 | BOM 导入预览：紧凑 padding；去掉预览区内部纵向滚动；表格字体/颜色对齐全局 list-table；主操作「批量上传」置底 |
| 规则 | 是（§3.4、§4） |
| 关联 CL | CL-0194、CL-0196 |

### UI-0002 · 2026-07-20 · 样式

| 字段 | 内容 |
|------|------|
| 涉及 | `style.css`、`cost_query.html` 等 |
| 内容 | 列表统一 `list-table` 紧凑表头/单元格；`--wkt-list-*` 变量；成本/BOM 查询列样式与出货明细对齐 |
| 规则 | 已并入 V2 §4 |
| 关联 CL | （见 CHANGELOG 2026-07 成本列表相关条目） |

### UI-0001 · 2026-05-30 · 布局

| 字段 | 内容 |
|------|------|
| 涉及 | `_order_sidebar.html`（顶栏）、`index.html`、`style.css`、`app.js` |
| 内容 | 左侧栏 → **顶部导航**；内容全宽；模块标题/说明移至 **页脚**；订单子功能改为顶栏下拉 |
| 规则 | 已并入 V2 §2 |
| 关联 CL | CL-0103 |

---

## 用户偏好备忘（勿删）

> 2026-07-28：用户明确表示希望界面 **清爽**，去除多余说明文字和留白；录入页 follow 订单录入模式；**不愿再反复花时间调布局**。  
> 后续 Agent 应优先 **遵守规则、登记变更**，而非每次重新猜测偏好。
