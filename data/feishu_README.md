# 飞书通知配置

将订单录入、出货、修改、删除、Excel 导入等变动推送到飞书群。

## 1. 创建飞书机器人

1. 在飞书群 → **设置** → **群机器人** → **添加机器人** → **自定义机器人**
2. 复制 **Webhook 地址**（形如 `https://open.feishu.cn/open-apis/bot/v2/hook/...`）
3. 若启用了「签名校验」，记下 **签名密钥**

## 2. 填写配置

编辑 `data/feishu_config.json`：

```json
{
  "enabled": true,
  "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx",
  "sign_secret": "",
  "app_name": "WKT销售系统",
  "events": {
    "line_created": true,
    "line_updated": true,
    "line_deleted": true,
    "line_shipped": true,
    "import_completed": true
  }
}
```

也可用环境变量（优先级更高）：

- `FEISHU_WEBHOOK_URL` — Webhook 地址
- `FEISHU_SIGN_SECRET` — 签名密钥
- `FEISHU_ENABLED=1` — 强制启用

修改后 **重启网页服务**。

## 3. 测试

```bash
curl -X POST http://127.0.0.1:5000/api/feishu/test
```

或在浏览器开发者工具执行：

```javascript
fetch("/api/feishu/test", { method: "POST" });
```

## 4. 推送的事件

| 事件 | 说明 |
|------|------|
| `line_created` | 单条订单录入（含 OCR 逐条提交） |
| `line_updated` | 订单明细修改 |
| `line_deleted` | 订单删除 |
| `line_shipped` | 未结订单出货 |
| `import_completed` | Excel 批量导入（合并为一条摘要，不逐行刷屏） |

## 5. 查看状态

`GET /api/feishu/config` 或 `/api/health` 中的 `feishu` 字段。
