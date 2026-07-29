# WKT · 全局 UI 设计规范（当前生效）

> **版本**：V3 · 2026-07-28  
> **状态**：**唯一权威** — 整合 V1 基线、顶栏 UI（CL-0103）、list-table、清爽录入（CL-0197）及 `style.css` / `themes.css` 全部约定  
> **取代**：`ui-style-guide-v1.md`（侧栏时代内容已合并并更正）  
> **用户偏好**：**清爽** — 少说明、少留白、一屏一事；改 UI 前先对照本文，勿反复猜测。

---

## 0. 规则层级与文档地图

### 0.1 优先级（Agent 必须遵守）

1. **用户明确指令**（最高）
2. **`docs/design/ui-layout-rules.md`（本文件）** — 全局 UI / 排版
3. **`docs/design/UI-CHANGELOG.md`** — UI 变更历史（改完必登记）
4. **`AGENTS.md`** — 合规清单、顶栏基线提醒
5. **`.cursor/rules/wkt-ui-design.mdc`** — 指向本文件的强制规则
6. **`docs/change/CHANGELOG.md`** — 功能变更（CL-XXXX）

### 0.2 源码与文档对照

| 类型 | 权威源码 | 说明文档 |
|------|----------|----------|
| 色彩 / 主题 | `test_impl/web/static/themes.css` | [`DESIGN.md`](DESIGN.md) |
| 排版 / 布局 / 组件 | `test_impl/web/static/style.css` | **本文件** |
| 成本 / BOM 扩展 | `test_impl/web/static/cost.css` | 本文件 §14 |
| 顶栏 HTML | `test_impl/web/templates/_order_sidebar.html` | §2（文件名历史遗留，实为 top-nav） |
| 字体链接 | `test_impl/web/templates/_font_links.html` | §5 |
| 顶栏基线会话 | — | [`SESSION-20260530-ui-baseline.md`](../handoff/SESSION-20260530-ui-baseline.md) |
| TP/ERP 字体目标 | 用户规则 `erp-ui-typography` | §5.1 |

### 0.3 Agent 工作流

**改 UI / 排版 / 布局前：**

1. 通读 **本文件**（至少 §1–§9 + 对应页面类型章节）
2. 读 `UI-CHANGELOG.md` 最新 5 条
3. 打开 **参考页**（§16）对照实现
4. 完成后登记 UI-CHANGELOG + 主 CHANGELOG（若用户可见）

---

## 1. 设计原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | **层级清晰** | 导航、页标题、区块标题、说明、标签各有统一字号/字重/颜色变量，**禁止**随意硬编码。 |
| 2 | **清爽** | 删多余说明、合并重复区块；新页默认不用长 `card-desc`、系统横幅、重复标题。 |
| 3 | **一屏一事** | 录入类先选模式，再出现上传/表单/预览；未选前仅 mode 按钮 + 一句 hint。 |
| 4 | **紧凑实用** | 业务模块用 `--wkt-module-*` 紧凑间距；表单/列表优先信息密度。 |
| 5 | **复用优先** | 复用 `style.css` 类与变量；模块只追加 CSS（如 `cost.css`），不另起视觉语言。 |
| 6 | **全宽** | 内容区铺满；子页标题在内容区顶；模块说明在 **页脚** 一行。 |

---

## 2. 全局布局架构（v0.5.1+ · CL-0103）

### 2.1 结构（当前标准 · 非侧栏）

