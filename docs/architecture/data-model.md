# WKT 销售管理系统 · 数据结构说明

> 描述业务数据如何存储、关联与流转。  
> 代码对照：`test_impl/order_management/order_entry/line_store.py`（SQLite 建表）、`line_models.py`、`shipment_models.py`。  
> 最后更新：2026-07-20 · CL-0114

---

## 1. 数据存放总览

| 类型 | 路径 | 说明 |
|------|------|------|
| **订单主库** | `data/wkt_orders.db` | SQLite，核心业务数据 |
| **JSON 配置** | `data/delivery_templates/`、`data/feishu_config.json` | 送货单抬头、客户收货信息、飞书 Webhook |
| **订单原件** | `orders/{客户名}/{接单日期}_{订单号}.ext` | OCR 识别后归档的 PDF/图片 |
| **上传临时** | `test_impl/web/uploads/` | 上传中间文件，可清理 |
| **OCR 任务** | 内存（`app.py`） | `_recognize_jobs`、`_recognize_previews`，重启清空 |
| **会话密钥** | `data/auth_secret.txt` | Flask Session 签名（自动生成，勿提交 Git） |
| **成本/BOM 主数据** | `data/wkt_orders.db` → `cost_records` | SQLite，料号、工序、成本；**订单料号权威来源** |
| **即时报价试算** | 不入库 | 浏览器内 `CostQuote`（`/cost` 页，非 BOM 主数据） |

```mermaid
flowchart TB
  subgraph persist["持久化"]
    DB["SQLite data/wkt_orders.db"]
    JSON["JSON 配置 data/"]
    ORD["订单原件 orders/"]
  end

  subgraph runtime["运行时 / 临时"]
    OCR["OCR 任务内存"]
    UP["uploads/"]
  end

  subgraph nopersist["仅页面计算"]
    COST["即时报价 CostQuote /cost"]
  end

  BOM["cost_records BOM主数据"] --> DB

  UI["网页 / API"] --> DB
  UI --> JSON
  OCR --> ORD
  OCR --> OCR
```

---

## 2. SQLite 实体关系

库文件默认路径：`P:\WKT\data\wkt_orders.db`（可通过环境变量 `WKT_DB_PATH` 覆盖）。

```mermaid
erDiagram
  customers ||--o{ order_lines : "名称引用(非FK)"
  cost_records ||--o{ order_lines : "customer_part_no 逻辑引用"
  parts ||--o{ order_lines : "品名引用(非FK)"
  order_lines ||--o{ shipment_events : "line_id FK"
  users ||--o{ audit_log : "user_id FK"

  users {
    int id PK
    text username UK "登录名"
    text display_name "显示姓名"
    text password_hash "密码哈希"
    text role "admin|user"
    int is_active
    int must_change_password
    text created_at
    text last_login_at
  }

  audit_log {
    int id PK
    int user_id FK
    text username
    text display_name
    text action "如 line.create"
    text module "orders|inventory|..."
    text summary "可读摘要"
    text detail_json
    text ip_address
    text created_at
  }

  cost_records {
    int id PK
    text customer_name "绑定客户"
    text product_part_no "客户料号 UK逻辑"
    text product_name "品名"
    text unit_weight_g "单重"
    text material "材质"
    text process_prices_json "工序单价"
  }

  customers {
    int id PK
    text name UK "客户名"
  }

  parts {
    int id PK
    text product_spec UK "品名规格"
    text customer_part_no "默认客户料号"
  }

  order_lines {
    int id PK
    text customer
    text order_date
    text delivery_date
    text order_no
    text product_spec
    text customer_part_no
    text unit_weight_g
    text material
    text po_qty
    text shipped_qty
    text unit
    text tax_rate
    text rmb_tax_incl_price
    text payment_terms
    text closure_type
    int is_demo
    text created_at
    text updated_at
  }

  shipment_events {
    int id PK
    int line_id FK
    text ship_qty
    text source
    text shipped_at
    text delivery_note_json
  }
```

**说明**

- `customers`、`parts` 为录入辅助主数据；`order_lines` 存的是文本副本，**无外键**约束。
- `shipment_events.line_id` → `order_lines.id` 为唯一正式外键。
- 数值在 SQLite 中多以 **TEXT** 存储（如 `po_qty`），应用层用 `Decimal` 解析。

---

## 3. 业务唯一性

逻辑唯一键（应用层校验，非数据库 UNIQUE 索引）：

**客户 + 订单号 + 品名规格**

重复新建返回 HTTP 409，响应含 `duplicate_id`。实现见 `line_store.find_duplicate_line()`。

