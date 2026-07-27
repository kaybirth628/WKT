# 应收 / 应付对账 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 顶栏「对账 ▾」拆分应收（现有出货对账）与应付（外发回货×供应商×BOM 工序价），应付支持汇总钻明细与收货日期区间筛选。

**Architecture:** 在 `reconciliation/` 包新增 `PayableService`，只读聚合 `inventory_movements`（回货）、BOM 工序价、`supplier_profiles`；前端 `app.js` 镜像现有 `reconcile` 子模块；应收仅改导航与文案。

**Tech Stack:** Python 3 / Flask / SQLite / 现有 `app.js` 子模块模式

**Spec:** `docs/superpowers/specs/2026-07-23-ar-ap-design.md`

---

## File map

| 文件 | 职责 |
|------|------|
| `reconciliation/payment_schedule.py` | 新增 `parse_supplier_payment_terms`、`compute_payable_date` |
| `reconciliation/payable_service.py` | 应付明细/汇总/月份列表 |
| `reconciliation/__init__.py` | 导出 `PayableService` |
| `web/app.py` | 路由 `/api/payable/*`、注入 service、`build` |
| `web/templates/_order_sidebar.html` | 对账下拉 |
| `web/templates/index.html` | payable 工具栏 DOM |
| `web/static/app.js` | payable 子模块 UI |
| `tests/test_payable.py` | 单元测试 |
| `docs/change/CHANGELOG.md` | CL-0127 |
| `docs/SOP/系统操作SOP.md` | 应收/应付操作 |
| `docs/architecture/data-model.md` | 应付数据流 |

---

### Task 1: 供应商账期解析与应付日

**Files:**
- Modify: `test_impl/order_management/reconciliation/payment_schedule.py`
- Test: `tests/test_payable.py`

- [ ] **Step 1: Write failing tests**

```python
def test_parse_supplier_terms():
    assert parse_supplier_payment_terms("90天") == {"term_days": 90, "is_cash": False}
    assert parse_supplier_payment_terms("现结")["is_cash"] is True

def test_payable_date_cash():
    assert compute_payable_date(date(2026, 7, 10), "现结") == date(2026, 7, 10)
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd tests && PYTHONPATH=.. python -m unittest test_payable.TestPayableSchedule -v
```

- [ ] **Step 3: Implement parser + compute_payable_date**

- [ ] **Step 4: Run test — expect PASS**

---

### Task 2: PayableService 明细与 BOM 取价

**Files:**
- Create: `test_impl/order_management/reconciliation/payable_service.py`
- Modify: `test_impl/order_management/reconciliation/__init__.py`
- Test: `tests/test_payable.py`

- [ ] **Step 1: Write failing test** — seed BOM + `outsource_receive` movement → `list_lines()` 返回正确 amount、settlement_month

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement**
  - 查 `inventory_movements` WHERE `action_type='outsource_receive'`
  - 本地日：`parse_ship_local_date(created_at)`
  - 单价：从 `CostRecordService` / store 读该料号 `process_code` 价
  - 供应商档案：`supplier_profile.store` 读 terms + period
  - `_merge_lines` 对称实现

- [ ] **Step 4: Run — PASS**

---

### Task 3: 汇总与月份列表

**Files:**
- Modify: `payable_service.py`
- Test: `tests/test_payable.py`

- [ ] **Step 1: Test** `summarize_by_supplier_month()` 分组与小计字段

- [ ] **Step 2: Implement** `list_settlement_months`、`list_payment_months`

- [ ] **Step 3: Run tests — PASS**

---

### Task 4: Flask API

**Files:**
- Modify: `test_impl/web/app.py`

- [ ] **Step 1: Wire** `PayableService` 单例（与 `InventoryService` / `CostStore` 同库）

- [ ] **Step 2: Add routes**
  - `GET /api/payable/config`
  - `GET /api/payable/payment-months`
  - `GET /api/payable/settlement-months`
  - `GET /api/payable/supplier-months`
  - `GET /api/payable/lines`

- [ ] **Step 3: Manual curl** 或 test client 冒烟

---

### Task 5: 导航 — 对账下拉

**Files:**
- Modify: `test_impl/web/templates/_order_sidebar.html`
- Modify: `test_impl/web/static/app.js`（SUBMODULES 标题「应收」）

- [ ] **Step 1:** 对账 ▾ → 应收 (`#reconcile`)、应付 (`#payable`)
- [ ] **Step 2:** 应收页标题改为「应收」

---

### Task 6: 应付前端子模块

**Files:**
- Modify: `test_impl/web/templates/index.html`
- Modify: `test_impl/web/static/app.js`

- [ ] **Step 1:** 复制 reconcile 模式：`payableDetailMode`、汇总列、明细列、工具栏（结算月、付款月、收货起止）
- [ ] **Step 2:** `loadPayableLines()` fetch `/api/payable/*`
- [ ] **Step 3:** hash `#payable` 切换子模块
- [ ] **Step 4:** bump `app.js?v=`、`build`

---

### Task 7: 文档与全量测试

**Files:**
- Modify: `docs/change/CHANGELOG.md`（CL-0127）
- Modify: `docs/SOP/系统操作SOP.md`
- Modify: `docs/architecture/data-model.md`

- [ ] **Step 1:** 登记 CHANGELOG
- [ ] **Step 2:** SOP §应收 / §应付
- [ ] **Step 3:** data-model 应付数据流（无新表）
- [ ] **Step 4:** `python -m unittest discover -s tests -p "test_*.py"`

---

## 验证清单

1. 顶栏 **对账 ▾** 可见应收、应付
2. **应收** 行为与改前一致
3. **应付** 汇总：供应商×结算月；点查看明细进入行级
4. 明细筛选 **收货日期起止** 生效
5. 金额 = 回货量 × BOM 工序价；缺 BOM 有提示
6. `/api/health` build 已更新