```
┌──────────────────────────────────────────────────────────────┐
│ top-nav（sticky，高 ~52px）                                    │
│   WKT 品牌 | 订单管理▾ | 对账▾ | 客商▾ | BOM▾ | 库存▾ | AI   │
├──────────────────────────────────────────────────────────────┤
│ app-main（background: --bg-soft，flex 列）                     │
│   main.content-stack 或 .cost-stack                           │
│     h3.submodule-page-title                                   │
│     section.card / .mode-card / .list-card …                  │
├──────────────────────────────────────────────────────────────┤
│ footer.page-footer（margin-top: auto）                          │
│   .page-title（通常 hidden）+ .page-desc 一行说明               │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 硬性约束

| 项 | 规则 |
|----|------|
| 导航 | **顶部导航 + 下拉子菜单**；订单子功能在「订单管理▾」内，**非**固定第二行 |
| 侧栏 | **禁止**改回左侧固定侧栏（除非用户明确要求） |
| 页眉 | 独立 `page-header` 不占顶栏位；子页用 `.submodule-page-title` |
| 页脚 | 模块名 + **一行** `.page-desc`；`index.html` 用 `#pageTitle` / `#pageDesc` 随子模块切换 |
| 宽度 | 业务区 **100% 全宽**；成本等用 `cost-layout` / `cost-stack` 铺满 |
| 文件名 | `_order_sidebar.html` = 顶栏模板（历史名，勿按侧栏理解） |

### 2.3 HTML 骨架（独立页）

```html
<div class="app-layout">
  {% include '_order_sidebar.html' %}
  <div class="app-main">
    <main class="content-stack"><!-- 或 cost-stack -->
      <h3 class="section-h3 submodule-page-title">子页标题</h3>
      <!-- 业务卡片 -->
    </main>
    <footer class="page-footer">
      <h2 class="page-title">模块名</h2>
      <p class="page-desc">一行说明</p>
    </footer>
  </div>
</div>
```

Head 必须：`{% include '_theme_head.html' %}` + `/static/style.css?v=…` + 模块 CSS。

---

## 3. 顶栏导航（`.top-nav`）

### 3.1 结构类名

| 类名 | 用途 |
|------|------|
| `.top-nav` |  sticky 顶栏容器 |
| `.top-nav-inner` | flex 行；`min-height: 52px`；左右 padding |
| `.top-nav-brand` | WKT 品牌链接 |
| `.top-nav-menu` | 模块链接区 |
| `.top-nav-link` | 单项链接/触发器；圆角 8px |
| `.top-nav-dropdown` | 带下拉的模块 |
| `.top-nav-dropdown-menu` | 下拉面板 |
| `.top-nav-dropdown-item` | 子菜单项；`.active` 当前页 |
| `.top-nav-head-link.is-active` | 无下拉模块的当前高亮 |
| `.top-nav-dropdown.is-module-active` | 下拉模块内有 active 子项时触发器高亮 |

### 3.2 交互样式

- 默认：透明底 + `--sidebar-text-secondary`
- Hover：`--sidebar-item-hover`
- 当前/激活：`--sidebar-item-active-bg` + `--sidebar-item-active-text` + 主色淡边框
- 子项：含 `.module-icon` + `.module-name`；分组用 `.top-nav-dropdown-divider` + `.top-nav-dropdown-label`

### 3.3 模块组织（现网）

- **订单管理▾**：录入、出货明细、未结、结案
- **对账▾**：应收、应付
- **客商信息维护▾**：客户、供应商
- **BOM信息▾**：BOM录入、BOM查询
- **库存▾**：总览、工序出入库、流水、计划
- **AI** 等独立链接

新增模块：在 `_order_sidebar.html` 追加 dropdown 或 link，样式复用现有类。

---

## 4. 色彩与主题

### 4.1 默认主题：HP 科技蓝（`data-theme="hp"`）

| 用途 | 变量 | 默认值 |
|------|------|--------|
| 画布 | `--bg` | `#ffffff` |
| 内容区底 | `--bg-soft` | `#f7f7f7` |
| 卡片面 | `--surface` | `#ffffff` |
| Hover 面 | `--surface-hover` | `#f0f0f0` |
| 主色 | `--primary` | `#024ad8` |
| 主色 Hover | `--primary-hover` | `#0e3191` |
| 主色浅底 | `--primary-soft` | `#c9e0fc` |
| 焦点环 | `--focus-ring` | `0 0 0 3px rgba(2,74,216,0.15)` |
| 正文 | `--text` | `#1a1a1a` |
| 次级 | `--text-secondary` | `#3d3d3d` |
| 辅助 | `--muted` | `#636363` |
| 边框 | `--border` / `--border-strong` | `#e8e8e8` / `#c2c2c2` |
| 表头 | `--table-header-bg` / `--table-header-text` | `#024ad8` / `#fff` |
| 成功/警告/危险 | `--success` / `--warning` / `--danger` | 见 `themes.css` |
| 圆角 | `--radius` / `--radius-lg` | `8px` / `12px` |
| 阴影 | `--shadow-sm` | 轻阴影；minimal-white 主题下卡片可无阴影 |

