---
name: wkt-ui-design
description: WKT 网页 UI 全局设计规范。在新建/修改页面布局、CSS、录入流程、列表表格、顶栏、主题、间距时使用；用户提到布局、UI、样式、留白、全局规则、follow 订单/BOM 模式时使用。
---

# WKT UI 设计

## 何时使用

- 新建/改 Web 页面、CSS、布局、交互
- 用户提到：清爽、留白、全局规则、排版、UI 设计

## 步骤（必须按序）

1. **通读** [`docs/design/ui-layout-rules.md`](../../../docs/design/ui-layout-rules.md) **V3 全文**
2. 读 [`docs/design/GLOBAL-RULES-INDEX.md`](../../../docs/design/GLOBAL-RULES-INDEX.md)
3. 读 [`docs/design/UI-CHANGELOG.md`](../../../docs/design/UI-CHANGELOG.md) 最新 5 条
4. 对照参考页实现（§16）
5. 登记 UI-CHANGELOG + CL；新范式则更新 ui-layout-rules.md

## 全局要点（不可只记最近）

| 领域 | 规则 |
|------|------|
| 布局 | 顶栏、全宽 content-stack、页脚 page-desc |
| 录入 | mode-card → mode-panel；BOM 式清爽 upload |
| 列表 | list-card + list-table + 行状态色 |
| 间距 | --wkt-module-* / --wkt-list-* |
| 主题 | themes.css 变量，HP 蓝默认 |
| 字体 | --type-* 层级；料号等宽 |
| 组件 | btn-primary/outline/sm；hover-tip 非 title |

## 禁止

- 只看最近对话、不读 V3 全文就改 UI
- 侧栏布局、默认展开录入、长 card-desc
- 硬编码字号颜色、新表格风格、改 UI 不登记

## 文档

- 规范：[`ui-layout-rules.md`](../../../docs/design/ui-layout-rules.md)
- 索引：[`GLOBAL-RULES-INDEX.md`](../../../docs/design/GLOBAL-RULES-INDEX.md)
- 变更：[`UI-CHANGELOG.md`](../../../docs/design/UI-CHANGELOG.md)
