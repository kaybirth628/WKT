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

### UI-0020 · 2026-07-30 · 样式

| 字段 | 内容 |
|------|------|
| 涉及 | `index.html`、`style.css` 供应商维护 |
| 内容 | 列宽重分配 + 单元格 padding 统一 + 新增表单 8 列网格 |
| 规则 | 否 |
| 关联 CL | CL-0274 |

### UI-0019 · 2026-07-30 · 样式

| 字段 | 内容 |
|------|------|
| 涉及 | `style.css`、`cost.css`、BOM 查询、供应商维护 |
| 内容 | 列表展示 0.75rem / 方框输入 0.8125rem 对齐 §8.2、§7.9；修复供应商行内 0.875rem 偏大 |
| 规则 | 是（§8.2 / §7.9.1） |
| 关联 CL | CL-0272 |

### UI-0018 · 2026-07-29 · 布局

| 字段 | 内容 |
|------|------|
| 涉及 | `cost_query.js`、`cost_common.js`、`cost.css` |
| 内容 | BOM 查询「成本详情」预览：分步只读 UI，与录入/修改弹窗结构一致 |
| 规则 | 否 |
| 关联 CL | CL-0249 |

### UI-0017 · 2026-07-29 · 布局 + 交互

| 字段 | 内容 |
|------|------|
| 涉及 | `cost_query.html/js`、`cost_common.js` |
| 内容 | BOM 查询「修改」弹窗改用分步工序 UI（勾选 + 单价/供应商明细），与 BOM 录入一致 |
| 规则 | 否（沿用 §7.9 / 录入范式） |
| 关联 CL | CL-0248 |

### UI-0016 · 2026-07-29 · 文档 + 样式

| 字段 | 内容 |
|------|------|
| 涉及 | `ui-layout-rules.md` §7.9、`wkt-ui-design.mdc`、`style.css` |
| 内容 | 全局规则：所有输入框（含 combo）统一 8px 圆角/`border-strong`/focus；多列表单统一 `field-label`+`field-control` 底对齐；BOM 明细为参考实现 |
| 规则 | 是（§7.9 新增；§7.4/§7.8/§15 更新） |
| 关联 CL | CL-0247 |

### UI-0015 · 2026-07-29 · 交互 + 样式 + 布局

| 字段 | 内容 |
|------|------|
| 涉及 | 全站模板/JS/CSS、`hover_tip.js`、`inventory_bom_lookup.js` |
| 内容 | 全量 UI 对齐：剩余页 combo、hover-tip、TP 字体、审计/用户 list-table+footer |
| 规则 | 是（§5.1 字体现状更新） |
| 关联 CL | CL-0236 |

### UI-0014 · 2026-07-29 · 交互

| 字段 | 内容 |
|------|------|
| 涉及 | `cost_entry.html/js`、`cost.css`、库存四页 HTML/JS |
| 内容 | BOM 手动录入 datalist → 标准可搜索 combo；库存筛选 combo 补 `openOnFocus`/`showToggle`/`simpleList` |
| 规则 | 否（沿用 §7.8） |
| 关联 CL | CL-0235 |

### UI-0013 · 2026-07-29 · 布局 + 交互 + 文档

| 字段 | 内容 |
|------|------|
| 涉及 | `index.html`、`app.js`、`style.css`、`ui-layout-rules.md` |
| 内容 | 订单手动录入：去掉接单日期（新建默认当天）；5×2 等宽网格；登记 §7.8 可搜索下拉 + §9.5 表单模板 |
| 规则 | **是**（§7.8、§9.5、§15 反模式） |
| 关联 CL | CL-0232 |

---

### UI-0012 · 2026-07-29 · 交互

| 字段 | 内容 |
|------|------|
| 涉及 | `inventory_entry.js`、`inventory_entry.html` |
| 内容 | 移除高级登记折叠区；工序多选（①②）+ 编辑面板（单道改数 / 双道流转）；卡片标签改为「场内库存/在途库存」 |
| 规则 | 否 |
| 关联 CL | CL-0213 |

### UI-0011 · 2026-07-28 · 交互

| 字段 | 内容 |
|------|------|
| 涉及 | `inventory_entry.js`、`inventory_entry.html` |
| 内容 | 供应商 `<select>` 改为可搜索 combo（复用 `process-supplier-combo` 样式） |
| 规则 | 否 |
| 关联 CL | CL-0212 |

### UI-0010 · 2026-07-28 · 交互

| 字段 | 内容 |
|------|------|
| 涉及 | `inventory_entry.js`、`inventory.css` |
| 内容 | 工序卡片展示供应商；单道/双道编辑表单增加供应商下拉（必选） |
| 规则 | 否 |
| 关联 CL | CL-0211 |

### UI-0009 · 2026-07-28 · 布局

| 字段 | 内容 |
|------|------|
| 涉及 | `inventory_entry.html`、`inventory_entry.js` |
| 内容 | 删除 `#invEntryHint` 长说明；未选工序时不显示操作条；页脚一行说明 |
| 规则 | 否（遵循既有 V3 §1 清爽原则） |
| 关联 CL | CL-0209 |

### UI-0008 · 2026-07-28 · 交互

| 字段 | 内容 |
|------|------|
| 涉及 | `inventory_entry.js`、`inventory.css` |
| 内容 | 卡片固定三态只读；编辑区改为从/到状态+数量登记流转，取消直接改数表单 |
| 规则 | 否 |
| 关联 CL | CL-0208 |

### UI-0007 · 2026-07-28 · 交互

| 字段 | 内容 |
|------|------|
| 涉及 | `inventory_entry.html/js`、`inventory.css` |
| 内容 | 工序库存：默认只读卡片（对齐库存总览）；**点击**工序后在下方展开编辑面板，卡片等高整齐 |
| 规则 | 否 |
| 关联 CL | CL-0207 |

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