### 4.2 主题切换

- 预览：`/themes`
- 存储：`localStorage.wkt-theme`
- 实现：`themes.css` + `theme.js`
- 可选：`classic` · `stripe` · `ibm` · `notion` · `minimal-white` 等

**规则**：新 UI 只引用 CSS 变量，不写死 hex（行高亮语义色除外，见 §8.3）。

---

## 5. 字体与排版

### 5.1 字体栈

**当前实现**（`_font_links.html` + `style.css`）：

```css
--font: "Inter", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
body { font-size: 0.9375rem; line-height: 1.5; -webkit-font-smoothing: antialiased; }
```

**TP/ERP 全局目标**（新页 / 字体大改时对齐）：

```html
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&family=DM+Sans:wght@500;600;700&display=swap" />
```

```css
font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", "DM Sans", system-ui, sans-serif;
```

**约束**：改字体时 **只改** `font-family` 与 Google Fonts；**不顺便改**字号、列宽、间距。

### 5.2 等宽（料号 / 表名 / 代码）

```css
Consolas, "Courier New", ui-monospace, monospace
```

用于：`.list-td-mono`、OCR 料号列、SQL/表名展示。**不与正文混用。**

### 5.3  typography 层级（`:root` 变量 · 必须复用）

| 层级 | 变量前缀 | 字号参考 | 用于 |
|------|----------|----------|------|
| 导航品牌 | `--type-nav-brand-*` | 0.9375rem / 700 | 系统名 |
| 导航副标题 | `--type-nav-sub-*` | 0.75rem | 副标题 |
| 导航分组 | `--type-nav-group-*` | 0.6875rem / 大写 | 「功能模块」类标签 |
| 导航项 | `--type-nav-item-*` | 0.875rem | 菜单项 |
| 页面标题 | `--type-page-title-*` | 1.25rem / 700 | `.page-title` |
| 页面说明 | `--type-page-desc-*` | 0.8125rem | `.page-desc`、页脚 |
| 区块标题 | `--type-section-title-*` | 0.9375rem / 700 | `h3`、`.submodule-page-title` |
| 区块副文 | `--type-section-sub-*` | 0.8125rem | `.mode-hint`、`.card-desc` |
| Tab/模式钮 | `--type-tab-*` | 0.875rem / 600 | `.mode-btn`、顶栏链接 |

**禁止**在新页面硬编码标题 `font-size`；扩展层级须在本文件登记。

### 5.4 表单标签

| 场景 | 标签字号 |
|------|----------|
| 通用 `.field span` | 0.8125rem / 500 |
| 紧凑 `.entry-card .field span` | 0.6875rem |
| 输入框 | 0.9375rem（entry 内 ~0.8125rem，高约 2rem） |

---

## 6. 间距系统

### 6.1 业务模块统一变量（订单 / 成本 / 客商 · **优先于** `.card` 默认）

| 变量 | 值 | 用途 |
|------|-----|------|
| `--wkt-module-pad-x` | 0.75rem | `content-stack` 水平 padding |
| `--wkt-module-pad-y` | 0.5rem | `content-stack` 垂直 padding |
| `--wkt-module-gap` | 0 | stack 内卡片间距（紧凑） |
| `--wkt-module-card-pad` | 0.55rem 0.65rem 0.75rem | `.list-card`、`.mode-card`、上传卡 |
| `--wkt-module-card-gap` | 0.45rem | 卡片内 flex gap |
| `--wkt-module-footer-pad` | 0.65rem 0.75rem 0.75rem | 页脚 |
| `--wkt-module-desc-size` | 0.75rem | 页脚说明字号 |
| `--wkt-module-title-margin` | 0 0 0.25rem | 子页标题 |

