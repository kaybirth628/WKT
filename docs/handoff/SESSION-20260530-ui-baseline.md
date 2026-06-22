# 会话摘要 · UI 基线（2026-05-30）

> **用途**：对话长度受限时，新 Agent 先读本文件 + `CHANGELOG` 顶部 + `AGENTS.md`。  
> **Git 回退**：`git log --oneline` → `git checkout <commit>` 或 tag `ui-baseline-20260530`。

## 用户目标（已达成）

1. 内容区全宽，侧栏不占横向空间 → **顶部导航**
2. 订单子功能 → **「订单管理」下拉**（非固定第二行）
3. 模块标题/说明不占顶部 → **页脚 `page-footer`**
4. 成本分析铺满 → **`cost-layout` 全宽双栏**
5. 客户信息并入 **送货单维护**（删除独立 `#customerInfo`）

## 当前 UI 结构（勿改回左侧栏 unless 用户明确要求）

```
[顶栏] WKT | 订单管理▾ | 对账 | 送货单维护 | 成本分析 | AI
[内容] 全宽业务区（表格/OCR/表单）
[页脚] 模块标题 + 一行说明（#pageTitle / #pageDesc，app.js 切换子模块时更新）
```

## 关键文件

| 文件 | 作用 |
|------|------|
| `test_impl/web/templates/_order_sidebar.html` | 实为 **top-nav**（历史文件名未改） |
| `test_impl/web/templates/index.html` | 无 `page-header`；footer 在底部 |
| `test_impl/web/static/style.css` | `.top-nav*`、`.page-footer` |
| `test_impl/web/static/cost.css` | 成本页全宽 |
| `test_impl/web/static/app.js` | `SUBMODULES` 描述；`top-nav-head-link` 高亮 |
| `snapshots/ui-baseline-20260530/` | 无 Git 时的 UI 文件快照 |
| `scripts/restore-ui-baseline.ps1` | 从快照恢复 UI 六文件 |

## 本段对话曾尝试、用户否定的方案

- 左侧栏收窄 + 子菜单折叠（难用，已弃）
- 订单子菜单 **固定第二行**（用户要求改回下拉）

## 未完成 / 待用户决定

- Git 用户身份配置后可持续 `commit` + `push`
- SOP 第二节仍部分描述「左侧菜单」（CL-0103 起应改为顶栏）

## 验证

```powershell
cd P:\WKT
python -m unittest discover -s tests -p "test_*.py"
# 103 tests OK（2026-05-30）
```