---

## 4. 表 `order_lines`（一料号一行）

对应网页列表一行、附件 2 的 15 列业务字段 + 系统字段。

| 字段 | 类型/存储 | 说明 |
|------|-----------|------|
| `id` | INTEGER PK | 自增主键 |
| `customer` | TEXT | 客户 |
| `order_date` | TEXT | 接单日期 |
| `delivery_date` | TEXT | 客户交期 |
| `order_no` | TEXT | 订单号 |
| `product_spec` | TEXT | 品名规格 |
| `customer_part_no` | TEXT | 客户料号 |
| `unit_weight_g` | TEXT | 单重(g)；可为数字或备注如「外购件」 |
| `material` | TEXT | 材质 |
| `po_qty` | TEXT → Decimal | PO 数量 |
| `shipped_qty` | TEXT → Decimal | 已出货，默认 0 |
| `unit` | TEXT | 单位 |
| `tax_rate` | TEXT → Decimal | 税率 0~1（如 0.13） |
| `rmb_tax_incl_price` | TEXT → Decimal | 人民币含税单价 |
| `payment_terms` | TEXT | 账期 |
| `closure_type` | TEXT | 结案方式：空=未强制结案；`forced`=强制结案（不记出货、不纳入对账） |
| `is_demo` | INTEGER | 1=测试数据（UI **测** 徽标）；库存演示 API / `test_impl/demo/sop_seed.py`（测试） |
| `created_at` | TEXT ISO | 系统录入时间 |
| `updated_at` | TEXT ISO | 最后更新时间 |

### 计算字段（不存表）

| 字段 | 公式 | 精度 |
|------|------|------|
| `open_qty` 未结 | `po_qty − shipped_qty` | 数量 1 位小数 |
| `amount` 含税金额 | `po_qty × rmb_tax_incl_price` | 金额 2 位小数 |

Python 模型：`OrderLine`（`line_models.py`）。

### API JSON 示例（`GET /api/lines`）

```json
{
  "id": 1,
  "customer": "怡利",
  "order_date": "2026-05-01",
  "delivery_date": "2026-06-01",
  "order_no": "PO-001",
  "product_spec": "某某散热器",
  "customer_part_no": "YL-123",
  "unit_weight_g": "12.5",
  "material": "ADC12",
  "po_qty": "1000",
  "shipped_qty": "200",
  "open_qty": "800",
  "unit": "PCS",
  "tax_rate": "0.13",
  "rmb_tax_incl_price": "3.5000",
  "amount": "3500.00",
  "payment_terms": "月结30天",
  "created_at": "2026-05-30T08:00:00+00:00",
  "updated_at": "2026-05-30T08:00:00+00:00"
}
```

结案订单（`view=closed`）在上述字段基础上增加：

```json
{
  "last_shipped_at": "2026-05-30T14:30:00+00:00",
  "last_delivery_doc_no": "WKT202605300003"
}
```

无出货登记记录时两字段为空字符串。

### 列表视图与数据关系

| 子模块 | 数据条件 |
|--------|----------|
| 订单明细 | 全部 `order_lines` |
| 未结订单 | `open_qty > 0` 且非强制结案；可出货、合并出货或 **强制结案**（`POST /api/lines/{id}/force-close`） |
| 正常结案订单 | `open_qty ≤ 0` 且 `closure_type ≠ forced`；按最后一次出货时间降序；附带 `last_shipped_at`、`last_delivery_doc_no` |
| 强制结案订单 | `closure_type = forced`；不记出货、不纳入对账；按 `updated_at` 降序 |
| 出货明细 | 仅 `shipment_events`（不含录入时直接填的「已出货」） |

---

## 5. 表 `shipment_events`（出货事件）

每次「未结 → 出货」登记产生一条记录；历史 Excel 导入出货（`source=import`）亦在此表。

| 字段 | 说明 |
|------|------|
| `id` | 主键；送货单打印 URL 使用此 ID |
| `line_id` | 关联 `order_lines.id` |
| `ship_qty` | 本次出货数量 |
| `source` | `open_ship`（未结出货）或 `import`（历史导入） |
| `shipped_at` | 出货时间（ISO 文本） |
| `delivery_note_json` | 确认出货时送货单完整 JSON 快照 |

出货明细 API 会 JOIN `order_lines`，并附带快照时刻的：

- `shipped_qty_after` — 该行累计已出货
- `open_qty_after` — 出货后未结（`po_qty − shipped_qty_after`）

Python 模型：`ShipmentEvent`（`shipment_models.py`）。