选择器：`.app-main:has(.submodule-panel) .content-stack`、`.app-main:has(.cost-stack) .content-stack`。

### 6.2 列表表格

| 变量 | 值 |
|------|-----|
| `--wkt-list-cell-py` | 0.45rem |
| `--wkt-list-cell-px` | 0.32rem |
| `--wkt-list-head-py` | 0.42rem |
| `--wkt-list-head-px` | 0.32rem |

### 6.3 默认 vs 业务模块

| 元素 | 默认 `.card` | 业务模块覆盖 |
|------|-------------|-------------|
| padding | 1.5rem | `--wkt-module-card-pad` |
| gap | 1.15rem | `--wkt-module-card-gap` |
| content-stack gap | 1.15rem | `--wkt-module-gap`（0） |

**新模块**在业务区内应走 **紧凑覆盖**，勿用默认 1.5rem 大 padding。

---

## 7. 组件规范

### 7.1 卡片 `.card`

- 背景 `--surface`；边框 `--border`；圆角 `--radius-lg`
- 默认 `box-shadow: var(--shadow-sm)`（minimal-white 可无阴影）
- 变体：`.list-card`、`.upload-card`、`.preview-card`、`.entry-card`、`.mode-card`（padding 0.65rem）

### 7.2 卡片头（慎用 · 清爽原则）

| 类名 | 说明 |
|------|------|
| `.card-head` | 图标 + 标题行 |
| `.card-icon` | 38×38 主色浅底图标块 |
| `.card-desc` | 副说明（**新页默认不加**） |

历史：订单 OCR 上传区仍有 `card-head`；**新模块以 BOM 录入上传区为准**（§9.3）。

### 7.3 按钮

| 类 | 用途 |
|----|------|
| `.btn-primary` | 主操作：提交、识别、搜索、解析 |
| `.btn-outline` | 次要：清空、应用到全部 |
| `.btn-ghost` | 弱操作：关闭、收起 |
| `.btn-sm` | 表格/工具栏小按钮 |
| `.btn-add` | 主数据「+」方钮（非宽文字） |
| `.btn-block` | 全宽 |

公共：圆角 8px；`font-family: inherit`；padding 约 0.7rem 1.15rem（`.btn-sm` 更小）。

### 7.4 表单

| 类 | 说明 |
|----|------|
| `.form` / `.form-stack` | 纵向表单容器 |
| `.field` | 标签上置 + 输入 |
| `.entry-card` + `.entry-grid` | 订单手动录入：5 列网格 |
| `.entry-divider` | 组间 1px 分隔 |
| `.customer-form` | 客商维护横向 field |

输入：边框 `--border-strong`；圆角 8px；focus 时 `--primary-focus` + `--focus-ring`。  
select 同表单风格（见 `cost.css` / 全局 `select`）。

### 7.5 消息与状态

| 类 | 说明 |
|----|------|
| `.msg` | 操作反馈；`.error` / `.ok` |
| `.msg:empty` | **display: none**（不占位） |
| `.verify-summary` | OCR 校验摘要；`.verify-ok` / `.verify-warn` |
| `.recognize-progress` | OCR 进度条 |
| `.bom-import-success` | 导入成功条 |

### 7.6 悬停全文 `.hover-tip`

- **仅**用 JS + 固定定位深色 tooltip
- **禁止** `title` 属性（避免双 tooltip）
- 用于：说明列、OCR 核对长文

### 7.7 隐藏

| 方式 | 用途 |
|------|------|
| `.is-hidden` | 面板/卡片切换（`display: none !important`） |
| `[hidden]` | 勿与 flex 布局混用以控制主面板 |
| `.submodule-panel.is-hidden` | 订单子模块切换 |

---

## 8. 列表与表格（`.list-table`）

### 8.1 结构

```html
<section class="card list-card">
  <div class="filter-bar filter-bar-compact">…</div>
  <div class="table-wrap list-table-wrap">
    <table class="data-table list-table">
      <thead><tr class="list-header-row">…</tr></thead>
      <tbody>…</tbody>
    </table>
  </div>
</section>
```

### 8.2 列类型 class

