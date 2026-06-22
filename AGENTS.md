# WKT 销售管理系统 · AI 协作指南

> 供 Cursor Agent 及后续会话阅读。**每次动手改代码前，先读本文件 + `docs/change/CHANGELOG.md` 最新条目 + `docs/VERSION.md`。**

## 项目概览

- **用途**：威可特（WKT）销售订单录入、出货、送货单、成本分析（演示/内网）。
- **运行入口**：根目录 `一键启动网页.bat` → Flask `http://127.0.0.1:5000`
- **代码根**：`test_impl/`（**禁止**直接改 `src/`）
- **数据**：SQLite `data/wkt_orders.db`；配置与模板在 `data/`
- **当前版本**：**v0.5.0**（见 `docs/VERSION.md`）

## 目录速查

| 区域 | 路径 |
|------|------|
| Flask 路由 | `test_impl/web/app.py` |
| 前端 | `test_impl/web/static/app.js`、`delivery-note-admin.js`、`style.css` |
| 订单行 CRUD / 出货 | `test_impl/order_management/order_entry/` |
| OCR 识别 | `test_impl/order_management/order_intake/` |
| 原件高清预览 | `test_impl/order_management/order_intake/source_preview.py` |
| 送货单 | `test_impl/order_management/delivery_note/` |
| 飞书通知 | `test_impl/integrations/feishu.py`、`wkt_events.py` |
| 单元测试 | `tests/` |
| 变更日志 | `docs/change/CHANGELOG.md` |
| 操作 SOP | `docs/SOP/系统操作SOP.md` |
| 版本记录 | `docs/VERSION.md` |
| **数据结构** | `docs/architecture/data-model.md` |
| 代码地图（CodeGraph） | `.codegraph/` 索引；CLI `codegraph`；MCP 见 `.cursor/mcp.json` |
| Agent Skills | `.cursor/skills/`（Superpowers + karpathy-guidelines） |

## Agent 技能与工作流

**优先级**：用户指令 > Superpowers 技能 > Karpathy 准则 > 本文件默认约定。

