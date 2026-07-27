# 对账 · 应收 / 应付 · 设计说明

> 日期：2026-07-23 · 状态：已确认 · 关联计划：`docs/superpowers/plans/2026-07-23-ar-ap-reconciliation.md`

## 背景

现有「对账」子模块基于 **出货明细** 计算客户应收（汇总 → 明细钻取）。业务需要拆成：

- **应收**：与客户出货绑定（保留现有逻辑）
- **应付**：与外发工艺 **供应商** 绑定，按 **回货入库** 结算，结算区间以 **收货日期** 为准

## 已确认决策

| 项 | 决策 |
|----|------|
| 导航 | 顶栏 **对账 ▾** → **应收** / **应付**（方案 A） |
| 应收 | 继续绑定 `shipment_events` + 订单行；行为不变 |
| 应付数据源 | `inventory_movements` 且 `action_type = outsource_receive` |
| 应付金额 | 回货数量 × **当前 BOM** 该外发工序单价 |
| 应付展示 | 供应商×结算月 **汇总** + **明细**；明细支持收货日期起止 |
| 结算月份 | 按供应商档案 `reconciliation_period`（复用 `period.py`） |
| 应付日期 | 按供应商档案 `payment_terms` + 回货日推算 |
| BOM 单价 | 查询时读 **当前 BOM**，不回溯历史版本 |

## 架构

在 `test_impl/order_management/reconciliation/` 下新增应付能力（方案 A）：

- `ReconciliationService` — 应收（现有，仅改对外命名/导航）
- `PayableService` — 应付（新建）
- 共享 `period.py`（结算月份）、扩展 `payment_schedule.py`（解析供应商账期）

依赖只读：

- `inventory_movements`（回货流水）
- `cost_records` / BOM 工序价（`CostRecordService` 或 store 查询）
- `supplier_profiles.json`（`payment_terms`、`reconciliation_period`）

不新增 SQLite 表（一期只读聚合）。

## 导航与路由

```
顶栏：对账 ▾
  ├ 应收  → /#reconcile   （hash submodule reconcile，标题「应收」）
  └ 应付  → /#payable     （hash submodule payable，新子模块）
```

修改 `_order_sidebar.html`：对账改为下拉，与「订单」「库存」一致。

## 应收（变更范围）

- 子模块 key 仍为 `reconcile`（兼容现有链接）
- 页面标题、下拉文案、SOP 统一为 **应收**
- API 路径不变：`/api/reconciliation/*`

## 应付 · 明细行

每条 **回货入库** 流水生成一行（可合并）。

| 字段 | 来源 |
|------|------|
| `id` | `inventory_movements.id` |
| `received_at` | `created_at`（转本地日期时间展示） |
| `receive_month` | `YYYY-MM`（回货日自然月，筛选用） |
| `supplier` | `from_supplier`（回货扣在途时的供应商） |
| `product_part_no` | 料号 |
| `process_code` | 工序代码 |
| `process_name` | BOM / `PROCESS_BY_CODE` |
| `qty` | 回货数量 |
| `unit_price` | BOM 该料号该工序单价；缺失则为空 |
| `amount` | `qty × unit_price`；缺价则空并标记 |
| `doc_no` | RK-… 回货单号 |
| `settlement_month` | 回货日 + 供应商 `reconciliation_period` |
| `payable_date` | 回货日 + 解析后的 `payment_terms` |
| `payment_month` | `payable_date` 所在月 `YYYY-MM` |
| `payment_terms` | 供应商档案原文 |
| `price_missing` | bool，BOM 无该工序价 |

**合并键**（与应收 `_merge_lines` 对称）：  
供应商 + 收货时间 + 料号 + 工序 + 单价 + 回货单号 → 合并数量与金额。

**缺 BOM**：行仍展示，`amount` 为空，汇总可计「待补 BOM」行数；不参与金额合计或单独小计（实现时明细标红，汇总金额只计有单价行）。

## 应付 · 汇总