| 表头 | 单元格 |
|------|--------|
| `.list-th-text` | `.list-td-text`（左对齐） |
| `.list-th-seq` | `.list-td-seq`（居中序号） |
| `.list-th-action` / `.action-cell` | 操作列居中 |
| — | `.list-td-mono`（料号等宽） |
| — | `.list-td-money`（金额） |
| `.list-th-filterable` | 列筛选按钮 `.list-filter-btn` |

表格：`table-layout: fixed`；字号 **0.75rem**；表头 sticky；表头字号 **0.6875rem**；主色底白字。

### 8.3 行状态色（语义 · 勿改含义）

| 类 | 含义 |
|----|------|
| `.row-new-highlight` | 刚新增/刚更新（黄，15s 淡出） |
| `.row-today-highlight` | 今日相关（紫） |
| `.row-order-overdue` | 订单逾期（橙） |
| `.row-delivery-warning` | 交期预警（黄棕） |
| `.row-delivery-overdue` | 交期逾期（红） |
| `.row-stock-critical` / `.row-stock-warn` | 库存预警 |
| `.row-editing` / `.is-editing` | 编辑中（主色浅底） |
| hover（默认行） | 绿色 mix 浅底 |

### 8.4 筛选栏 `.filter-bar`

- 横向排列输入/选择 + 搜索按钮
- 紧凑变体：`.filter-bar-compact`
- 不单独做大标题区；hint 用 `.filter-hint` 小字

### 8.5 滚动策略

| 场景 | 规则 |
|------|------|
| 订单/客商/成本 **查询列表** | 可用 `.list-scroll-host` 占满剩余高度 |
| **导入预览** | **不要** `max-height` 内滚动；页内自然展开 |
| 表格横向 | `.list-table-wrap { overflow-x: auto }` 当列多时 |

---

## 9. 录入类页面

### 9.1 模式切换（强制模板）

```html
<section class="card mode-card">
  <div class="mode-switch" role="tablist" aria-label="录入方式">
    <button type="button" class="mode-btn" aria-selected="false">方式 A</button>
    <button type="button" class="mode-btn" aria-selected="false">方式 B</button>
  </div>
  <p class="mode-hint">请先选择录入方式</p>
</section>
<div class="mode-panel is-hidden">…</div>
```

| 状态 | 行为 |
|------|------|
| 初始 | 无 `active`；hint 可见；panel 全 hidden |
| 已选 | 对应 btn `active`；hint hidden；panel 显示 |
| JS | 勿默认展开某模式（除非 URL 参数） |

`.mode-btn`：等宽 flex:1；未选 `--bg-soft`；选中 `--primary-soft` + 主色边框。

### 9.2 订单录入交互（`index.html`）

| 场景 | 行为 |
|------|------|
| 进入录入 | 仅 mode-card + hint |
| 选 OCR | 显示上传；识别成功后 preview |
| 选手动 | 显示 `.entry-card` 表单 |
| 列表点修改 | 切手动并载入 |
| 已录入列表 | 两种模式下 **始终可见** |

OCR 布局（历史，功能复杂可保留）：`.ocr-review-layout` 原件在上、表格在下；原件区 `.ocr-source-block`。**新简单录入勿复制 OCR 长 hint。**

### 9.3 上传区（清爽标准 · `cost_entry.html`）

```html
<section class="card upload-card">
  <div class="upload-row">
    <input type="file" … />
    <button class="btn btn-primary">解析预览</button>
  </div>
  <p class="msg"></p>
</section>
```

`.upload-row`：file input flex:1 + 主按钮；file input 圆角 8px。

### 9.4 预览与导入

- 预览：`preview-card list-card` + `list-table`
- 批量操作：**底部**主按钮（如「批量上传」）
- 成功：清空预览、恢复上传、简短 success banner；**勿**成功后 silent re-parse
- 统一客户等工具条：紧凑单行，非大段说明

### 9.5 手动录入表单

- 订单：`entry-card` + `entry-grid`（5 列）
- BOM/成本：`cost-form-card` + `.field` 网格（见 `cost_entry.html`）
- 标签紧凑；placeholder 代替长说明

---

