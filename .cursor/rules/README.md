# WKT Cursor Project Rules

本目录下的 `.mdc` 文件会在 **打开 WKT 仓库** 时由 Cursor **自动加载**（无需在 Settings 里手抄）。

## 要求

- 强制规则必须带 frontmatter：`alwaysApply: true`
- 改规则后运行：`scripts/sync-cursor-rules.ps1`
- 然后 **Reload Window** 或新开 Agent 聊天

## 文件

| 文件 | 说明 |
|------|------|
| `00-wkt-master.mdc` | 总入口 |
| `wkt-read-before-edit.mdc` | 改代码前 Read 清单 |
| `wkt-ui-design.mdc` | UI 规则 |
| `wkt-agent-workflow.mdc` | Agent 工作流 |
| `wkt-change-governance.mdc` | CL/BF/SOP |
| `wkt-production-safety.mdc` | 生产安全 |
| `karpathy-guidelines.mdc` | 编码准则 |

权威文档：`docs/design/GLOBAL-RULES-INDEX.md`
