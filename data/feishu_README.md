# 飞书通知配置

将 **云端/本地** 业务操作与 **系统迭代部署** 推送到飞书群。

## 1. 创建飞书机器人

1. 在飞书群 → **设置** → **群机器人** → **添加机器人** → **自定义机器人**
2. 复制 **Webhook 地址**
3. 若启用了「签名校验」，记下 **签名密钥**

## 2. 填写配置

**云端**请编辑服务器上 `data/feishu_config.json`，或通过 **一键同步云端** 自动推送本地配置（默认同步行为，不覆盖订单/客商数据）。

```json
{
  "enabled": true,
  "webhook_urls": [
    "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx",
    "https://open.feishu.cn/open-apis/bot/v2/hook/yyyyyyyy"
  ],
  "sign_secret": "",
  "app_name": "WKT销售系统",
  "events": {
    "audit_action": true,
    "system_deploy": true
  }
}
```

也兼容旧版单地址字段 `webhook_url`；多条消息会 **同时推送到所有 Webhook**（去重后）。

环境变量：
- `FEISHU_WEBHOOK_URLS` — 逗号分隔多个地址（优先级高于配置文件）
- `FEISHU_WEBHOOK_URL` — 单个地址（兼容旧用法）

完整 `events` 列表见下文。未列出的类型默认 **开启**。

环境变量（优先级更高）：`FEISHU_WEBHOOK_URL`、`FEISHU_SIGN_SECRET`、`FEISHU_ENABLED=1`

修改后 **重启网页服务**。

## 3. 测试

```javascript
fetch("/api/feishu/test", { method: "POST" });
```

## 4. 推送类型

### 操作通知（`audit_action`）

用户登录/退出，以及所有已登记写操作，统一推送一条「操作通知」，包含：

- 操作人（姓名 + 用户名）
- 模块（订单 / 库存 / BOM / 客商 …）
- 摘要（如「录入订单行：客户 订单号」）
- IP

覆盖：订单录入/修改/删除/出货/导入、库存出入库、BOM、客商档案、送货单模板、用户管理等。

### 系统更新（`system_deploy`）

每次运行 **一键同步云端** 并成功部署后，服务器自动执行 `scripts/notify-feishu-deploy.py`，推送：

- 版本号（来自 `deploy-info/VERSION.md`）
- Build 号（来自 `app.py`）
- 最近若干条 CHANGELOG 摘要

### 其他事件（可选开关）

| 事件 | 说明 |
|------|------|
| `line_created` 等 | 旧版分事件通知（现由 `audit_action` 统一覆盖，可关） |
| `import_completed` | 同上 |
| `inventory_movement` | 同上 |

建议只保留 `audit_action` + `system_deploy` 为 `true`，避免重复。

## 5. 查看状态

`GET /api/feishu/config` 或 `/api/health` 中的 `feishu` 字段。
