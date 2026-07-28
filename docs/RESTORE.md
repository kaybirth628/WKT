# 版本回退与发版指南

## 1. 每次变更在哪里看

| 来源 | 内容 |
|------|------|
| **`docs/change/CHANGELOG.md`** | 业务变更 **CL-XXXX**（几乎每次改动都登记） |
| **`docs/VERSION.md`** | 里程碑版本号 **v0.5.x**（大节点才升） |
| **`git log --oneline`** | 每次 Git 提交（可回退到任意 commit） |
| **`git tag -l`** | 里程碑标签（如 `v0.5.1`） |
| **`docs/handoff/SESSION-*.md`** | 长对话精简摘要，供新 Agent 读 |

### CL、版本号、Git 标签分别是什么

| 名字 | 比喻 | 频率 |
|------|------|------|
| **CL-0104** | 日记里的一页 | 几乎每次改代码 |
| **v0.5.2** | 书的章节标题 | 攒一批改动、要「定格一版」时 |
| **Git tag** | 给 GitHub 上某次提交贴书签，便于 `git checkout v0.5.2` 整版回退 | 与 v0.5.x 同时打，**不是每次推送都要** |

---

## 2. 小改 vs 大改（怎么区分）

**原则：** 日常只记 **CL**；只有「值得定格、以后要整版回退」时才升 **v0.5.x** 并打 tag。

### 算小改 —— 只写 CL，推送时里程碑版本留空

- 修 bug、改文案、调列宽/颜色、改 SOP 措辞  
- 单个页面小优化（筛选、按钮、提示）  
- 不改数据库结构、不改 API 字段含义  
- 用户**不用重新学**怎么用系统  
- CHANGELOG 等级多为 **C 优化** 或 **D 文档**

**例子：** `CL-0104: 修复对账筛选` → 双击 **「一键推送云端和 GitHub」** → 里程碑版本**直接回车**。

### 算大改 —— CL + 升 v0.5.x + 打 Git 标签

下面**任意一条**成立，建议升里程碑版本：

- **界面架构变了**（如左侧栏改顶部导航）  
- **新模块 / 删掉或合并模块**  
- **数据库、API、送货单快照**等持久化格式变了  
- **业务流程明显变化**（SOP 要大段重写）  
- 你心里认定：**「这一版给同事用 / 要定格 / 以后要整版回退」**  
- CHANGELOG 等级为 **B 重构** 或影响面很大的 **A 新增**

**例子：** `CL-0103` + **v0.5.1**（顶部导航 UI 基线）。

### 与 CHANGELOG 合规等级对照

| 等级 | 通常是否升 v0.5.x |
|------|-------------------|
| **C 优化 / D 文档** | 否 |
| **A 新增**（小功能） | 一般否 |
| **B 重构** | **经常是** |

**拿不准时：当小改处理（里程碑留空）。** 大改忘了打 tag 以后还可以补打。

### 版本号怎么递增

- 常规里程碑：`v0.5.1` → `v0.5.2`（第三位 +1，最常用）  
- 较大阶段：`v0.5.x` → `v0.6.0`（多个模块一起大改时）

---

## 3. 一键推送云端和 GitHub

项目根目录双击：**`一键推送云端和GitHub.bat`**

1. 提交并推送到 **GitHub**（不含本地订单库 `*.db`）  
2. 部署 **程序代码** 到云端（**不覆盖**云端生产 `data/` 业务数据）

脚本会依次询问：

1. **【变更记录】** — 已根据 `CHANGELOG.md` **顶部 CL 条目自动推荐**；**直接回车**即提交，无需手打 CL 编号  
2. **【里程碑版本】** — **直接回车跳过**（日常小改）；仅大版本发布时填 `v0.6.1`

或 PowerShell：

```powershell
cd P:\WKT
powershell -ExecutionPolicy Bypass -File scripts\push-cloud-and-github.ps1
# 仅 GitHub、不部署云端：
powershell -ExecutionPolicy Bypass -File scripts\push-cloud-and-github.ps1 -PushOnly
```

打新里程碑后，请同步更新 **`docs/VERSION.md`** 与 CHANGELOG「当前发布版本」。

**生产安全规范**：[`docs/change/PRODUCTION-SAFETY.md`](change/PRODUCTION-SAFETY.md)

---

## 4. 回退到某一 Git 版本

```powershell
cd P:\WKT

git log --oneline -20
git tag -l

# 整版回到某里程碑（示例）
git checkout v0.5.1 -- .

# 仅恢复 Web UI（不碰数据库）
git checkout ui-baseline-20260530 -- test_impl/web/

# 回到某次 commit（会丢失未提交改动，慎用）
git stash push -m "backup before restore"
git checkout <commit-hash>
```

回退后：**重启「一键启动网页.bat」**，浏览器 **Ctrl+F5**。

## 5. 无 Git 标签时：用快照目录

```powershell
powershell -ExecutionPolicy Bypass -File scripts\restore-ui-baseline.ps1
```

快照路径：`snapshots/ui-baseline-20260530/`（6 个 UI 核心文件）。

---

## 6. 云端与本地数据（测试阶段 · 云端=生产）

**原则：云端 `data/` 为正式生产数据，程序只上传代码，不上传本地库覆盖云端。**

| 脚本 | 作用 |
|------|------|
| **`一键启动网页.bat`** | 本地启动 Web 服务 |
| **`一键推送云端和GitHub.bat`** | GitHub + 云端 **代码**部署（含 `feishu_config.json`；**不碰**订单库/客商 JSON） |
| **`一键下载云端数据覆盖本地.bat`** | 云端 `data/` → 本地（本地先备份 `data.local.bak-*`） |

已删除（勿再使用）：全量同步云端、查询云端、恢复云端供应商、写入 SOP 测试数据、清库 `reset_order_db`、旧版单独 GitHub/同步 bat 及对应 `scripts/*.ps1`/`seed_*.py`。  
`sync-to-cloud.ps1` 的 `-FullData` / `-WithMasterData` 已在脚本层 **禁用**。

本地要与生产数据一致：用 **下载云端覆盖本地**，不要用本地库推云。

---

## 7. 勿提交到 GitHub 的文件

已由 `.gitignore` 排除，一般无需手动排除：

- `data/wkt_orders.db`（业务数据库）  
- `config/secrets.local.json`、`data/feishu_config.json`（密钥）  
- `*.db.bak*`（数据库备份）

仓库地址：https://github.com/kaybirth628/WKT