### API JSON 示例（`GET /api/shipment-events`）

```json
{
  "id": 12,
  "line_id": 1,
  "ship_qty": "100",
  "source": "open_ship",
  "source_label": "未结出货",
  "shipped_at": "2026-05-30T10:00:00+00:00",
  "customer": "怡利",
  "order_date": "2026-05-01",
  "order_no": "PO-001",
  "product_spec": "某某散热器",
  "customer_part_no": "YL-123",
  "po_qty": "1000",
  "shipped_qty_after": "300",
  "open_qty_after": "700"
}
```

---

## 6. 送货单快照 `delivery_note_json`

结构对应 `WktDeliveryDocument`（`delivery_note/wkt_document.py`），确认出货时写入 `shipment_events.delivery_note_json`。

```
WktDeliveryDocument
├── title_company          抬头公司名
├── doc_no                 送货单号（格式见下）
├── ship_date_cn           出货日期（中文格式）
├── receiver_company       收货公司
├── receiver_address       收货地点
├── receiver_contact       收货联系人
├── supplier_name          供应商名称
├── supplier_address       供应商地址
├── supplier_phone         供应商电话
├── lines[]                明细行 WktDeliveryLine
│   ├── order_no           订单号
│   ├── customer_part_no   客户料号
│   ├── product_name       品名
│   ├── spec               规格
│   ├── unit               单位
│   ├── qty                数量
│   ├── batch_no           批号
│   ├── box_count          箱数
│   └── remark             备注
├── total_qty              合计数量
├── footer_note            页脚说明
├── deliverer              送货人
├── warehouse_manager      仓管
├── receiver_sign          收货签收
└── is_sample              是否样品
```

抬头默认值来自 `data/delivery_templates/wkt_company.json`；客户收货信息来自 `customer_delivery.json`。

**送货单号 `doc_no` 规则**（`wkt_document._gen_doc_no`）：

- 格式：`{前缀}{YYYYMMDD}{当月序号4位}`，如 `WKT202605300001`。
- 前缀：客户维护的 `doc_no_prefix`（如 `ABL`），否则全公司默认 `WKT`。
- 末 4 位为**自然月**内出货序号：每月 1 日（本地时区）归零后，按 `shipment_events` 登记顺序从 `0001` 递增。
- 草稿预览未确认前末位为 `01`；确认出货后写入正式序号。

---

## 7. 主数据表

### `cost_records`（BOM · 料号主数据）

| 字段 | 说明 |
|------|------|
| `id` | PK |
| `customer_name` | 绑定客户（同一 `product_part_no` 仅允许一个客户） |
| `product_part_no` | **客户料号**（BOM 权威键） |
| `product_name` | 品名 |
| `mold_no` / `cavity` / `unit_weight_g` / `material` / `machine_tonnage` | 模具与物性 |
| `material_unit_price` / `process_prices_json` | 原材与工序单价；JSON 每道工序 `{ price, supplier, suppliers[] }`（`supplier` 为主供应商/兼容旧数据；`suppliers` 为可选外发供应商列表，CL-0238）；可含 **`__order__`** 数组保存自定义工艺顺序（CL-0137） |
| `material_cost` / `process_total` / `unit_cost` / `quote_price` | 计算结果 |
| `is_demo` | 1=测试数据（列表显示 **测**）；0=正式（CL-0133） |
| `created_at` / `updated_at` | 时间戳 |

**数据流（订单 ← BOM）**

```mermaid
flowchart LR
  BOM["BOM录入 cost_records"]
  ORD["订单录入 order_lines"]
  API["GET /api/bom/lookup"]
  BOM --> API
  API -->|"回填品名/单重/材质"| ORD
  ORD -->|"保存时 require_for_order"| BOM
```

- 订单保存/导入时若带 `customer_part_no`，`BomService.require_for_order()` 校验 BOM 存在且客户一致。
- 未建档 → `BomNotFoundError`，提示先到 **BOM录入**。
- 客户名匹配支持 profile 简称（如「怡利」↔ `customer_profiles.json` 全称）。

### `customers`

| 字段 | 说明 |
|------|------|
| `id` | PK |
| `name` | 客户名，UNIQUE |

录入 / OCR 时自动 `INSERT OR IGNORE`；用于手工录入客户下拉。

### `parts`

| 字段 | 说明 |
|------|------|
| `id` | PK |
| `product_spec` | 品名规格，UNIQUE |
| `customer_part_no` | 对应客户料号 |

**说明**：`parts` 表仍保留品名下拉；**客户料号以 BOM（`cost_records`）为准**。选品名时 `GET /api/master/lookup` 优先查 BOM，再回退 `parts`。

