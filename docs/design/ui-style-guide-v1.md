# WKT 销售管理系统 · UI 设计基线（V1.0）

> **生效版本**：v0.3.8（2026-05-30 · HP 科技蓝默认主题）  
> **设计来源**：[`docs/design/DESIGN.md`](DESIGN.md) · HP · `#024ad8`  
> **适用范围**：`test_impl/web` 及后续所有 Web 模块  
> **强制要求**：新增页面、组件、模块须遵循本基线；偏离须登记变更日志并说明理由。

---

## 1. 设计原则

1. **层级清晰**：菜单、页面标题、区块标题、说明文字、表单标签各有统一字号/字重，不可混用。  
2. **紧凑实用**：业务录入表单优先信息密度，避免过大留白。  
3. **一屏一事**：录入方式、功能面板按步骤展示，未选择前不展示后续区域。  
4. **复用优先**：新模块复用 `style.css` 变量与现有组件类，不另起一套视觉语言。

---

## 2. 布局结构

```
┌─────────────┬──────────────────────────────────┐
│  侧栏导航    │  页面标题 + 说明                    │
│  (240px)    ├──────────────────────────────────┤
│             │  内容区（卡片 stack）                 │
│             │  ┌ card ──────────────────────┐   │
│             │  │ 区块标题 / 操作              │   │
│             │  │ 表单或表格                   │   │
│             │  └────────────────────────────┘   │
└─────────────┴──────────────────────────────────┘
```

- **侧栏**：深灰底（`#0f1011`）、右边框；品牌区 +「功能模块」分组 + 模块列表。  
- **主区**：`--bg` 近黑底；顶栏 `--bg-soft` + 底边框。  
- **卡片**：`--bg-soft` 底、`--radius-lg` 12px 圆角、发丝线边框（无阴影）；区块间距 `1.15rem`。

---

## 3. 色彩（`:root` 变量 · HP 科技蓝默认）

| 用途 | 变量 | 值 |
|------|------|-----|
| 画布 / 侧栏 | `--bg` / `--sidebar-bg` | `#ffffff` |
| 内容区底 | `--bg-soft` | `#f7f7f7` |
| 卡片 | `--surface` | `#ffffff` |
| 主色 | `--primary` | `#024ad8`（HP Electric Blue） |
| 主色 Hover | `--primary-hover` | `#0e3191` |
| 主色浅底 | `--primary-soft` | `#c9e0fc` |
| 正文 | `--text` | `#1a1a1a` |
| 次级文字 | `--text-secondary` | `#3d3d3d` |
| 辅助/说明 | `--muted` | `#636363` |
| 边框 | `--border` / `--border-strong` | `#e8e8e8` / `#c2c2c2` |
| 表格表头 | `--table-header-bg` | `#024ad8` |
| 成功 / 警告 / 危险 | `--success` / `--warning` / `--danger` | 见 `themes.css` |

切换主题：`/themes` 或改 `themes.css` / `localStorage.wkt-theme`。

---

## 4. 字体

- **字体栈**：`"Inter", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif`  
- **层级变量**（定义于 `style.css` `:root`，同级必须统一）：

| 层级 | CSS 变量前缀 | 用于 |
|------|-------------|------|
| 侧栏 L1 | `--type-nav-brand-*` | 系统名称 |
| 侧栏 L2 | `--type-nav-sub-*` | 系统副标题 |
| 侧栏 L3 | `--type-nav-group-*` | 「功能模块」分组标签（大写） |
| 侧栏 L4 | `--type-nav-item-*` | 模块菜单项 |
| 页面 L5 | `--type-page-title-*` | 页面主标题 |
| 页面 L6 | `--type-page-desc-*` | 页面说明 |
| 区块 L7 | `--type-section-title-*` | 卡片/区块标题（h3、h4 同级） |
| 区块 L8 | `--type-section-sub-*` | 卡片描述、提示文字 |
| Tab | `--type-tab-*` | 录入方式切换等 Tab 按钮 |

新标题不得硬编码 `font-size`；应使用上述变量或扩展变量后全局登记。

---

## 5. 组件规范

### 5.1 模块导航（`.module-item`）

- 圆角 8px；hover 浅灰底；当前页 `--primary-soft` + 主色文字。  
- 禁用项 `opacity: 0.5`，不可点击。

### 5.2 录入方式 Tab（`.mode-btn`）

- 两列等宽；未选浅底 + 边框；选中 `--primary-soft` + 主色边框/文字。  
- 切换面板用 `.is-hidden`（`display: none !important`），**不用**单独 `[hidden]` 与 flex 混用。

### 5.3 表单（`.entry-card`）

- 5 列网格；组间 `.entry-divider` 细线分隔。  
- 标签上置、小字号（0.6875rem）；输入框紧凑（高约 2rem）。  
- 下拉旁「+」用 `.btn.btn-add` 方钮，不用宽文字按钮。

### 5.4 数据表格（`.data-table`）

- 表头紫底白字；行 hover 浅灰。  
- OCR 预览单元格内联输入（`.pv`）保持紧凑。

### 5.5 按钮

| 类 | 用途 |
|----|------|
| `.btn-primary` | 主操作（提交、识别、搜索） |
| `.btn-outline` | 次要操作（清空） |
| `.btn-sm` | 表格/工具栏小按钮 |
| `.btn-add` | 主数据「+」 |

### 5.6 悬停完整内容（`.hover-tip`）

- **仅**使用自定义深色浮动 tooltip。  
- **禁止**设置 `title` 属性（避免与原生 tooltip 重叠）。

---

## 6. 交互模式

| 场景 | 行为 |
|------|------|
| 进入订单录入 | 仅显示录入方式 Tab + 提示；不显示上传/预览/手动表单 |
| 选 OCR | 显示上传区；识别成功后显示预览 |
| 选手动 | 显示手动表单 |
| 列表「修改」 | 自动切到手动录入并载入 |
| 已录入列表 | 两种录入模式下始终可见 |

---

## 7. 新模块接入 checklist

- [ ] 复用 `app-layout` + `sidebar` + `page-header` + `content-stack`  
- [ ] 引入 `/static/style.css`（必要时追加模块 CSS，不覆盖基线变量）  
- [ ] 标题/说明使用层级变量  
- [ ] 主操作用 `.btn-primary`，卡片用 `.card`  
- [ ] 登记 CL + 更新 SOP；若扩展 UI 基线则更新本文档版本  

---

## 8. 参考文件

| 文件 | 说明 |
|------|------|
| `test_impl/web/static/style.css` | 全局样式与变量源 |
| `test_impl/web/templates/index.html` | 订单录入参考页 |
| `test_impl/web/templates/cost_analysis.html` | 第二模块参考页 |
| `docs/VERSION.md` | 当前版本号 |
| `docs/change/CHANGELOG.md` | 变更历史 |