- 维度：**供应商 × 结算月份**（`settlement_month`）
- 列：行数、回货总量、应付金额、操作「查看明细」
- 排序：应付金额大的供应商优先（对齐应收）
- 每组末尾 **【小计】**（可选，与应收一致）

筛选：

- 汇总页：**结算月份**、**付款月份**（下拉，来自 `list_payment_months`）
- 明细页 / 明细模式：**收货日期起止**（`receive_from` / `receive_to`，含起止日）

## 账期计算（应付）

扩展 `payment_schedule.py`：

1. **`parse_supplier_payment_terms(text) -> { term_days, is_cash }`**
   - 支持：`90天`、`150天`、`15天`、`120天`、`现结` 等
   - 无法解析：fallback 全局 `reconciliation_config.term_days`（默认 90）

2. **`compute_payable_date(receive_date, payment_terms, *, payment_day=25)`**
   - **现结**：应付日 = 回货日
   - **N 天**：应付日 = 回货日 + N 天，再对齐到 **最近 upcoming 的 payment_day**（若回货日+N 已过当月 payment_day，顺延下月 payment_day）
   - 简化版（与应收不同）：起算点为 **回货日**，不是「回货月月末」

3. **`payment_due_month_label(payable_date)`** — 已有，复用

结算月份：  
`reconciliation_period_for_ship_date(receive_local_date, supplier.reconciliation_period)` — 复用 `period.py`，参数名虽为 ship_date，语义为事件本地日。

## API

| 方法 | 路径 | 参数 | 返回 |
|------|------|------|------|
| GET | `/api/payable/config` | — | 说明、周期选项（复用 PERIOD_OPTIONS） |
| GET | `/api/payable/payment-months` | — | 付款月份列表 |
| GET | `/api/payable/settlement-months` | — | 结算月份列表 |
| GET | `/api/payable/supplier-months` | `q`, `supplier`, `settlement_month`, `payment_month` | 汇总行 |
| GET | `/api/payable/lines` | 同上 + `receive_from`, `receive_to` | 明细行 |

Flask：`app.py` 注入 `PayableService(inventory_store, cost_store, supplier_profile)`。

## 前端

在 `index.html` + `app.js` 增加 `payable` 子模块，结构镜像 `reconcile`：

- `PAYABLE_SUMMARY_COLS` / `PAYABLE_LIST_COLS`
- `payableDetailMode`、返回汇总、查看明细按钮
- 工具栏：结算月份、付款月份、收货日期起止（明细模式）、刷新、金额合计
- 侧栏 `data-submodule="payable"` 或 hash `#payable`

应收工具栏文案：「收款月份」保留；应付：「付款月份」「结算月份」「收货日期」。

## 测试

新建 `tests/test_payable.py`：

- 解析 `90天` / `现结` / 未知账期
- 回货流水 + BOM 价 → 金额、结算月、应付日
- 合并键
- 缺 BOM 行标记
- 汇总钻明细 API（Flask test client 或 service 层）

现有 `tests/test_reconciliation.py` 不受影响。

## 文档与合规

- **CL-0127**（或下一编号）：应收/应付拆分 + 应付模块
- `docs/architecture/data-model.md`：应付数据流（无新表）
- `docs/SOP/系统操作SOP.md`：§对账 → 应收、应付
- `app.py` `build` bump；静态 `?v=` 若改 `app.js`

## 非目标（一期不做）

- 应付核销、付款登记、发票号
- 回货时快照单价入库
- 演示数据（测）自动排除 — 可展示，与库存一致可选后续加筛
- 应收改为读客户档案逐户账期（仍用全局 config + 行上 payment_terms 展示）

## 风险与假设

- BOM 改价会导致历史应付重算 — 已确认接受「当前 BOM」
- 供应商档案缺 `reconciliation_period` → 默认 `month_21_20`（与档案默认一致）
- 回货流水供应商名须与 BOM / `supplier_profiles` 大小写一致（现有库存已校验供应商列表）