| 技能包 | 路径 | 何时用 |
|--------|------|--------|
| **Superpowers**（[obra/superpowers](https://github.com/obra/superpowers)） | `.cursor/skills/*/SKILL.md` | 先读 `using-superpowers`；新功能→`brainstorming`/`writing-plans`；Bug→`systematic-debugging`；编码→`test-driven-development` |
| **Karpathy** | `.cursor/skills/karpathy-guidelines/` + `.cursor/rules/karpathy-guidelines.mdc` | 写码/重构：先想清楚、最小改动、可验证完成标准 |
| **项目规则** | `.cursor/rules/wkt-agent-workflow.mdc` | 数据结构图同步、合规清单 |

更新 Superpowers：`scripts/sync-superpowers-skills.ps1` 后重启 Cursor。

## CodeGraph（代码地图）

本项目已配置 [CodeGraph](https://github.com/colbymchenry/codegraph)（v1.0.1）：本地索引符号、调用关系、路由等，供 Agent 与命令行查询。

- **重建索引**：`codegraph sync`（大改后）或 `codegraph index`
- **结构树**：`codegraph files --filter test_impl --format tree`
- **搜符号**：`codegraph query line_service`
- **看调用链**：`codegraph explore ship` / `codegraph node loadLines`
- **状态**：`codegraph status`
- Cursor 需在 **Settings → Tools & MCP** 启用 `codegraph` 并**重启 Cursor**

## 架构要点

1. **订单行**：一料号一行（15 列 RMB 口径），`line_service.py` + `line_store.py`（SQLite）。
2. **出货**：`shipment_events` 表；未结列表可部分出货；POST `/api/lines/{id}/ship`。
3. **送货单**：全客户统一 **WKT 标准模板**（`wkt_standard`）；客户差异仅在收货地址/联系人/单号前缀（`data/delivery_templates/customer_delivery.json`）。
4. **出货确认**：出货前 iframe 弹窗 `/delivery-note/ship-confirm`，可编辑后确认；快照写入 `shipment_events.delivery_note_json`。
5. **飞书**：Webhook 推送录入/修改/删除/出货/导入；配置 `data/feishu_config.json`（**勿提交密钥**）。
6. **OCR 预览**：上方原件（PDF 200 DPI PNG）、下方识别表；API `/api/lines/recognize/<job_id>/preview/<page>`。
7. **健康检查**：GET `/api/health` 的 `build` 字段用于确认是否在跑新进程（旧进程会导致 404/HTML 假 JSON）。

## 每次功能变更必须完成（合规清单）

未全部完成视为**不合规改动**（与 CHANGELOG 头部规则一致）：

1. **登记 CHANGELOG**（`docs/change/CHANGELOG.md`）
   - 新编号 **CL-XXXX**（递增，不复用）
   - 字段：日期、类型、合规等级、涉及模块、变更内容、验证、SOP 是否同步
2. **改库表 / 持久化字段 / API 字段 / 送货单快照结构 → 同步 `docs/architecture/data-model.md`**（ER 图、字段表、示例 JSON）
3. **用户可见流程变更 → 同步 SOP**（`docs/SOP/系统操作SOP.md`）
3. **里程碑发布 → 更新 VERSION**（`docs/VERSION.md`）并改 CHANGELOG「当前发布版本」
4. **跑测试**：`python -m unittest discover -s tests -p "test_*.py"` 或 `scripts/verify.ps1`
5. **更新 `/api/health` 的 `build`**（`test_impl/web/app.py`）
6. **静态资源 cache bust**：`index.html` 等处 `app.js?v=` / `style.css?v=` 日期后缀
7. **提醒用户**：改后端后需重启 `一键启动网页.bat` + 浏览器 Ctrl+F5

## 编码约定

- **最小 diff**：只改任务相关文件；匹配现有命名与风格。
- **不 over-engineer**：不抽一层只调用一次的 helper；不写不可能触发的防御代码。
- **注释**：仅解释非 obvious 的业务/技术点。
- **测试**：仅在有真实行为覆盖时新增；不堆 trivial assert。
- **不主动 git commit/push**，除非用户明确要求。

## 密钥与敏感文件

- `data/feishu_config.json`、DeepSeek/百度 OCR 等密钥：**不要**写入 CHANGELOG 正文、不要 commit 到公开仓库。
- 文档中引用 webhook 时用「已配置」描述即可。

## 常见运维问题

| 现象 | 处理 |
|------|------|
| API 返回 HTML 或 404 | 旧 Flask 进程；重启 bat，查 `/api/health` 的 `build` |
| 前端改了不生效 | Ctrl+F5；确认 `?v=` 已 bump |
| 数据库路径 | `line_service.db_path`，默认 `data/wkt_orders.db` |

## 会话连贯性协议

新会话或模型切换时，Agent 应：

1. 读 `AGENTS.md`（本文件）+ CHANGELOG 顶部 5 条 + VERSION 当前版；涉及数据时读 `docs/architecture/data-model.md`
2. 任务开始前检查 Superpowers / Karpathy 是否适用（见 `using-superpowers`）
2. 用户描述的功能若已在 CHANGELOG/SOP 出现，**在已有实现上扩展**，避免重复造轮子
3. 完成工作后，在回复中简要列出：CL 编号、是否更 SOP、测试数、是否需要重启服务
4. 大功能拆分时，每条 CL 对应一个可验证的用户故事

## 当前里程碑 v0.4.0 能力（CL-0051 ~ CL-0056）

- SQLite 持久化 + 出货事件 + 未结出货
- WKT 统一送货单 + 送货单维护页
- 出货前送货单确认弹窗与快照
- 飞书 Webhook 变动通知
- OCR 原件高清预览（200 DPI）
- 本指南与 VERSION/CHANGELOG 治理同步