## 10. 弹窗与 iframe

| 类 | 用途 |
|----|------|
| `.cost-modal` | 成本预览等模态 |
| `.ship-dn-frame` | 出货送货单确认 iframe |

模态：`.cost-modal-panel` + head/body；关闭用 `.btn-ghost`。

---

## 11. 订单 SPA 子模块

- 容器：`.submodule-panel` + `.is-hidden` 切换
- 标题：`.submodule-page-title` 每 panel 顶部
- 页脚文案：`app.js` 的 `SUBMODULES` 驱动 `#pageDesc`
- 列表 panel：`.list-scroll-host` 可 flex 撑满

---

## 12. 客商维护特殊规则

- 表单卡 `.dn-maint-card`：**勿 flex 拉伸**（`:has(.dn-new-form) { flex: 0 0 auto }`）
- 避免表单上方大面积留白
- 列表卡 `:has(.list-scroll-host)` 随内容高度

---

## 13. 成本 / BOM 模块（`cost.css`）

- 容器：`.cost-stack` 全宽
- 录入：遵循 §9；`.cost-stack .upload-card` 用 module 变量 padding
- 查询：`list-card` + `list-table`（与订单列表一致）
- 分析页：`cost-layout` 双栏 grid（小屏单列）
- 工艺单价：`.process-grid` auto-fill

**规则**：只在 `cost.css` 追加；不覆盖 `themes.css` 变量。

---

## 14. 静态资源与验证

| 项 | 规则 |
|----|------|
| CSS/JS 缓存 | 改后 bump `?v=YYYYMMDD-描述` |
| 后端 build | 改 UI 相关 API 时 bump `/api/health` 的 `build` |
| 主题 | 所有页面 include `_theme_head.html` |
| 验证 | 重启 bat + Ctrl+F5；查 health build |

---

## 15. 反模式

| 反模式 | 正确 |
|--------|------|
| 左侧固定侧栏 | 顶栏 + 下拉 |
| 进入页展开全部区域 | mode-card 分步 |
| 3 段以上说明 | 页脚一行 + placeholder |
| 预览表格外包 max-height 滚动 | 自然高度或整页滚 |
| 每卡片 card-head + 长 desc | 仅必要时；新页用 BOM 上传标准 |
| 新表格样式 | `list-table` |
| 硬编码颜色/字号 | CSS 变量 |
| 改 UI 不登记 | UI-CHANGELOG + CL |
| 料号用正文字体 | `list-td-mono` |
| 用 title 做 tooltip | `.hover-tip` |

---

## 16. 参考页索引

| 页面 | 模板 | 学习点 |
|------|------|--------|
| 订单录入 | `index.html` | mode 切换、entry-grid、OCR、列表共存 |
| BOM 录入 | `cost_entry.html` | **清爽上传**、mode-card、导入预览 |
| BOM 查询 | `cost_query.html` | list-table、筛选 |
| 客商维护 | `index.html#delivery` | dn-maint、表单不拉伸 |
| 库存 | `inventory*.html` | 独立页 footer + stack |
| 主题预览 | `design_gallery.html` | 多主题 |

---

## 17. 新模块 Checklist

- [ ] `app-layout` + 顶栏 + `content-stack` / 模块 stack
- [ ] `_theme_head.html` + `style.css` + 模块 CSS
- [ ] 子页标题 + 页脚一行说明
- [ ] 录入 → §9 mode 模板；列表 → §8 list-table
- [ ] 间距走 `--wkt-module-*` / `--wkt-list-*`
- [ ] 字体/颜色走变量；料号等宽
- [ ] `?v=` + build bump
- [ ] `UI-CHANGELOG.md` + `CHANGELOG.md`
- [ ] 若扩展全局范式 → 更新 **本文件** 对应章节

---

## 18. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| V1 | 2026-05-30 | `ui-style-guide-v1.md` 侧栏时代 |
| V2 | 2026-07-28 | 清爽录入 + UI-CHANGELOG 体系 |
| V3 | 2026-07-28 | **合并全部全局规则**：顶栏、主题、 typography、组件、list-table、间距、交互 |
