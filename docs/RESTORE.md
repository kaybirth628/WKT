# 版本回退指南

## 1. 每次变更在哪里看

| 来源 | 内容 |
|------|------|
| **`docs/change/CHANGELOG.md`** | 业务变更 CL-XXXX（必读，含验证方式） |
| **`docs/VERSION.md`** | 里程碑版本号 |
| **`git log --oneline`** | 每次 Git 提交（可回退到任意 commit） |
| **`git tag -l`** | 重要快照标签（如 `ui-baseline-20260530`） |
| **`docs/handoff/SESSION-*.md`** | 长对话精简摘要，供新 Agent 读 |

## 2. 回退到某一 Git 版本

```powershell
cd P:\WKT

# 查看历史
git log --oneline -20
git tag -l

# 仅恢复 Web UI（不碰数据库）
git checkout ui-baseline-20260530 -- test_impl/web/

# 回退整个仓库到某 commit（会丢失未提交改动，慎用）
git stash push -m "backup before restore"
git checkout <commit-hash>
```

回退后：**重启「一键启动网页.bat」**，浏览器 **Ctrl+F5**。

## 3. 无 Git 标签时：用快照目录

```powershell
powershell -ExecutionPolicy Bypass -File scripts\restore-ui-baseline.ps1
```

快照路径：`snapshots/ui-baseline-20260530/`（仅 6 个 UI 核心文件）。

## 4. 发版建议

每次满意的一版：

```powershell
git add -A
git -c user.name="Your Name" -c user.email="you@example.com" commit -m "CL-XXXX: 简述"
git tag -a v0.x.x -m "说明"
```

勿提交：`data/wkt_orders.db`、`data/feishu_config.json`、`*secrets*`、`.db.bak*`。
