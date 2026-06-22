# WKT 项目 Agent Skills

## 已安装

| 来源 | 路径 | 说明 |
|------|------|------|
| [obra/superpowers](https://github.com/obra/superpowers) | 各子目录 `*/SKILL.md` | 头脑风暴、TDD、调试、计划执行等 |
| [karpathy-guidelines](https://github.com/swarmclawai/andrej-karpathy-skills) | `karpathy-guidelines/SKILL.md` | Karpathy 四条编码准则 |

项目规则：`.cursor/rules/karpathy-guidelines.mdc`、`wkt-agent-workflow.mdc`

## 更新 Superpowers

```powershell
cd P:\WKT
.\scripts\sync-superpowers-skills.ps1
```

重启 Cursor 或新开 Agent 会话以加载更新。

## 手动触发

在 Agent 聊天输入 `/brainstorming`、`/test-driven-development` 等（技能名与文件夹名一致）。
