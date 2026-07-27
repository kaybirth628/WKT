# SOP 配图说明

本目录存放《员工培训手册-图文版》的截图。手册正文中引用 `images/文件名.png`。

## 如何截屏（推荐）

1. 启动系统：双击 `P:\WKT\一键启动网页.bat`，浏览器打开 `http://127.0.0.1:5000`
2. 浏览器窗口宽度建议 **1440px** 或以上，缩放 **100%**
3. 使用 **Win + Shift + S** 区域截图，或浏览器全页截图扩展
4. 保存为 **PNG**，文件名与下表一致
5. 敏感信息（客户全称、单价、电话）可打码；演示数据可用「写入10料号演示」

## 自动截屏（推荐）

在项目根目录执行（须先 **启动网页.bat**，服务在 `http://127.0.0.1:5000`）：

```powershell
cd P:\WKT
pip install playwright pillow mss pygetwindow
python -m playwright install chromium
python scripts/create_sop_sample_po.py          # 样例 PO（OCR 用）
python scripts/capture_desktop_sop_shots.py     # Windows 实拍：bat + 服务窗口
python scripts/capture_sop_screenshots.py       # 浏览器全模块
# 仅重拍 OCR 预览：
python scripts/capture_ocr_preview_only.py
```

样例 PO 路径：`data/sop_samples/sample_po.pdf`（可替换为贵司脱敏 PO 后重跑 OCR 脚本）。

输出目录：`docs/SOP/images/`（与手册引用文件名一致）。

| 类型 | 文件 |
|------|------|
| **Windows 桌面实拍** | `00-start-bat.png`（资源管理器选中 bat）、`00-cmd-window.png`（服务 PowerShell 窗口） |
| **真实 OCR 预览** | `03-ocr-preview.png`（依赖 `sample_po.pdf` + 本机 OCR/AI 可用） |
| **真实浏览器截屏** | 其余模块页 |

## 必拍清单（手动补拍时参考）

| 文件名 | 拍什么 | 进入路径 |
|--------|--------|----------|
| `00-start-bat.png` | 资源管理器中 `一键启动网页.bat` | `P:\WKT` |
| `00-cmd-window.png` | 启动后命令行窗口（勿关提示） | 启动后 |
| `01-top-nav.png` | 顶栏全部菜单展开状态（可拼 2 张） | 首页任意页 |
| `01-page-footer.png` | 页脚标题与说明 | 切换模块时 |
| `02-entry-mode-select.png` | 订单录入 · 两种模式按钮 | 订单管理 → 订单录入 |
| `03-ocr-upload.png` | OCR 上传区 | 选「订单 OCR 识别」 |
| `03-ocr-preview.png` | 原件 + 识别表 + 黄标记 | 识别成功后 |
| `04-manual-form.png` | 手动录入完整表单 | 选「手动录入」 |
| `05-order-detail-list.png` | 订单明细表格 + 表头筛选 | 订单管理 → 订单明细 |
| `06-open-ship.png` | 未结订单 · 出货按钮 | 订单管理 → 未结订单 |
| `06-ship-confirm.png` | 出货确认弹窗 / 送货单 | 点出货后 |
| `06-batch-ship.png` | 合并出货勾选 | 未结 · 多选同一客户 |
| `07-shipped-list.png` | 出货明细 + 送货单按钮 | 订单管理 → 出货明细 |
| `08-reconcile-outlook.png` | 应收 · 6 个月滚动汇总 | 对账 → 应收 |
| `08-reconcile-detail.png` | 应收 · 查看明细钻取 | 点「查看明细」 |
| `09-payable-outlook.png` | 应付 · 6 个月汇总 | 对账 → 应付 |
| `10-customer-maint.png` | 客户信息维护表格 | 客商信息维护 → 客户 |
| `10-delivery-preview.png` | 送货单预览 | 客户一览 · 预览 |
| `11-supplier-maint.png` | 供应商维护 | 客商信息维护 → 供应商 |
| `12-bom-entry.png` | BOM录入 + 工序勾选 | BOM分析 → BOM录入 |
| `12-bom-query.png` | BOM查询结果 | BOM分析 → BOM查询 |
| `13-inventory-board.png` | 库存总览卡片（测/实） | 库存 → 库存总览 |
| `13-inventory-entry.png` | 工序出入库登记 | 库存 → 工序出入库 |
| `14-col-filter.png` | 表头 ▾ 列筛选面板 | 任意列表 |

## 可选补充

- `warn-yellow-red.png` — 未结订单交期黄/红预警行
- `force-close.png` — 强制结案确认框
- `inv-doc-no.png` — 流水中的 WG/FC/RK/CP 单号

## 更新记录

- 2026-07-23：初版清单（CL-0130）
- 2026-07-23：新增 `scripts/capture_sop_screenshots.py` 自动截屏
- 2026-07-23：桌面实拍 + 样例 PO + 真实 OCR 预览（`capture_desktop_sop_shots.py`、`create_sop_sample_po.py`）