### `users` / 用户管理 API（CL-0171）

| 字段 | 说明 |
|------|------|
| `id` | PK |
| `username` | 登录名，UNIQUE |
| `display_name` | 显示姓名 |
| `role` | `admin` / `user` |
| `is_active` | 1=启用，0=禁用 |
| `must_change_password` | 首次登录须改密 |
| `last_login_at` | 上次登录时间 |

| 接口 | 说明 |
|------|------|
| `GET /api/users` | 用户列表（仅管理员） |
| `POST /api/users` | 创建用户 |
| `PUT /api/users/{id}` | 编辑姓名、角色 |
| `DELETE /api/users/{id}` | 删除用户（不可删 `admin`、当前登录账号；至少保留一名管理员） |
| `POST /api/users/{id}/reset-password` | 重置密码 |
| `POST /api/users/{id}/active` | 启用/禁用 |

页面：`/admin/users`。

| `POST /api/cost/bom-import/parse` | 上传 BOM 表单 Excel，解析预览（每 sheet 一料号） |
| `POST /api/cost/bom-import/commit` | 批量写入 BOM（工序单价默认 0） |

页面：`/bom/entry`（BOM 录入页顶部「BOM 表单批量导入」）。

### `inventory_balances` / `inventory_movements`（库存 · CL-0114）

| 表 | 说明 |
|----|------|
| `inventory_balances` | 余额：料号 × 工序 × 状态（`inhouse` / `outsource` / `finished`）× 供应商 |
| `inventory_movements` | 流水：`inbound` 入库 / `outbound` 出库（历史 `complete`/`outsource_*`/`ship_finished` 展示映射为入库/出库） |
| `production_replenish_orders` | 生产补产单（CL-0118，UI 已收起） |
| `inventory_part_tags` | 料号数据标注（CL-0124）：`product_part_no` PK、`is_demo`（1=测 / 0=实）、`updated_at` |

统一模型（CL-0163）：**入库** = 首道+场内 / 非首道在途→场内 / 末道→成品；**出库** = 上道场内→下道在途 / 成品出库。末道入库写入 `process_code=FIN` 成品仓。页面：`/inventory`、`/inventory/entry`。展示文案「在途」对应库内状态 `outsource`。

| `POST /api/inventory/inbound` | 入库；`process_code`、可选 `supplier_name`（外发回货） |
| `POST /api/inventory/outbound` | 出库；`from_process_code`、`to_process_code`（成品出库时 from=`FIN`、to 空） |

| `GET /api/inventory/board` | 库存总览看板；可选 `product_part_no`、`customer_name`（客户模糊匹配）；每项含 `product_part_no`、`product_name`、`customer_name`、`finished_qty`、`stages[]`、`data_tag` |
| `GET /api/cost/customers` | BOM 客户名称联想；`q` 模糊匹配，返回 `{ items: string[] }` |

进出单号（CL-0163）：未填时自动 `RK` 入库 / `CK` 出库 / `TZ` 校正 -YYYYMMDD-序号；`inventory_movements.doc_no`。API  enriched 字段含 `route_display`（如 `01 压铸 → 02 去毛边`）。

订单出货（`OrderLineService.ship_line`，已注入库存服务）自动调用 `ship_finished` 扣成品仓；不足则拒绝。

### 排产对照 / 补产单 API（CL-0115 / CL-0118）

| 接口 | 说明 |
|------|------|
| `GET /api/inventory/planning?customer=&q=` | 未结订单行 × 成品/半成品缺口；**一行一条** |
| `POST /api/inventory/planning/seed-demo` | 演示：PLAN-A/B/C 需求各 1000，可用库存约 500/600/700 |
| `GET /api/inventory/replenish` | 补产单列表 |
| `POST /api/inventory/replenish` | 生成补产单（可绑 `sales_order_no` / `line_id`） |
| `POST /api/inventory/seed-demo` | 单料号流水演示 |
| `POST /api/inventory/seed-board-demo` | 约 10 料号 BOM+各工序在途/成品（总览看板演示） |
| `GET /api/inventory/movements` | 流水；可选 `product_part_no`、`customer_name`（模糊）、`on_date`；每项含 `customer_name`、`product_name`（BOM）、`action_label`、`editable` 等 |
| `PUT /api/inventory/movements/{id}` | 修改手工出入库流水数量/备注（同步回滚库存；订单出货流水不可改，CL-0152） |

