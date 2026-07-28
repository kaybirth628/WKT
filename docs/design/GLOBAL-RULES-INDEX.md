# WKT · 全局规则索引

> Agent 改 **UI / 排版 / 布局** 时：**先读 [`ui-layout-rules.md`](ui-layout-rules.md)（V3 全文）**，再读 [`UI-CHANGELOG.md`](UI-CHANGELOG.md) 最新条目。  
> 本文档列出仓库内 **所有** 与界面相关的规则来源，避免只跟最近对话、遗漏历史基线。

---

## 1. 必读（UI 任务）

| 优先级 | 文件 | 内容 |
|--------|------|------|
| ★★★ | [`ui-layout-rules.md`](ui-layout-rules.md) | **全局 UI 设计规范 V3**（唯一权威） |
| ★★☆ | [`UI-CHANGELOG.md`](UI-CHANGELOG.md) | UI 专用变更日志 |
| ★★☆ | [`DESIGN.md`](DESIGN.md) | 品牌色 / HP 主题 Token |
| ★☆☆ | [`ui-style-guide-v1.md`](ui-style-guide-v1.md) | 历史 V1（已 superseded，仅考古） |

---

## 2. Agent / 工作流规则（`.cursor/`）

| 文件 | 内容 |
|------|------|
| [`.cursor/rules/wkt-production-safety.mdc`](../../.cursor/rules/wkt-production-safety.mdc) | **生产安全**（alwaysApply） |
| [`.cursor/rules/wkt-change-governance.mdc`](../../.cursor/rules/wkt-change-governance.mdc) | 变更治理 CL+BF+SOP |
| [`.cursor/rules/wkt-ui-design.mdc`](../../.cursor/rules/wkt-ui-design.mdc) | UI 强制规则 |
| [`.cursor/rules/wkt-agent-workflow.mdc`](../../.cursor/rules/wkt-agent-workflow.mdc) | 总工作流 |
| [`.cursor/skills/wkt-change-governance/SKILL.md`](../../.cursor/skills/wkt-change-governance/SKILL.md) | 变更治理 skill |
| [`.cursor/skills/wkt-ui-design/SKILL.md`](../../.cursor/skills/wkt-ui-design/SKILL.md) | UI skill |

---

## 3. 项目协作（`docs/`）

| 文件 | 内容 |
|------|------|
| [`AGENTS.md`](../../AGENTS.md) | 合规清单、顶栏基线 |
| [`change/CHANGELOG.md`](../change/CHANGELOG.md) | 功能变更 CL-XXXX |
| [`change/BUG-FIX-LOG.md`](../change/BUG-FIX-LOG.md) | **Bug 根因与防复发 BF-XXXX** |
| [`change/AGENT-COMPLIANCE.md`](../change/AGENT-COMPLIANCE.md) | Agent 每次改动 Checklist |
| [`change/PRODUCTION-SAFETY.md`](../change/PRODUCTION-SAFETY.md) | **生产安全**（3 bat、禁止覆盖云端 data） |
| [`SOP/系统操作SOP.md`](../SOP/系统操作SOP.md) | 用户操作说明（用户可见变更必更） |
| [`handoff/SESSION-20260530-ui-baseline.md`](../handoff/SESSION-20260530-ui-baseline.md) | 顶栏 UI 会话摘要 |

---

## 4. 源码权威（`test_impl/web/`）

| 文件 | 定义内容 |
|------|----------|
| `static/style.css` | 布局、 typography 变量、top-nav、mode-*、list-table、entry-*、按钮、卡片 |
| `static/themes.css` | 色彩变量、多主题 |
| `static/cost.css` | 成本/BOM 模块布局扩展 |
| `static/app.js` | 订单子模块切换、页脚 `#pageDesc` |
| `templates/_order_sidebar.html` | 顶栏导航结构 |
| `templates/_theme_head.html` | 主题 + 字体入口 |
| `templates/_font_links.html` | Google Fonts |
| `templates/index.html` | 订单录入参考 |
| `templates/cost_entry.html` | BOM 清爽录入参考 |
| `templates/cost_query.html` | 列表查询参考 |

---

## 5. 用户级规则（Cursor User Rules）

| 规则 | 内容 |
|------|------|
| **ERP 全局字体规范** | Noto Sans SC + DM Sans；body 15px；料号等宽；改字体不改字号列宽 |
| **代码风格** | 最小 diff、匹配现有约定、不过度抽象 |

已并入 `ui-layout-rules.md` §5。

---

## 6. 历史 UI 里程碑（CHANGELOG 摘要）

| CL | 日期 | UI 要点 |
|----|------|---------|
| CL-0103 | 2026-05-30 | 顶栏导航、全宽、页脚说明、订单下拉 |
| CL-0108 | 2026-07-11 | 成本分析拆分、客商维护 |
| CL-0194~0197 | 2026-07-28 | BOM 导入 UX、紧凑 list-table、清爽 mode-card |
| CL-0198 | 2026-07-28 | UI 规则文档与 Agent 接入 |
| CL-0199 | 2026-07-28 | V3 全局规则合并 |

---

## 7. 改 UI 时的登记要求

1. **`docs/design/UI-CHANGELOG.md`** — UI-XXXX
2. **`docs/change/CHANGELOG.md`** — CL-XXXX（**任何代码改动必写**）
3. **修复类** → **`docs/change/BUG-FIX-LOG.md`** — BF-XXXX
4. **用户可见** → **`docs/SOP/系统操作SOP.md`**
5. **`ui-layout-rules.md`** — 若新增全局 UI 范式

---

## 8. 用户长期偏好（固定备忘）

- 界面要 **清爽**：不要反复调布局
- 录入页 follow **订单录入 / BOM 录入** mode-card 模式
- 说明文字 **能少则少**；页脚一行即可
- **不要**改回左侧栏、不要把订单子菜单做成固定第二行