| `GET /api/reconciliation/due-outlook` | 应收到期：自本月起重 **6** 个收款月按客户汇总（CL-0129） |
| `GET /api/payable/due-outlook` | 应付到期：自本月起重 **6** 个付款月按供应商汇总（CL-0129） |
| `GET /api/payable/supplier-months` | 应付汇总：供应商×结算月 |
| `GET /api/payable/lines` | 应付明细（`payment_month` / `receive_from` / `receive_to`） |

应付只读聚合：`inventory_movements`（`outsource_receive` 或 `inbound` 且外发在途回货）+ BOM 工序价 + `supplier_profiles`（账期/对账周期）。无新增 SQLite 表（CL-0127）。

---

## 8. JSON 配置文件

| 文件 | 用途 |
|------|------|
| `data/delivery_templates/wkt_company.json` | 威可特供应商信息、`doc_no_prefix`（如 WKT） |
| `data/delivery_templates/customer_delivery.json` | 按客户：收货地址、联系人、单号前缀 |
| `data/delivery_templates/mapping.json` | 客户名 → 旧 Excel 模板文件名（遗留） |
| `data/feishu_config.json` | 飞书 Webhook（**勿提交 Git**）；支持 `webhook_urls` 多群推送 |

`customer_delivery.json` 示例：

```json
{
  "怡利": {
    "receiver_company": "",
    "receiver_address": "江苏省苏州市吴江经济开发区锦湖西路167号",
    "receiver_contact": "",
    "doc_no_prefix": ""
  }
}
```

---

## 9. 订单原件归档

路径规则（`order_archive.py`）：

```
orders/
└── {客户名}/
    └── {接单日期}_{订单号}.pdf
```

- 客户名、日期、订单号来自 OCR 识别结果第一行。
- 非法路径字符替换为 `_`；重名文件自动加 `_2`、`_3` …
- 归档失败不阻断 OCR 识别流程。

---

## 10. 不入库 / 临时数据

| 数据 | 位置 | 说明 |
|------|------|------|
| OCR 识别任务 | `app.py` `_recognize_jobs` | 进度、结果；重启丢失 |
| PDF 预览页 PNG | `_recognize_previews` | 200 DPI 渲染缓存；重启丢失 |
| 成本报价 | `cost_analysis/models.py` `CostQuote` | 原材 + 工艺单价，仅前端会话 |
| Excel 导入预览 | 前端 `excelImportPreview` | 解析后待确认，未提交前不入库 |

---

## 11. 业务流程（数据流）

```mermaid
flowchart LR
  A["手工录入 / OCR / Excel"] --> B["order_lines"]
  B --> C{"未结 > 0?"}
  C -->|是| D["未结订单"]
  C -->|否| E["结案订单"]
  D --> F["出货确认 + 送货单编辑"]
  F --> G["shipment_events"]
  F --> H["更新 order_lines.shipped_qty"]
  G --> I["delivery_note_json"]
  G --> J["出货明细"]
  B --> K["订单明细"]
```

**出货时同步更新**

1. `order_lines.shipped_qty` += 本次数量  
2. 插入 `shipment_events`（含 `delivery_note_json`）  
3. 若未结变为 0，该行从未结列表消失，进入结案列表  

---

## 12. 小数与展示口径

| 项目 | 存储/计算精度 | 说明 |
|------|---------------|------|
| 数量 `po_qty`、`shipped_qty` | 1 位小数 | `round_qty` |
| 单重 | 2 位或原文 | 允许非数字备注 |
| 含税单价 | 4 位小数 | `round_price` |
| 金额 | 2 位小数 | `round_amount` |
| 税率 | 0~1 | 录入可写 `13%`，归一化为 0.13 |

详见 `docs/change/money-format-v1.md`。

---

## 13. 维护与排查

| 操作 | 命令 / 路径 |
|------|-------------|
| 查看库路径 | `GET /api/health` → `db_path` |
| 本地对齐云端生产 data | 根目录 **`一键下载云端数据覆盖本地.bat`** |
| 表结构源码 | `line_store.py` → `_SCHEMA`、`_migrate_schema` |
| 代码符号索引 | CodeGraph：`codegraph query OrderLine` |

### 文档同步（强制）

凡修改 **SQLite 表**、**持久化字段**、**API 返回字段**、**送货单 `delivery_note_json` 结构** 时，**同一变更**内必须更新本文档（ER 图、字段表、JSON 示例、数据流图），并登记 CHANGELOG。  
纯 UI / 不改结构的逻辑：无需改本文档。  
Agent 规则见 `.cursor/rules/wkt-agent-workflow.mdc` 与 `AGENTS.md` 合规清单。
