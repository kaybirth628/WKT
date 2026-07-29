# WKT 销售管理系统 · 变更日志（CHANGELOG）

> 规则：每一次变更都必须在此登记，并**同步**更新《系统操作 SOP》（`docs/SOP/系统操作SOP.md`）（用户可见变更）。  
> **Bug 修复**须同时登记 [`BUG-FIX-LOG.md`](BUG-FIX-LOG.md)（BF-XXXX）并填写下方 **根因 / 防复发**。  
> Agent 合规流程见 [`AGENT-COMPLIANCE.md`](AGENT-COMPLIANCE.md)。  
> 里程碑版本发布时，同步更新《版本记录》（`docs/VERSION.md`）。  
> 未登记变更日志、未同步 SOP（且无免同步原因）、修复类未记 BF 的改动，视为不合规。

## 当前发布版本

**v0.6.0** · 2026-07-11 · 成本分析拆分与客商维护（CL-0108）  
上一里程碑：**v0.5.1** · 2026-05-30 · 顶部导航 UI 基线（CL-0103）  
详见 `docs/VERSION.md` · 回退见 `docs/RESTORE.md`

## 登记格式说明

| 字段 | 说明 |
|------|------|
| 变更编号 | CL-XXXX，递增不复用 |
| 日期 | 变更完成日期 |
| 类型 | 新增 / 优化 / 修复 / 重构 / 文档 |
| 合规等级 | A / B / C / D |
| 涉及模块 | 受影响的子模块或文件 |
| 变更内容 | 做了什么 |
| 根因 | **修复类必填**；其他填「—」 |
| 防复发 | 测试/规则/SOP 如何防止再犯 |
| 验证 | 如何验证通过 |
| SOP 同步 | 是 / 否 |
| SOP 免同步原因 | 仅当「否」时填写 |
| 关联 | BF-XXXX / UI-XXXX / CL-YYYY（可选） |

---

## 变更记录

### CL-0249 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | BOM 查询详情预览（`cost_query.js`、`cost_common.js`、`cost.css`） |
| 变更内容 | 「成本详情」弹窗改用与录入/修改相同的分步只读布局：头字段、已选工序、单价/供应商明细、成本合计 |
| 根因 | — |
| 防复发 | 共用 `renderCostRecordDetailHtml` |
| 验证 | BOM 查询点击行：预览区只读、布局与修改弹窗一致 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 仅预览 UI |
| 关联 | CL-0248 · UI-0018 |

### CL-0248 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | BOM 查询修改弹窗（`cost_query.html/js`、`cost_common.js`） |
| 变更内容 | 「修改」弹窗工序区与 BOM 录入一致；修复多余 `</div>` 致保存/取消漂到弹窗外；按钮区底部居中 |
| 根因 | — |
| 防复发 | 共用 `bindStagedProcessPicker` / `renderProcessPickOnlyGridHtml` |
| 验证 | BOM 查询 → 修改：勾选工序 → 底部明细；保存后供应商/单价正确 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 与录入页同逻辑，步骤更直观 |
| 关联 | CL-0247 · UI-0017 |

### CL-0247 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | BOM 录入 UI（`cost.css`/`cost_common.js`）、全局 UI 规范（`style.css`） |
| 变更内容 | 工序勾选与明细区布局优化；供应商/单价等宽底对齐；全局 §7.9 输入框一致性与多列对齐规则（UI-0016）；combo 主输入统一 8px 圆角/`border-strong` |
| 根因 | — |
| 防复发 | `ui-layout-rules.md` §7.9 + `style.css` combo 与 `.field input` 同 token |
| 验证 | BOM 录入明细对齐；规范文档 UI-0016 已登记 |
| SOP 同步 | 否 |
| SOP 免同步原因 | UI 规范与布局密度 |
| 关联 | UI-0016 · CL-0246 |

### CL-0246 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | BOM 录入 UI（`cost_entry`/`cost_common`/`cost.css`） |
| 变更内容 | 工序两步操作：上方仅勾选；底部填单价与供应商。修复多余 `</div>` 导致批量导入页误显示「预览/提交」；恢复 `cost-entry-layout` 横向按钮 |
| 根因 | 单价/供应商与勾选同卡，料号载入与用户点击竞态 |
| 防复发 | 分步 UI；明细区独立于 `#processGrid` 锁定 |
| 验证 | BOM 录入：勾选 → 底部出现明细行；保存校验仍生效 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 同页分步，流程更直观 |

### CL-0245 · 2026-07-29 · 修复（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | BOM 录入（`cost_entry.js`） |
| 变更内容 | 料号载入后工序回填延迟 400ms：窗口内点工序视为手工编辑、取消自动覆盖；下拉选料号不再清空编辑标记；mousedown 提前记录触摸 |
| 根因 | 本地快网络 lookup 瞬间完成，员工 Tab 料号后立即点工序仍被 `applyProcessPrices` 覆盖 |
| 防复发 | BF-0018；`scheduleProcessApply` + `shouldSkipProcessApply` |
| 验证 | Playwright 快点击场景；`test_cost_*` 通过 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 防误覆盖 |
| 关联 | BF-0018 · CL-0244 |

### CL-0244 · 2026-07-29 · 修复（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | BOM 录入（`cost_entry.js`） |
| 变更内容 | 员工手速快时工序被刷掉：记录工序区手工编辑，lookup 返回后若已动过工序则只填客户/品名等基础字段、不覆盖工序；去掉 blur 重复 lookup；换料号/下拉换料时重置编辑标记 |
| 根因 | lookup 异步回填 `applyProcessPrices` 覆盖用户已勾选的工序与供应商 |
| 防复发 | BF-0017；`processGridTouched` + `skipProcesses`；`scripts/test_bom_entry_lookup_race.py` |
| 验证 | Playwright：先勾工序再填料号 → 烤漆保留；载入中锁定仍生效 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 防误覆盖，操作步骤不变 |
| 关联 | BF-0017 · CL-0243 |

### CL-0243 · 2026-07-29 · 修复（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | BOM 录入（`cost_entry.js`、`cost.css`） |
| 变更内容 | 料号 lookup 返回空工序时不再清空已勾选工序；载入期间工序区短暂锁定并提示「正在载入 BOM / 工序」；防并发 lookup 覆盖 |
| 根因 | `applyProcessPrices` 先全量取消勾选再 early return；lookup 异步返回时与用户手工勾选竞态 |
| 防复发 | BF-0016；先构建 byCode 再改 DOM；in-flight 锁工序区 |
| 验证 | BOM 录入：录料号后立即点工序应被锁住；空工序 BOM 载入后已勾选项保留；`test_cost_*` 通过 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 防误操作，操作流程不变 |
| 关联 | BF-0016 |

### CL-0242 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | 全站悬停 tooltip（`hover_tip.js`、`style.css`） |
| 变更内容 | 截断单元格黑色悬停框改为可移入停留：文本可选中复制；双击复制全文并提示「已复制到剪贴板」；底部提示「拖选复制 · 双击复制全文」 |
| 根因 | — |
| 防复发 | `hover_tip.js` 统一行为；移入 tooltip 延迟关闭 |
| 验证 | BOM 查询等表格悬停 → 移入黑框拖选或双击复制 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 交互细节优化，操作流程不变 |

### CL-0241 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | 操作记录（审计日志） |
| 变更内容 | 列表「模块」「动作」列改为中文展示名（与顶栏一致：订单管理、BOM信息、录入订单行等）；筛选下拉同步；飞书操作通知模块名统一 |
| 根因 | — |
| 防复发 | `audit_labels.py` + `test_auth` |
| 验证 | 打开 `/admin/audit`，模块/动作应为中文 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 展示层优化 |

### CL-0239 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | BOM 工序多供应商 UI |
| 变更内容 | 已选供应商改为 **0.8125rem 整行标签**（可读性提升）；「添加供应商」改用 §7.8 **`inv-bom-combo`**（▼ 展开、下拉内关键字筛选）；`InventoryBomLookup.bindCustomer` 支持 `onSelect` 回调 |
| 根因 | — |
| 防复发 | `ui-layout-rules.md` §7.8；BOM 录入/查询编辑页对照 |
| 验证 | Ctrl+F5 → 勾选外发工序 → 点 ▼ 应展开带搜索框的下拉；已选供应商字号与单价框一致 |
| SOP 同步 | 否 |
| SOP 免同步原因 | UI 交互对齐 CL-0238 |
| 关联 | CL-0238 |

### CL-0238 · 2026-07-29 · 新增（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | BOM 录入/查询编辑、成本记录服务、工序库存 |
| 变更内容 | 编辑 BOM 时外发工序可绑定**多家供应商**：`process_prices_json` 增加 `suppliers[]`，`supplier` 仍为主供应商；录入/查询 UI 改为标签 +「添加供应商」；库存出入库下拉优先展示 BOM 已绑定的供应商 |
| 根因 | — |
| 防复发 | `normalize_process_suppliers` + `test_cost_records.test_multi_process_suppliers` |
| 验证 | BOM 录入勾选外发工序→添加 2 家供应商→保存→查询编辑应回显；`python -m unittest tests.test_cost_records -v` |
| SOP 同步 | 是 |

### CL-0237 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | BOM Excel 批量导入、供应商档案 |
| 变更内容 | 解析工序供应商时按 `supplier_profiles.json` 自动将简称（如「锦拓」）匹配为全称（如「吴中区甪直锦拓精密电子厂」）；唯一/备注匹配写入 BOM，未匹配/多家歧义写入预览 warnings |
| 根因 | — |
| 防复发 | `resolve_supplier_name` + `test_supplier_profile` / `test_bom_form_import` |
| 验证 | `python -m unittest tests.test_supplier_profile tests.test_bom_form_import -v` |
| SOP 同步 | 否 |
| SOP 免同步原因 | 导入逻辑增强，用户可见为预览提示 |

### CL-0236 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | 全局 UI：BOM 查询/分析、送货单模板、导入预览、字体、hover-tip、审计/用户页 |
| 变更内容 | 全量对齐 `ui-layout-rules` V3：BOM 查询筛选+编辑弹窗 combo；成本分析原材 combo；送货单模板客户 combo；Excel 导入预览行内 combo；新增 `hover_tip.js` 替换 `title` tooltip；字体 Inter→Noto Sans SC+DM Sans；审计/用户页 list-table+页脚；`InventoryBomLookup` 导出 `STANDARD_COMBO_OPTS`/`bindPartOnly`/`bindMaterialList` |
| 根因 | — |
| 防复发 | §7.6/§7.8/§5.1；`hover_tip.js` 复用 |
| 验证 | 各模块 Ctrl+F5；health `build=20260729-ui-full-align`；unittest |
| SOP 同步 | 否 |
| SOP 免同步原因 | UI/交互对齐，业务流程未变 |
| 关联 | UI-0015 · CL-0235 |

### CL-0235 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | BOM 录入、库存四页 |
| 变更内容 | UI 对齐 §7.8：`cost_entry` 手动录入客户/料号/品名/材质改 `InventoryBomLookup`（▼、聚焦展开、面板搜索、单列）；Excel 导入「统一客户」同组件；库存总览/流水/工序出入库/排产筛选 combo 补全标准参数 |
| 根因 | — |
| 防复发 | `ui-layout-rules.md` §7.8；参考 `initOrderEntryCombos` |
| 验证 | 打开 BOM 录入→手动录入，点击客户/料号应展开下拉；库存总览筛选栏同效；`python -m unittest discover -s tests -p "test_*.py"` |
| SOP 同步 | 否 |
| SOP 免同步原因 | 仅 UI 交互对齐，业务流程与 API 未变 |
| 关联 | UI-0014 |

### CL-0234 · 2026-07-29 · 文档（A）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `.cursor/rules/`、`scripts/sync-cursor-rules.ps1`、`.cursorrules` |
| 变更内容 | Cursor **Project Rules 自动加载**：`00-wkt-master.mdc` 总入口 + 校验脚本；打开 WKT 即注入 alwaysApply 规则 |
| 根因 | — |
| 防复发 | sync-cursor-rules.ps1 |
| 验证 | `scripts/sync-cursor-rules.ps1` 全 OK |
| SOP 同步 | 否 |
| SOP 免同步原因 | Agent/Cursor 配置 |

---

### CL-0233 · 2026-07-29 · 文档（A）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `.cursor/rules/wkt-read-before-edit.mdc`、`AGENT-COMPLIANCE.md`、`AGENTS.md` |
| 变更内容 | 新增 **alwaysApply** 规则：每次改代码前必须用 Read 读 AGENTS/UI/合规/生产安全；不可凭会话记忆跳过 |
| 根因 | — |
| 防复发 | wkt-read-before-edit.mdc alwaysApply |
| 验证 | 新 Agent 会话可见该 rule；AGENT-COMPLIANCE §2 动手前 Checklist |
| SOP 同步 | 否 |
| SOP 免同步原因 | Agent 内部治理 |

---

### CL-0232 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | 订单手动录入、`docs/design/ui-layout-rules.md` |
| 变更内容 | 移除 **接单日期**（新建默认当天）；表单 5×2 等宽；**UI 规则** 写入 `ui-layout-rules.md` §7.8（可搜索下拉）§9.5（录入网格） |
| 根因 | — |
| 防复发 | UI-0013；Agent 改 UI 前必读 ui-layout-rules V3 |
| 验证 | 新建订单无接单日期字段；列表显示当天；health build `20260729-entry-ui-rules` |
| SOP 同步 | 是 |

---

### CL-0231 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | 订单手动录入 UI |
| 变更内容 | 表单 **2 行 × 6 列**：第1行 客户/料号/品名/单重/材质；第2行 接单日期/交期/订单号/PO/税率/单价；移除已出货、账期、单位（隐藏默认 0/空/PCS） |
| 根因 | — |
| 防复发 | — |
| 验证 | 手动录入仅两行 11 个可见字段；提交仍带 shipped_qty=0 |
| SOP 同步 | 是 |

---

### CL-0230 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | 订单手动录入 UI |
| 变更内容 | 表单压缩为 **3 行 × 5 列** 等宽网格；账期、单价与其他字段同宽；去掉分段线与通栏大框 |
| 根因 | — |
| 防复发 | — |
| 验证 | 手动录入 14 项字段 3 行排布、框宽一致 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 仅布局紧凑，字段含义不变 |

---

### CL-0229 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | 订单手动录入 UI |
| 变更内容 | 移除客户/品名旁 **「+」** 按钮；表单改为 **4 列等宽网格**（账期通栏、单价占 2 列），字段对齐一致 |
| 根因 | — |
| 防复发 | — |
| 验证 | 手动录入表单行列对齐、无加号按钮 |
| SOP 同步 | 是 |

---

### CL-0228 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | 订单手动录入、`inventory_bom_lookup.js` |
| 变更内容 | **客户料号** 改为可搜索下拉（仅显示料号）；**品名规格** 下拉仅显示品名；选料号优先按 BOM 回填品名/单重/材质；表单料号列置于品名之前 |
| 根因 | — |
| 防复发 | — |
| 验证 | 料号下拉只显示料号，选后品名自动填入；品名下拉只显示品名 |
| SOP 同步 | 是 |

---

### CL-0227 · 2026-07-29 · 修复（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `inventory_bom_lookup.js`、订单手动录入 |
| 变更内容 | 下拉面板 **顶部增加搜索框**（置顶不随列表滚动）；输入关键字实时筛选客户/BOM；主输入框与搜索框双向同步 |
| 根因 | 仅有列表无框内搜索，用户无法在展开的下拉里筛选 |
| 防复发 | — |
| 验证 | 展开客户/品名下拉 → 顶部有搜索框 → 输入「商米」列表收窄 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 搜索框为 CL-0225/0226 交互补全 |

---

### CL-0226 · 2026-07-29 · 修复（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `inventory_bom_lookup.js`、订单手动录入 |
| 变更内容 | 客户/品名 **点击或聚焦即展开下拉列表**（无需先输入）；右侧 **▼** 按钮可展开；输入关键字实时筛选 |
| 根因 | CL-0225 仅在有输入时才请求联想，空栏聚焦无下拉 |
| 防复发 | — |
| 验证 | 手动录入 → 点客户/品名栏或 ▼ → 出现列表；输入关键字列表收窄 |
| SOP 同步 | 是 |
| SOP 免同步原因 | — |

---

### CL-0225 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | 订单手动录入、`inventory_bom_lookup.js`、`line_service.py` |
| 变更内容 | **客户**、**品名规格** 由普通下拉改为 **可搜索联想框**：客户搜主数据（含历史订单客户）；品名/料号搜 BOM，点选后自动回填客户料号、单重、材质 |
| 根因 | — |
| 防复发 | — |
| 验证 | 订单录入 → 手动录入 → 客户/品名输入关键字出现下拉 → 点选回填；`/api/master/customers?q=` 返回匹配项 |
| SOP 同步 | 是 |

---

### CL-0224 · 2026-07-29 · 修复（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `cost_query.js`、`cost_common.js` |
| 变更内容 | BOM 查询 **修改弹窗** 填表时意外关闭：Esc 关供应商下拉不再连带关弹窗；Enter 不再误触提交；取消点遮罩关弹窗 |
| 根因 | 供应商搜索 Esc 冒泡到全局 handler；表单 Enter 默认 submit；误点弹窗外灰色区域关闭 |
| 防复发 | BF-0015 |
| 验证 | BOM 查询 → 修改 → 工序供应商按 Esc / Enter、点遮罩，弹窗应保持 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 交互修复，无流程变更 |
| 关联 | BF-0015 |

### CL-0223 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `cost_query.js`、`cost.css`、`cost_query.html` |
| 变更内容 | **撤销** BOM 查询按客户折叠（CL-0222），恢复平铺列表 |
| 根因 | — |
| 防复发 | — |
| 验证 | `/bom/query` 列表直接显示全部 BOM 行 |
| SOP 同步 | 是 |
| 关联 | CL-0222 |

### CL-0222 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `cost_query.js`、`cost.css`、`cost_query.html` |
| 变更内容 | BOM 查询列表 **按客户折叠**：默认只显示客户分组行（名称、条数、最近更新），点 **▸** 展开明细；多客户时汇总显示「N 个客户」 |
| 根因 | — |
| 防复发 | — |
| 验证 | 打开 `/bom/query`，确认分组折叠/展开与修改删除仍可用 |
| SOP 同步 | 是 |

### CL-0221 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `bom_form_import.py`、`app.py`、`cost_bom_import.js`、`cost.css` |
| 变更内容 | BOM 解析预览：**本批相同料号行橙色高亮** +「料号重复」标签；说明列提示重复行号；改料号后自动刷新重复标记 |
| 根因 | — |
| 防复发 | `test_batch_duplicate_part_hints` |
| 验证 | `python -m unittest discover -s tests -p test_bom_form_import.py -v` |
| SOP 同步 | 否 |

### CL-0220 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `bom_form_import.py`、`app.py`、`cost_bom_import.js`、`test_bom_form_import.py` |
| 变更内容 | BOM Excel **解析预览**不再查库、不提示覆盖，**完整保留**全部解析行供人工核对；点 **批量上传** 前才校验库内已存在料号并提示覆盖，写入仍按料号覆盖逻辑 |
| 根因 | — |
| 防复发 | `test_existing_part_preview_not_blocked` 分拆解析/上传两阶段断言 |
| 验证 | `python -m unittest tests.test_bom_form_import -v` |
| SOP 同步 | 是 |

### CL-0219 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `bom_form_import.py`、`record_service.py`、`cost_store.py` |
| 变更内容 | 表内未填产品料号：预览/入库显示 **`/`**，档位待核可导入；多个 `/` 互不覆盖 |
| 根因 | — |
| 防复发 | `test_unfilled_part_no_shows_slash_and_imports` |
| 验证 | `test_bom_form_import.py` |
| SOP 同步 | 否 |

### CL-0218 · 2026-07-29 · 修复（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `bom_form_import.py`、`test_bom_form_import.py` |
| 变更内容 | 产品料号 **完整保留** Excel 原值；仅 **换行** 表示同 Sheet 多产品；料号内 `/` 不再拆分（如 `11*000000/08016-01`） |
| 根因 | `_split_multi_values` 对料号也按 `/` 拆，锐霸 composite 料号被拆成两条 |
| 防复发 | BF-0014；`test_part_no_slash_preserved_ruiba` |
| 验证 | `test_bom_form_import.py`；锐霸 xls 解析 46 行（原误 73 行） |
| SOP 同步 | 否 |

### CL-0217 · 2026-07-29 · 修复（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `bom_form_import.py`、`test_bom_form_import.py` |
| 变更内容 | BOM 批量导入：**一 Sheet 一 BOM**；共用表头多型号品名/重复料号时按 Sheet 名拆分；Excel 数值料号规范化 |
| 根因 | 多 Sheet 同料号导入互相覆盖；表头品名 `A/B/C` 未按 Sheet 拆开 |
| 防复发 | BF-0013；新增单元测试 |
| 验证 | `test_bom_form_import.py` 26 项通过 |
| SOP 同步 | 是 |
| 关联 | BF-0013 |

### CL-0216 · 2026-07-29 · 文档（D）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `docs/SOP/工序出入库-操作说明.md/pdf`、`scripts/export_inv_stage_guide_pdf.py` |
| 变更内容 | 新增工序出入库员工宣导 PDF（含点选/编辑截图与操作要点） |
| 根因 | — |
| 防复发 | — |
| 验证 | `python scripts/export_inv_stage_guide_pdf.py` 生成 PDF |
| SOP 同步 | 否 |
| SOP 免同步原因 | 独立宣导材料，非系统操作 SOP 正文变更 |

### CL-0215 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | 顶部导航、BOM 录入/查询页脚、`app.js`、SOP |
| 变更内容 | 模块名 **BOM分析** 更名为 **BOM信息** |
| 根因 | — |
| 防复发 | — |
| 验证 | 顶栏与各页脚显示「BOM信息」 |
| SOP 同步 | 是 |

### CL-0214 · 2026-07-29 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `inventory.js`、`inventory.css` |
| 变更内容 | 库存总览工序卡片与工序出入库页统一：固定宽度等高布局；展示场内/在途/返修/供应商；成品卡含返修在途 |
| 根因 | — |
| 防复发 | — |
| 验证 | 打开库存总览，多料号卡片尺寸与字段与工序出入库一致 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 只读总览展示对齐，操作流程不变 |

### CL-0213 · 2026-07-29 · 重构（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `inventory_entry.js/html`、`inventory/service.py`（已在先）、`test_inventory.py` |
| 变更内容 | 工序库存页移除「高级登记」折叠区；改为点选工序（最多 2 道，角标 ①②）→ 编辑：单道改各桶数量 + 必选供应商（`stage-set`）；双道登记流转 + 各选供应商（`stage-flow`）。流水单号统一 `WKT+日期+序号`；改数流水备注仅存供应商名 |
| 根因 | — |
| 防复发 | 单元测试 doc_no 前缀 WKT、set_stage_buckets 备注为供应商 |
| 验证 | `python -m unittest tests.test_inventory`；载入料号点选 1/2 道工序编辑保存 |
| SOP 同步 | 是 |
| SOP 免同步原因 | — |
| 关联 | UI-0012 |

### CL-0212 · 2026-07-28 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `inventory_entry` 页 |
| 变更内容 | 供应商改为「按钮 + 下拉面板」：面板顶部独立搜索框，输入关键字实时过滤列表 |
| 根因 | 上一版把已选值填在输入框，用户误以为普通下拉无法搜索 |
| 防复发 | — |
| 验证 | 点击供应商按钮见搜索框；输入「麦凯」等可过滤 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 交互细节优化 |
| 关联 | UI-0011 |

### CL-0211 · 2026-07-28 · 优化（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `inventory/service.py`、`inventory_entry` 页 |
| 变更内容 | 工序卡片展示供应商；单道/双道编辑均必选供应商（下拉，默认 BOM）；保存时回写 BOM 工序供应商 |
| 根因 | — |
| 防复发 | `test_board_stage_includes_supplier`、`test_set_stage_buckets_syncs_supplier` |
| 验证 | 单元测试通过；载入料号见卡片供应商；编辑保存后 BOM 同步 |
| SOP 同步 | 是 |

### CL-0210 · 2026-07-28 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `inventory/service.py` · 流动记录展示 |
| 变更内容 | 工序卡片改数流水：动作按桶显示「修改场内/在途/返修/成品库存」；工序列仅工序名；数量列显示「原值-新值」（如 50-80） |
| 根因 | — |
| 防复发 | `test_adjust_outsource_balance_display` |
| 验证 | 单元测试通过；改在途 50→80 后流动记录三列符合预期 |
| SOP 同步 | 是 |

### CL-0209 · 2026-07-28 · 修复（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `inventory/service.py` `_movement_route_display`、`inventory_entry` 页 |
| 变更内容 | 修复载入含「工序流转」流水的料号（如 TST-PL-002）时 API 500 导致前端 JSON 解析失败；按 UI V3 去掉页内长说明，选中工序后才显示操作条 |
| 根因 | CL-0208 新增 `ACTION_STAGE_FLOW` 展示分支引用未定义的 `from_st`/`to_st`，含 stage_flow 流水的料号触发 500 HTML 响应 |
| 防复发 | `test_stage_flow_movement_route_display` |
| 验证 | `python -m unittest tests.test_inventory` 通过；载入 TST-PL-002 无报错 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 仅修复载入失败与 UI 文案精简，操作流程未变 |
| 关联 | BF-0012 / UI-0009 |

### CL-0208 · 2026-07-28 · 优化（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `inventory/service.py`、`stage-flow` API、`inventory_entry` |
| 变更内容 | 工序卡片固定展示场内库存/在途库存/返修；编辑改为选择从/到状态登记**工序流转**（非直接改目标数）；支持外部来料与跨工序 |
| 根因 | — |
| 防复发 | `test_stage_flow_*` |
| 验证 | 单元测试通过；点击工序→选状态→登记流转，流动记录显示路线 |
| SOP 同步 | 是 |
| 关联 | UI-0008 |

### CL-0207 · 2026-07-28 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `inventory_entry` 页 UI |
| 变更内容 | 工序卡片默认只读展示（与库存总览一致）；点击后在下方展开编辑区，避免卡片参差不齐 |
| 根因 | — |
| 防复发 | UI-0007 |
| 验证 | 载入料号见整齐卡片；点击单道展开编辑；保存后收起 |
| SOP 同步 | 是（点击编辑说明） |
| 关联 | UI-0007 |

### CL-0206 · 2026-07-28 · 优化（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `inventory/service.py`、`inventory_entry` 页、`/api/inventory/stage-set` |
| 变更内容 | 工序库存改为**各道独立修改**场内/在途/返修；保存时按变更桶写入工序流动记录；流动记录按料号展示 |
| 根因 | — |
| 防复发 | `test_set_stage_buckets_records_movements` |
| 验证 | `python -m unittest tests.test_inventory` 通过；载入料号后改数保存，下方可见流动记录 |
| SOP 同步 | 是 |
| SOP 免同步原因 | — |

### CL-0205 · 2026-07-28 · 修复（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `order_intake/deepseek.py`、`part_no_fill.py`、`intake_service.py` |
| 变更内容 | 修复大沃等 PO 使用「物料编码」（如 `1-000797`）时 OCR 识别后客户料号全空：扩展 DeepSeek 提示词映射规则；增加 OCR 原文兜底补全 |
| 根因 | CL-0035 提示词将 customer_part_no 限定为「客户料号/料号」且举例 B 开头；大沃表格列为「物料编码」、原始编码为空，AI 合规留空 |
| 防复发 | `part_no_fill` 单元测试；提示词明确物料编码/原始编码列映射 |
| 验证 | `python -m unittest tests.test_order_intake tests.test_field_validation` 通过 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 识别逻辑修复，用户操作流程不变 |
| 关联 | BF-0011 |

### CL-0204 · 2026-07-28 · 修复（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `.gitignore`、`scripts/git-push.ps1` |
| 变更内容 | 修复推送失败：`git add -A` 误纳入 `data.local.bak-*` 本地备份；加入 gitignore + 提交前自动 unstage 数据库/备份路径 |
| 根因 | 下载云端覆盖本地时产生多份 `data.local.bak-*`，未 gitignore，`git add -A` 整包暂存后触发 Assert-NoDatabaseStaged |
| 防复发 | `.gitignore` `data.local.bak-*/`；`Invoke-SafeGitStage` |
| 验证 | `git add -A` 后 staged 中 bak 数量为 0；一键推送可过 commit 步骤 |
| SOP 同步 | 否 |
| SOP 免同步原因 | 开发脚本 |
| 关联 | BF-0010 |

### CL-0203 · 2026-07-28 · 优化（D）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `scripts/git-push.ps1` |
| 变更内容 | 推送 GitHub 时 **自动推荐** commit 信息：读取 CHANGELOG 最新 CL 条目，**直接回车**即可提交；里程碑 tag 默认跳过 |
| 根因 | — |
| 防复发 | — |
| 验证 | 运行 `一键推送云端和GitHub.bat`，见绿色 Recommended 行，回车两次完成 commit+push |
| SOP 同步 | 否 |
| SOP 免同步原因 | 开发脚本交互优化 |

### CL-0202 · 2026-07-28 · 重构（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | 删除 `scripts/inspect-cloud-data.ps1`、`restore-cloud-suppliers.ps1`、`seed_sop_test_data.py`、`reset_order_db.ps1`、`seed_board_demo.py`、`force-restart-cloud.ps1`；SOP、data-model |
| 变更内容 | 删除无 bat 入口及违背生产安全的废弃/清库脚本；文档改为「下载云端覆盖本地」 |
| 根因 | — |
| 防复发 | 仅保留 3 个 bat；`PRODUCTION-SAFETY.md` |
| 验证 | 上述文件不存在；`test_sop_seed.py` 仍通过（直接用 `sop_seed` 模块） |
| SOP 同步 | 是 |
| SOP 免同步原因 | — |

### CL-0201 · 2026-07-28 · 重构（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | 根目录 bat、`scripts/push-cloud-and-github.ps1`、`sync-to-cloud.ps1`、`PRODUCTION-SAFETY.md`、`.cursor/rules/wkt-production-safety.mdc`、`RESTORE.md`、SOP §九 |
| 变更内容 | 测试阶段运维精简为 **3 个 bat**：启动网页 / 推送云端+GitHub / 下载云端覆盖本地；删除全量同步、查询云端、恢复供应商、SOP 测试数据等 bat；**禁用** `-FullData`/`-WithMasterData`；写入生产安全强制规范 |
| 根因 | — |
| 防复发 | `wkt-production-safety.mdc` alwaysApply；`sync-to-cloud.ps1` 入口 throw |
| 验证 | 根目录仅 3 个 `一键*.bat`；执行全量同步参数应报错 |
| SOP 同步 | 是 |
| 关联 | — |

### CL-0200 · 2026-07-28 · 文档（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `docs/change/AGENT-COMPLIANCE.md`、`BUG-FIX-LOG.md`、`.cursor/rules/wkt-change-governance.mdc`、`AGENTS.md`、`系统操作SOP.md` §4.1/§七 |
| 变更内容 | 建立 Agent 变更治理：强制 CL+BF+SOP 规则；回溯登记 BOM 导入 Bug BF-0001～0008；**补写 SOP** BOM 批量导入现行流程（mode 选择、预览编辑、底部批量上传、料号覆盖、成功提示） |
| 根因 | — |
| 防复发 | `wkt-change-governance.mdc` alwaysApply；修 Bug 前查 BUG-FIX-LOG |
| 验证 | 文档齐全；SOP §4.1 与当前 `cost_entry.html` 一致 |
| SOP 同步 | 是 |
| 关联 | BF-0009 |

### CL-0199 · 2026-07-28 · 文档（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `docs/design/ui-layout-rules.md`（V3）、`GLOBAL-RULES-INDEX.md`、Agent rules/skill、`AGENTS.md` |
| 变更内容 | 将 **全部** 全局 UI 规则（顶栏、主题、字体、间距、组件、list-table、录入模板等）合并入 V3 规范；改 UI 须先参照全文 |
| 验证 | `docs/design/GLOBAL-RULES-INDEX.md` 可索引所有规则源；UI-0006 已登记 |
| SOP 同步 | 否 |

### CL-0198 · 2026-07-28 · 文档（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `docs/design/`、`.cursor/rules/wkt-ui-design.mdc`、`.cursor/skills/wkt-ui-design/`、`AGENTS.md` |
| 变更内容 | 固化用户「清爽布局」偏好：`ui-layout-rules.md`（V2 权威）、`UI-CHANGELOG.md`、Agent 规则与 skill；新功能须 follow |
| 验证 | Agent 改 UI 前可读 rules + design 目录；UI-0005 已登记 |
| SOP 同步 | 否 |

### CL-0197 · 2026-07-28 · 优化（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `cost_entry.html`、`cost_entry.js`、`cost_bom_import.js`、`cost.css` |
| 变更内容 | BOM 录入对齐订单录入清爽模式：mode-card +「请先选择录入方式」；去除上传区/页脚长说明；初始不展开子面板 |
| 验证 | 进入页仅见两个模式按钮与提示；选模式后才出现上传或表单 |
| SOP 同步 | 否 |

### CL-0196 · 2026-07-28 · 优化（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `cost_entry.html`、`cost.css` |
| 变更内容 | BOM 导入/upload 区去掉多余留白；预览表取消内嵌纵向滚动，改为整页自然展开；表格字体/颜色与全局 list-table 一致 |
| 验证 | 导入规则区无大块空白；10+ 行预览无内部滚动条；字号与 BOM 查询页一致 |
| SOP 同步 | 否 |

### CL-0195 · 2026-07-28 · 修复（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `cost_bom_import.js`、`cost_entry.html`、`cost.css` |
| 变更内容 | 修复批量上传成功后界面回到预览/选文件前的混淆状态：成功后清空预览表、回到初始上传页，并在顶部显示绿色「批量上传成功」横幅（含前往 BOM 查询链接） |
| 验证 | 批量上传成功后预览区隐藏、文件已清空、成功提示可见 |
| SOP 同步 | 否 |

### CL-0194 · 2026-07-28 · 优化（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `cost_entry.html`、`cost_bom_import.js`、`cost.css` |
| 变更内容 | BOM 导入预览：顶部去掉文件区/导入按钮与系统识别条；客户栏改为纯文本输入（无下拉）；人工审核后表格底部增加 **批量上传** 按钮 |
| 验证 | 解析后仅见预览表 + 底部上传；客户输入框无 datalist 箭头 |
| SOP 同步 | 否 |

### CL-0193 · 2026-07-28 · 优化（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `cost_bom_import.js`、`cost_entry.html`、`cost.css`、`bom_form_import.py` |
| 变更内容 | BOM 导入预览表：**Sheet/客户/料号/品名/单重**均可编辑；说明/制程列悬停显示全文；表格对齐全局 list-table 间距与列宽 |
| 验证 | `test_revalidate_field_override_part_no`；预览表修改后 revalidate 再导入 |
| SOP 同步 | 否 |

### CL-0192 · 2026-07-28 · 新增（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `bom_form_import.py`、`app.py`、`cost_bom_import.js`、`cost_entry.html` |
| 变更内容 | BOM 批量导入：解析后**人工确认客户**——表格内可编辑客户、支持「统一客户」批量应用到全部/阻断行；`POST /api/cost/bom-import/revalidate` 重新校验档位后再导入 |
| 验证 | `test_revalidate_manual_customer_unblocks_row`；东硕 BOM 中 DLS/XFT 行可批量改为鑫福泰-东硕后导入 |
| SOP 同步 | 否 |

### CL-0191 · 2026-07-28 · 修复（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `cost_store.py`、`cost_query.js`、`cost_query.html` |
| 变更内容 | BOM 查询改为按 **updated_at（更新时间）** 排序与展示；修复 SQLite `datetime()` 无法解析 ISO 时区导致覆盖后旧记录仍排后；批量导入覆盖后全部被更新记录排到列表最前 |
| 验证 | `test_list_records_ordered_by_updated_at`；本地重复导入同一 BOM 后查询列表顶部均为刚覆盖记录 |
| SOP 同步 | 否 |

### CL-0190 · 2026-07-28 · 修复（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `record_service.py`、`cost_bom_import.js`、`cost_entry.html` |
| 变更内容 | 明确 BOM 批量导入覆盖规则：**仅按产品料号**匹配，后导入覆盖先导入（含重复上传同一 Excel）；覆盖更新时不再因客户简称/全称不一致而失败；移除「相同料号覆盖」勾选项（改为固定行为） |
| 验证 | `test_import_overwrite_reupload_same_excel`、`test_import_overwrite_same_part_different_customer_alias` |
| SOP 同步 | 否 |

### CL-0189 · 2026-07-28 · 修复（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `cost_bom_import.js`、`cost_query.js`、`bom_form_import.py`、`cost_store.py` |
| 变更内容 | 修复 BOM 批量导入成功后无提示：结果横幅保留成功/失败明细与「前往 BOM 查询」链接；导入 payload 将简称「大沃」等统一展开为客商全称；BOM 查询客户筛选改为模糊匹配并支持 URL 参数 |
| 验证 | `test_bom_form_import`；导入后结果区可见；`/cost/query?q=大沃` 可定位记录 |
| SOP 同步 | 否 |

### CL-0188 · 2026-07-28 · 修复（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `customer_name.py`、`bom_form_import.py`、`cost_bom_import.js` |
| 变更内容 | 修复 BOM 批量导入误报「客户未匹配」：文件名 `大沃产品BOM(1)(1)` 正确剥离为「大沃」；表内已匹配客户时顶栏显示成功而非文件名错误；新增「大沃」别名 |
| 验证 | `test_filename_dawo_product_bom_copy_suffix`、`test_preview_meta_uses_sheet_customer_when_filename_fails` |
| SOP 同步 | 否 |

### CL-0187 · 2026-07-28 · 新增（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `record_service.py`、`cost_store.py`、`bom_form_import.py`、`cost_bom_import.js`、`cost_entry.html`、`app.py` |
| 变更内容 | BOM 批量导入支持 **相同料号覆盖**：`POST /api/cost/bom-import/commit` 默认 `overwrite=true`，更新最新 BOM 并删除同料号重复行；预览「料号已存在」改为待核（非阻断）；UI 勾选「相同料号覆盖已有 BOM」 |
| 验证 | `test_import_overwrite_same_part_no`、`test_existing_part_preview_not_blocked` |
| SOP 同步 | 否 |

### CL-0186 · 2026-07-28 · 修复（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `bom_form_import.py`、`record_service.py`、`cost_bom_import.js`；移除误加的 `supplier_name.py` |
| 变更内容 | 纠正 CL-0185：BOM 批量导入改为匹配 **客户档案**（表内/文件名简称如「大沃」→「苏州大沃工具科技有限公司」）；**不再**匹配供应商档案，工序供应商按 Excel 原文写入；订单 OCR 仍优先 BOM 料号并在客户不一致时提示 |
| 验证 | `test_bom_form_import.test_sheet_customer_short_name_resolved_on_preview`；全量 unittest |
| SOP 同步 | 否 |

### CL-0185 · 2026-07-28 · 修复（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `supplier_name.py`、`bom_form_import.py`、`record_service.py`、`line_service.py`、`field_validation.py`、`app.js`、`cost_bom_import.js` |
| 变更内容 | BOM 批量导入：外发供应商简称（如「大沃」）自动匹配供应商档案全称（如「苏州大沃工具科技有限公司」）；导入 commit 启用供应商校验。订单 OCR：优先按 BOM 料号回填；料号一致但客户不一致时标黄并在提交前询问是否改用 BOM 客户 |
| 验证 | `tests/test_supplier_name.py`、`test_bom_form_import`、`test_order_line_service`；`/api/health` build=`20260728-bom-supplier-match` |
| SOP 同步 | 否 |

### CL-0184 · 2026-07-28 · 优化（C）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `app.js`、`index.html`、`app.py` |
| 变更内容 | 未结订单列表：隐藏接单日期；去掉出货/排产缺口与库存预警列，仅保留「成品库存」一列 |
| 验证 | 未结订单列表列数与展示符合预期；`/api/health` build=`20260728-open-fg-only` |
| SOP 同步 | 否 |

### CL-0183 · 2026-07-28 · 新增（B）

| 字段 | 内容 |
|------|------|
| 涉及模块 | `planning.py`、`app.py`、`app.js`、`style.css`、`_order_sidebar.html` |
| 变更内容 | 未结订单列表绑定成品/半成品库存：`GET /api/lines?view=open` 返回 `finished_qty`、`gap_ship`、`gap_cover`、`stock_warn_level`；列表增列与行色预警（成品不足橙、需排产蓝）；汇总行统计缺口行数；恢复「库存 → 排产对照」页入口 |
| 验证 | `python -m unittest discover -s tests -p "test_*.py"`；未结订单见库存列与预警色；`/api/health` build=`20260728-open-stock-warn` |
| SOP 同步 | 否（列表增强，流程不变） |

### CL-0182 · 2026-07-28 · 新增（C）

- 涉及模块：`inventory/service.py`、`store.py`、`inventory_entry.js/html`、`app.py`、`test_inventory.py`
- 变更内容：**校正库存**支持场内 / 在途 / 返修在途（成品含成品返修在途）；新增 **返修**（FX）与 **返修入库**（FR），半成品场内或成品 → 返修在途 → 恢复库存。
- 验证：`tests/test_inventory.py`；本地 `/inventory/entry`。
- SOP 同步：否。

### CL-0181 · 2026-07-28 · 新增（C）

- 涉及模块：`inventory/service.py`、`inventory_entry.js/html`、`app.py`、`test_inventory.py`
- 变更内容：库存 **跳序出库**（TK 单号）：任意工序场内 → 任意工序在途，可跨道或逆向回补；顺序出库仍限相邻工序。不建欠账表，靠流水记录。
- 验证：`tests/test_inventory.py`；本地 `/inventory/entry` 载入料号 → 跳序出库。
- SOP 同步：否（本地预览）。

### CL-0180 · 2026-07-27 · 优化（C）

- 涉及模块：`cost_entry.html`、`cost_entry.js`、`cost_bom_import.js`、`cost.css`
- 变更内容：BOM 录入页改为与订单录入一致的 **模式切换**（Excel 批量导入 / 手动录入）；批量区复用 upload-card + preview-card 版式。
- 验证：浏览器 `/bom/entry` 切换两种模式并解析 Excel。
- SOP 同步：否。

### CL-0179 · 2026-07-27 · 优化（C）

- 涉及模块：`cost_entry.html`、`cost_bom_import.js`、`cost.css`
- 变更内容：BOM 批量导入 UI 优化——展示文件名、客户匹配、通过/待核/阻断统计、同 Sheet 拆分标记；说明已内置纵表头料号、多料号拆分、工序别名等解析能力（后端 `bom_form_import.py` 已生效）。
- 验证：浏览器打开 `/bom/entry` → 上传 Excel → 解析预览。
- SOP 同步：否。

### CL-0178 · 2026-07-27 · 修复（C）

- 涉及模块：`bom_form_import.py`、`scripts/split_metal_shaft_bom.py`
- 变更内容：同一 Sheet **多产品料号**（换行/`/` 分隔，如怡利「金属转轴」）自动拆成多条 BOM；已拆分误合并记录为 `1A104D0A001-00` / `1A104D0A003-00` 两条。
- 验证：`tests/test_bom_form_import.py`；`python scripts/split_metal_shaft_bom.py`。
- SOP 同步：否。

### CL-0177 · 2026-07-27 · 修复（B）

- 涉及模块：`bom_form_import.py`、`scripts/reimport_bom_audit_batch.py`
- 变更内容：修正威可特 BOM 表 **纵表头** 解析（标签第 3/5 行、数值第 4/6 行）；产品料号读取 **E 列产品料号栏** 而非 Sheet 名/组装区「料号」；已删除并 **重新导入 68 条 BOM**。
- 验证：`tests/test_bom_form_import.py`；`python scripts/reimport_bom_audit_batch.py`。
- SOP 同步：否。

### CL-0176 · 2026-07-27 · 新增（B）

- 涉及模块：`models.py`、`bom_form_import.py`、`customer_name.py`、`cost_store.py`、库存/演示 BOM 编号、`scripts/import_bom_audit_batch.py`
- 变更内容：新增工艺 **铝挤（32，位于制程损耗前）** 并顺延旧 32–36→33–37（含 SQLite 一次性迁移）；按员工确认更新 BOM 工序别名（清洗拉白/拉白/钝化拉白、振动研磨去毛边→去毛边+震研、铆合弹片跳过等）；文件名 **BOM格式** 后缀剥离 + 日月照明/欧菲光/红黑客户映射；批量导入 `data/bom_import_audit/` 六份 BOM。
- 验证：`tests/test_bom_form_import.py`、`tests/test_cost_analysis_service.py`；`python scripts/import_bom_audit_batch.py`。
- SOP 同步：否。

### CL-0175 · 2026-07-26 · 优化（C）

- 涉及模块：`bom_form_import.py`
- 变更内容：BOM 导入支持 **东硕式纵向制程表**（制程:1 + 工序 + 可加工厂商）；料号误读「文件编号/版次」时改用 **sheet 名**（如 HUV9142V1）；新增工序别名（冲切下料、振动研磨、皮膜钝化、全检出货等）。
- 验证：`tests/test_bom_form_import.py`。
- SOP 同步：否。

### CL-0174 · 2026-07-26 · 优化（C）

- 涉及模块：`customer_name.py`、`bom_form_import.py`、`cost_bom_import.js`、`app.py`
- 变更内容：BOM 导入 **从文件名识别客户简称**（如 `东硕BOM.xls`→东硕），匹配客商档案全称（如 `苏州鑫福泰电子科技有限公司-东硕`）；无匹配时提示先建客户。
- 验证：`tests/test_bom_form_import.py`。
- SOP 同步：否。

### CL-0173 · 2026-07-26 · 修复（C）

- 涉及模块：`bom_form_import.py`、`requirements.txt`、`cost_entry.html`、`app.py`
- 变更内容：BOM 导入 **支持旧版 `.xls`**（需 `xlrd 1.2`）；修复仅接受 xlsx 导致无法上传 `.xls` 的问题。
- 验证：`tests/test_bom_form_import.py`。
- SOP 同步：否。

### CL-0172 · 2026-07-26 · 新增（B）

- 涉及模块：`cost_analysis/bom_form_import.py`、`record_service.py`、`cost_entry.html`、`cost_bom_import.js`、`app.py`
- 变更内容：**BOM 表单批量导入**：上传威可特「新产品 BOM 表」Excel（每 sheet 一料号），解析表头 + 产品制程（单价默认 0）；预览分通过/待核/阻断后批量写入。
- 验证：`tests/test_bom_form_import.py`。
- SOP 同步：是。

### CL-0171 · 2026-07-25 · 新增（B）

- 涉及模块：`auth/service.py`、`auth/store.py`、`flask_integration.py`、`users_admin.html/js`、`auth.css`
- 变更内容：用户管理增加 **编辑**（姓名、角色）与 **删除** 员工；`PUT/DELETE /api/users/{id}`；不可删 admin / 当前登录账号。
- 验证：`tests/test_auth.py`。
- SOP 同步：是。

### CL-0170 · 2026-07-25 · 修复（C）

- 涉及模块：`cost_store.py`、`bom_service.py`、`line_service.py`
- 变更内容：撤销 CL-0169 料号前缀匹配；**订单客户料号与 BOM 产品料号须完全一致**（仍保留连字符/空格规范化与 CL-0168 空客户误报修复）。
- 验证：`tests/test_order_line_service.py` 全通过。
- SOP 同步：否。

### CL-0169 · 2026-07-25 · 修复（B）

- 涉及模块：`cost_store.py`、`bom_service.py`、`line_service.py`
- 变更内容：订单 **客户料号** 可匹配 BOM **产品料号** 前缀（如订单 `PL9-12580-10-0A` ↔ BOM `PL9-12580-10-0A-前挡板`）；结合品名/客户消歧。
- 验证：`test_create_line_bom_part_no_with_product_suffix`。
- SOP 同步：否。

### CL-0168 · 2026-07-25 · 修复（B）

- 涉及模块：`cost_store.py`、`bom_service.py`、`tests/test_order_line_service.py`
- 变更内容：订单录入查 BOM 时修复误报「未建档」（BOM 存在但客户名为空时 `get_part_binding` 返回空）；料号匹配增加连字符/空格规范化；错误提示注明须在同一服务器保存 BOM。
- 验证：`tests/test_order_line_service.py` 新增用例。
- SOP 同步：否。

### CL-0167 · 2026-07-25 · 修复（C）

- 涉及模块：`inventory_entry.js`
- 变更内容：点选上方工序站时，下方 **入库工序 / 从工序** 下拉框同步跳到该工序（不再被上一次手动选择覆盖）；**到工序** 自动带出下道。
- 验证：载入料号后点「01 压铸」，出库「从工序」应显示 01 而非上次选的包装。
- SOP 同步：否。

### CL-0166 · 2026-07-25 · 优化（C）

- 涉及模块：`inventory_entry.html`、`inventory_entry.js`
- 变更内容：工序出入库 **登记动作** 下方扣增说明文字移除（界面更简洁）。
- 验证：打开 `/inventory/entry` 载入料号后无灰色提示行。
- SOP 同步：否。

### CL-0165 · 2026-07-25 · 优化（C）

- 涉及模块：`inventory_movements.html`、`inventory_movements.js`
- 变更内容：**出入库流水**总览表与工序出入库 **当日流水** 列格式统一：时间 → 客户 → 料号 → 品名 → 动作 → 工序（路线）→ 数量 → 单号 → 备注 → 操作；移除来源/去向列。
- 验证：打开 `/inventory/movements` 与 `/inventory/entry` 对比列一致。
- SOP 同步：是。

### CL-0164 · 2026-07-25 · 修复（C）

- 涉及模块：`inventory/service.py`、`inventory/store.py`
- 变更内容：历史流水单号 **WG/FC/CP** 在列表/API 展示时统一映射为 **RK/CK**；新单号序号与旧前缀共用当日序号（避免 RK-001 与 WG-003 并存）。
- 验证：`test_legacy_doc_no_display_normalized`。
- SOP 同步：否。

### CL-0163 · 2026-07-25 · 重构（B）

- 涉及模块：`inventory/service.py`、`app.py`、`inventory_entry.html/js`、`inventory_movements.js`、`flask_integration.py`、`payable_service.py`、`tests/test_inventory.py`
- 变更内容：工序出入库统一为 **入库 / 出库** 两种动作（保留 **校正库存**）；**入库** 选择目标工艺（首道加场内、非首道在途→场内、末道→成品）；**出库** 选择从哪道工艺发往下道相邻工艺（成品出库：从→成品）；单号前缀改为 **`RK` 入库 / `CK` 出库**（原 WG/FC/CP 仅历史流水展示仍映射为入库/出库）；旧 API（complete/outsource-*）兼容转发；应付对账同时识别 `inbound` 外发回货。
- 验证：`python -m unittest tests.test_inventory -v`；`/inventory/entry` 载入料号后选入库/出库登记。
- SOP 同步：是。

### CL-0162 · 2026-07-25 · 优化（C）

- 涉及模块：出入库流水、`inventory/service.py`、`inventory_entry.js`、`inventory_movements.js`
- 变更内容：流水表 **工序** 列显示 **编号 + 名称**（如 `01 压铸`）；API 返回 `process_name`。
- 验证：`test_list_movements_filter_on_date`。
- SOP 同步：否。

### CL-0161 · 2026-07-25 · 优化（C）

- 涉及模块：工序出入库 `inventory_entry.html/js`
- 变更内容：移除「当日出入库流水」下方筛选栏；当日流水表去掉 **从/到** 列（动作列已表达业务）；「出入库流水」页改为 **来源/去向** 中文可读格式。
- 验证：工序出入库页当日流水无筛选、无从到列；流水页来源去向可读。
- SOP 同步：是。

### CL-0160 · 2026-07-25 · 优化（B）

- 涉及模块：工序出入库、出入库流水、`inventory/service.py`
- 变更内容：当日/历史流水表列顺序改为 **时间 → 客户名称 → 客户料号 → 产品名称 → 动作…**；工序出入库增加 **客户名称** 载入条件与 **筛选流水**（客户/料号）；流水 API 支持 `customer_name` 模糊筛选。
- 验证：`tests/test_inventory.py`；`/inventory/entry` 筛选流水与列显示。
- SOP 同步：是。

### CL-0159 · 2026-07-25 · 优化（B）

- 涉及模块：工序出入库、出入库流水、`inventory/service.py`
- 变更内容：工序出入库移除绿色 BOM 提示行与「返回总览」；出入库流水表增加 **品名**、**客户** 列（BOM 关联）；移除流水页冗余「出入库登记」按钮。
- 验证：`tests/test_inventory.py`；打开 `/inventory/entry`、`/inventory/movements`。
- SOP 同步：是。

### CL-0158 · 2026-07-25 · 优化（C）

- 涉及模块：库存总览 `inventory.html`、`inventory.js`
- 变更内容：移除筛选栏「写入10料号演示」「出入库登记」「出入库流水」按钮，避免与顶栏库存菜单重复。
- 验证：打开 `/inventory` 筛选栏仅保留查询条件与「查询」。
- SOP 同步：是。

### CL-0157 · 2026-07-25 · 优化（B）

- 涉及模块：库存总览/流水/登记/排产、`inventory_bom_lookup.js`、`cost_store.py`、`app.py`
- 变更内容：总览卡片 **客户名称** 显示在卡片标题右侧（测/实 标签旁）；库存各页搜索栏增加 **自动填充**：料号/品名/客户下拉联想（`GET /api/cost/customers`）；选 BOM 项时互填料号/品名/客户；排产页客户与关键字亦支持下拉。
- 验证：`tests/test_cost_lookup.py`；总览/流水/登记/排产页输入联想。
- SOP 同步：是。

### CL-0156 · 2026-07-25 · 新增（B）

- 涉及模块：库存总览、`inventory/service.py`、`inventory.js/html`、`app.py`
- 变更内容：看板卡片显示 **客户名称**（来自 BOM）；筛选栏增加 **客户名称** 模糊查询（`GET /api/inventory/board?customer_name=`）。
- 验证：`tests/test_inventory.py` 客户筛选；总览页按客户查询。
- SOP 同步：是。

### CL-0155 · 2026-07-25 · 优化（C）

- 涉及模块：工序出入库 `inventory_entry.js`
- 变更内容：移除工序出入库页载入前的静态说明（「点选工序站登记…」「未载入料号…」）；载入成功后继续隐藏 BOM 提示与状态行。
- 验证：载入料号后仅显示工序站卡片与登记区。
- SOP 同步：否。

### CL-0154 · 2026-07-25 · 新增（B）

- 涉及模块：工序出入库、`inventory/service.py`、`inventory_entry.js/html`、`app.py`、审计
- 变更内容：新增 **库存校正**：当余额本身有误（如期初成品 150 实际应为 120）时，点选工序站/成品卡 → **校正库存**，填写 **正确数量**；系统按差额记 `TZ` 流水（`POST /api/inventory/adjust`）。与 **修改流水** 区分：修改仅改单笔登记数量，校正改目标余额。
- 验证：`python -m unittest tests.test_inventory.TestInventoryService.test_adjust_finished_balance` 等；工序出入库页成品 150→120。
- SOP 同步：是（§工序出入库 改错说明）。

### CL-0153 · 2026-07-25 · 优化（B）

- 涉及模块：工序出入库 `inventory_entry.js`、`inventory.css`
- 变更内容：提交登记成功后展示 **「已录入」** 动画（约 1.5 秒），并高亮当日流水新增行；避免成功反馈一闪而过。
- 验证：手动提交登记确认动画与流水高亮。
- SOP 同步：否（交互增强）。

### CL-0152 · 2026-07-25 · 新增（B）

- 涉及模块：工序出入库、`inventory/store.py`、`inventory/service.py`、`inventory_entry.js`、`app.py`
- 变更内容：当日出入库流水增加 **修改**（更正数量/备注，自动回滚并重算库存）；`PUT /api/inventory/movements/{id}`；订单出货与演示流水不可改。
- 验证：`test_inventory.py` 修改数量与拒绝订单出货用例。
- SOP 同步：是。

### CL-0151 · 2026-07-25 · 优化（B）

- 涉及模块：`data-sync-rules.ps1`、`sync-to-cloud.ps1`、`server-merge-update.sh`、`一键同步云端.bat`
- 变更内容：**默认一键同步云端** 时始终推送本地 `data/feishu_config.json` 到服务器（双 Webhook 等通知配置），**不**覆盖订单库与客商 JSON。
- 验证：同步后云端 `/api/feishu/config` 显示 `webhook_count: 2`；飞书测试与操作通知两群均收到。
- SOP 同步：否（RESTORE 云端节补充说明）。

### CL-0150 · 2026-07-25 · 优化（B）

- 涉及模块：`integrations/feishu.py`、`data/feishu_config.json`、`feishu_README.md`
- 变更内容：飞书支持 **多个 Webhook 同时推送**（`webhook_urls` 数组）；本地已配置 2 个机器人；兼容旧 `webhook_url` 单地址。
- 验证：`test_feishu_notify.py` 多 Webhook 用例；`/api/feishu/config` 返回 `webhook_count`。
- SOP 同步：否（配置说明在 feishu_README）。

### CL-0149 · 2026-07-25 · 优化（A）

- 涉及模块：飞书、`flask_integration.py`（审计钩子）、`sync-to-cloud.ps1`、`server-merge-update.sh`、`notify-feishu-deploy.py`
- 变更内容：
  - **云端任意操作**：登录/退出及所有已登记写操作（订单、库存、BOM、客商、送货单、用户管理等）经 **审计钩子统一推送飞书**（含操作人、模块、摘要、IP）；
  - **系统迭代通知**：一键同步云端完成后自动推送 **版本号 + build + CHANGELOG 摘要**（`deploy-info/` 随包下发）；
  - 移除各 API 端点重复飞书调用，避免双份通知。
- 验证：`test_feishu_notify.py`；同步云端后飞书收到「系统更新」；云端登录/出货/BOM 等收到「操作通知」。
- SOP 同步：是。

### CL-0148 · 2026-07-25 · 优化（B）

- 涉及模块：飞书集成（`wkt_events.py`、`feishu.py`、`app.py`）、SOP §五、`data/feishu_README.md`
- 变更内容：飞书通知扩展至 **全模块写操作**：库存出入库、BOM 录入/修改/删除、客户/供应商档案、订单强制结案、撤销出货等；原订单录入/修改/删除/出货/导入保持不变。
- 验证：`test_feishu_notify.py`；手动测试 `/api/feishu/test` 与各模块操作。
- SOP 同步：是。

### CL-0147 · 2026-07-25 · 优化（B）

- 涉及模块：库存导航、`inventory_movements.html`、`inventory_movements.js`、`inventory.html`、`inventory.js`、`app.py`
- 变更内容：将 **出入库流水** 从库存总览拆为独立子模块 **库存 ▾ → 出入库流水**（`/inventory/movements`）；支持料号/品名/日期筛选；总览页仅保留看板。
- 验证：手动打开 `/inventory` 与 `/inventory/movements`；导航高亮正确。
- SOP 同步：是。

### CL-0146 · 2026-07-25 · 优化（B）

- 涉及模块：BOM 查询、`cost_query.html`、`cost_query.js`
- 变更内容：BOM 查询列表增加 **序号** 列；按 **录入时间降序**（最新录入在最前，与后端 `created_at DESC` 一致）。
- 验证：手动 BOM 查询页；`test_cost_records.py` 列表顺序不变。
- SOP 同步：否。

### CL-0145 · 2026-07-25 · 优化（B）

- 涉及模块：客户/供应商档案 store、客商维护列表
- 变更内容：客户与供应商列表按 **录入时间** 降序排列（**最新录入在最前**）；新建档案自动写入 `created_at`；旧档案无时间戳时按 JSON 原顺序靠后。
- 验证：`test_customer_profile.py`、`test_supplier_profile.py` 排序用例。
- SOP 同步：否。

### CL-0144 · 2026-07-25 · 修复（B）

- 涉及模块：`scripts/pull-data-from-cloud.ps1`、`一键从云端拉取数据.bat`
- 变更内容：修复拉取云端数据时 `$remoteArchive` 未定义、SSH 空密码；改用 **Python UTF-8 解压**（避免 Windows tar 中文文件名失败）；打包时排除 `delivery_templates/files/`。
- 验证：运行「一键从云端拉取数据」完成下载与解压。
- SOP 同步：否。

### CL-0143 · 2026-07-25 · 优化（B）

- 涉及模块：客户信息维护、供应商信息维护、`index.html`
- 变更内容：客商列表首列增加 **序号**（筛选后按当前显示顺序 1、2、3…）。
- 验证：手动打开客商维护页确认序号列。
- SOP 同步：否（列展示增强）。

### CL-0142 · 2026-07-25 · 修复（A）

- 涉及模块：`scripts/sync-to-cloud.ps1`、`scripts/data-sync-rules.ps1`、`scripts/server-merge-update.sh`、云端运维 bat
- 变更内容：
  - **默认「一键同步云端」改为仅同步代码**（`test_impl` + `scripts`），**不再上传/覆盖** 云端 `data/`（订单库、供应商、客户、BOM 等以云端为准）；
  - 新增 **一键查询云端数据**、**一键从云端拉取数据**、**一键恢复云端供应商**（从 `data.bak-*` 恢复 `supplier_profiles.json`）；
  - 旧行为「本地 JSON 覆盖云端」改为显式参数 `-WithMasterData`（需手动调用，不再默认）。
- 验证：打包 staging 无 `data/` 目录；`server-merge-update.sh` 在无 staging/data 时跳过 data 合并。
- SOP 同步：已更新 RESTORE 云端数据节。

### CL-0141 · 2026-07-24 · 优化（B）

- 涉及模块：库存总览、`inventory/service.py`、`inventory.js`
- 变更内容：库存总览看板卡片标题除料号外增加 **BOM 品名**；API `GET /api/inventory/board` 返回 `product_name`。
- 验证：`test_inventory.py` 通过。
- SOP 同步：否（展示增强）。

### CL-0140 · 2026-07-24 · 修复（B）

- 涉及模块：客商信息维护、`style.css`
- 变更内容：修复客户/供应商维护页 **添加表单卡片被 flex 拉伸** 导致表头筛选上方大面积留白；表单卡与列表卡改为随内容高度紧凑排列。
- 验证：打开客商信息维护，确认表单与列表表头之间无大块空白。
- SOP 同步：否（纯布局）。

### CL-0139 · 2026-07-24 · 优化（B）

- 涉及模块：BOM 查询、`cost_query.js`、`list-col-filter.js`
- 变更内容：
  - BOM 查询列表表头增加 **▾ 列筛选**（客户、产品、料号、材质、单重、机台、工序数、成本、录入时间）；
  - 支持与顶部关键字查询组合；**清空列筛选** 一键恢复。
- 验证：手动 BOM 查询页列筛选；全量单元测试通过。
- SOP 同步：已更新。

---

### CL-0138 · 2026-07-24 · 优化（B）

- 涉及模块：客户信息维护、供应商信息维护、`delivery-note-admin.js`、`supplier-admin.js`
- 变更内容：
  - 客商列表布局收紧：表格紧贴上方，底部 **清空筛选 / 条数 / 刷新**；
  - **客户、供应商** 均仅 **名称列 ▾** 表头筛选；
  - 新增客户/供应商表单改为 **两排** 横排布局。
- 验证：手动进入客商维护页筛选；全量单元测试通过。
- SOP 同步：已更新。

---

### CL-0137 · 2026-07-24 · 优化（B）

- 涉及模块：BOM 录入/查询、`record_service.py`、`cost_common.js`、`inventory/service.py`
- 变更内容：
  - BOM 录入与编辑时，已选工序下方显示 **工艺顺序** 列表，可用 **↑↓** 调整先后；
  - 顺序写入 `process_prices_json` 的 **`__order__`** 字段；库存工艺路线按此顺序展示；
  - 旧记录无自定义顺序时，仍按工序代码排序（兼容）。
- 验证：`tests/test_cost_records.py::test_custom_process_order_persisted`；全量单元测试。
- SOP 同步：已更新 BOM 录入说明。

---

### CL-0136 · 2026-07-24 · 优化（B）

- 涉及模块：库存总览、工序出入库、`inventory_bom_lookup.js`
- 变更内容：
  - 库存搜索支持 **料号 + 品名** 双字段；
  - 输入时 **BOM 自动联想**（同 BOM 录入数据源）；
  - 选料号自动带出品名，选品名自动带出料号。
- 验证：库存页手动验证联想与查询；全量单元测试通过。
- SOP 同步：已更新库存搜索说明。

---

### CL-0135 · 2026-07-23 · 新增（A）

- 涉及模块：`test_impl/auth/`、登录页、操作记录、用户管理、`app.py`
- 变更内容：
  - **正式登录**：未登录跳转 `/login`；Flask Session + 密码哈希（werkzeug）；
  - 首次无用户时 bootstrap **`admin` / `WKT@2026`**（须改密）；
  - **`audit_log` 表**：自动记录 POST/PUT/DELETE 业务操作（模块、动作、操作人、IP、摘要）；
  - **操作记录页** `/admin/audit`；**用户管理** `/admin/users`（仅 admin）；
  - CLI：`python scripts/create_employee_user.py --username ... --name ... --password ...`
- 验证：`tests/test_auth.py` 3 项；全量 `192` tests OK。
- SOP 同步：已更新登录与审计说明。

---

### CL-0134 · 2026-07-23 · 新增（B）

- 涉及模块：`scripts/sync-to-cloud.ps1`、`scripts/data-sync-rules.ps1`、`scripts/server-merge-update.sh`、`一键全量同步云端.bat`
- 变更内容：
  - 新增 **全量云端同步**：`-FullData` / `一键全量同步云端.bat`；
  - 整包覆盖 `data/`（含 **`wkt_orders.db`**、`delivery_notes/`）；服务器先停进程、备份旧 `data/` 再覆盖；
  - 原 `一键同步云端.bat` 仍保留「只同步代码+主数据、不动订单库」行为。
- 验证：全量同步后 `/api/health` 的 `line_count`、`build` 与本地一致。
- SOP 同步：否（运维脚本）。

---

### CL-0133 · 2026-07-23 · 新增（A）

- 涉及模块：`test_impl/demo/sop_seed.py`、`一键写入SOP测试数据.bat`、`is_demo` 字段
- 变更内容：
  - **一键写入 SOP 测试数据**：清空 SQLite 业务表（订单/BOM/库存/出货），**保留** `customer_profiles.json` / `supplier_profiles.json`；
  - 默认每模块 **15 条**（10~20 可调）；料号 `TST-PL-*`、订单 `TST-PO-*`、账期后缀 **【测试数据】**；
  - 订单/BOM 增加 **`is_demo` + 列表「测」徽标**；库存沿用 `inventory_part_tags`；
  - 分布：5 未结 / 5 部分出货 / 3 已结案 / 2 强制结案；含出货明细、应收、外发回货应付。
- 验证：`tests/test_sop_seed.py`；`python scripts/seed_sop_test_data.py`。
- SOP 同步：已更新。

---

### CL-0132 · 2026-07-23 · 文档（B）

- 涉及模块：`docs/SOP/员工培训手册-图文版.pdf`、`scripts/export_sop_pdf.py`
- 变更内容：培训手册导出 **PDF**（A4、嵌入全部配图、页眉页脚页码）；脚本 `export_sop_pdf.py` 可重复生成。
- 验证：`docs/SOP/员工培训手册-图文版.pdf` 约 5MB，可正常打开。
- SOP 同步：Markdown 手册已加 PDF 链接。

---

### CL-0131 · 2026-07-23 · 文档（B）

- 涉及模块：`docs/SOP/images/`、截屏脚本、`data/sop_samples/sample_po.pdf`
- 变更内容：SOP 配图升级为 **Windows 实拍**（资源管理器 bat、服务 PowerShell 窗口）+ **真实 OCR 预览**（自动生成样例 PO 并跑识别截屏）；新增 `capture_desktop_sop_shots.py`、`create_sop_sample_po.py`、`capture_ocr_preview_only.py`。
- 验证：`03-ocr-preview.png` 含识别表 2 行；`00-start-bat.png` / `00-cmd-window.png` 为桌面窗口截屏。
- SOP 同步：`images/README.md` 已更新。

---

### CL-0130 · 2026-07-23 · 文档（A）

- 涉及模块：`docs/SOP/`
- 变更内容：新增 **《员工培训手册-图文版》**（全模块手把手步骤、注意事项、mermaid 流程、正式测试检查表）；`docs/SOP/images/README.md` 配图清单；简明 SOP 增加详版入口。
- 验证：手册覆盖订单/BOM/库存/对账/客商/飞书；与当前顶栏菜单一致。
- SOP 同步：已更新。

---

### CL-0129 · 2026-07-23 · 优化（A）

- 涉及模块：应收/应付到期视图、`due-outlook` API
- 变更内容：去掉「随后到期」；改为自 **本月起重连续 6 个月** 收款/付款到期滚动展示（应付逻辑对称）。
- 验证：`due_outlook` 返回 `months` 长度 6；10 月出货数据出现在对应月份段。
- SOP 同步：已更新。

---

### CL-0128 · 2026-07-23 · 优化（A）

- 涉及模块：应收/应付页、`due-outlook` API
- 变更内容：打开 **应收/应付** 默认展示 **本月 + 下月** 到期客户/供应商及各自合计；仍可点「查看明细」钻取。本月/下月无数据时提示原因并展示 **随后到期** 月份（如有）。
- 验证：`/api/reconciliation/due-outlook`、`/api/payable/due-outlook`；`test_payable_due_bucket_by_month`。
- SOP 同步：已更新。

---

### CL-0127 · 2026-07-23 · 新增（A）

- 涉及模块：对账导航、`PayableService`、`/api/payable/*`、首页子模块
- 变更内容：
  - 顶栏 **对账 ▾** → **应收**（原出货对账）/ **应付**（外发回货×供应商）；
  - 应付金额 = 回货数量 × BOM 工序单价；结算月按供应商对账周期；应付日按供应商账期；
  - 应付支持供应商×结算月汇总、明细钻取、收货日期起止筛选。
- 验证：`tests/test_payable.py`；导航切换应收/应付；有回货流水时应付表有数据。
- SOP 同步：已更新。

---

### CL-0126 · 2026-07-22 · 优化（A）

- 涉及模块：工序出入库页布局
- 变更内容：收紧上方留白（缩短说明、空状态改左对齐一行、压缩区块间距），流水区更靠上。
- 验证：打开 `/inventory/entry` 未载入料号时，当日流水紧接在载入区下方，无大块空白。
- SOP 同步：无需（纯布局）。

---

### CL-0125 · 2026-07-22 · 优化（A）

- 涉及模块：工序出入库页、`GET /api/inventory/movements`
- 变更内容：
  - 流水区改为 **当日出入库流水**：打开即显示今天全部料号（含料号列）；
  - 载入料号仅用于工序站登记，不再要求先载入才看流水；
  - API 支持 `on_date=YYYY-MM-DD`（按本机时区日历日）。
- 验证：`/inventory/entry` 无料号也可看到当日流水；`test_list_movements_filter_on_date` 通过。
- SOP 同步：已更新。

---

### CL-0124 · 2026-07-22 · 优化（A）

- 涉及模块：导航、库存总览/工序出入库、`inventory_part_tags`
- 变更内容：
  - 导航 **排产对照** 菜单（`/inventory/planning` 重定向至总览）；
  - 料号增加数据标注：**测**（演示/测试）/ **实**（正式）；写入演示库存自动标测；已有演示流水启动时回填。
- 验证：导航无排产对照；总览卡片显示测/实；`test_seed_board_demo_ten_parts` 断言 `data_tag=测`。
- SOP 同步：已更新。

---

### CL-0123 · 2026-07-22 · 优化（A）

- 涉及模块：工序出入库登记表单
- 变更内容：登记区去掉「单号」输入（避免切换工序时残留旧单号误解）；单号仍后台自动生成，提交成功提示与流水中可见。
- 验证：打开 `/inventory/entry` 登记区无单号栏；提交后提示含 `FC-…` 等单号。
- SOP 同步：无需。

---

### CL-0122 · 2026-07-22 · 新增（A）

- 涉及模块：库存进出单号、`InventoryStore.next_movement_doc_no`、工序出入库登记
- 变更内容：
  - 未填单号时自动生成：`WG`完工转入 / `FC`发出 / `RK`回货入库 / `CP`成品出货 + `YYYYMMDD` + 当日序号；
  - 手工传入 `doc_no` 仍保留；登记页单号只读，提交后显示生成结果。
- 验证：`test_auto_doc_no_by_action`；工序出入库提交后看提示与流水单号。
- SOP 同步：已补充单号规则。

---

### CL-0121 · 2026-07-22 · 优化（B）

- 涉及模块：`outsource_receive`、工序出入库文案、演示流水、测试
- 变更内容：
  - **回货入库**改为本道在途 → **本道场内**（不再进下一道）；
  - 发下一道：对本道场内点下道「发出」（本道场内↓、下道在途↑）；
  - 动作文案：发出 / 回货入库；演示流与 SOP/data-model 同步。
- 验证：`test_receive_goes_to_same_process_inhouse`、`test_send_next_from_same_process_inhouse`、全量 unittest。
- SOP 同步：已更新 §工序出入库。

---

### CL-0120 · 2026-07-22 · 优化（A）

- 涉及模块：工序出入库登记区、`inventory_entry.js/html/css`
- 变更内容：
  - 登记区改为 **横向**：数量/供应商/单号/备注与提交同一行；
  - 在途发出/回货时：BOM 已填供应商则只读默认；未填则下拉选客商档案供应商；
  - 修复 `hidden` 被 CSS `display:flex` 顶掉导致「完工转入」误显供应商。
- 验证：点场内工序应无供应商；点外发工序有 BOM 供应商则只读，无则下拉可选。
- SOP 同步：无需（交互优化）。

---

### CL-0119 · 2026-07-21 · 优化（A）

- 涉及模块：工序出入库页、排产对照 UI、导航
- 变更内容：
  - **出入库登记**改为按工序站卡片操作：载入料号后显示场内/在途/成品余额，点选工序再选「完工转入 / 在途发出 / 在途回货 / 成品出货」，并展示扣增说明与本料号流水；
  - 暂缓订单绑定：排产页隐藏「生成补产单」与补产单列表（API 保留）；
  - 导航文案改为「工序出入库」。
- 验证：打开 `/inventory/entry` 载入演示料号，点外发工序发出并看流水刷新；全量 unittest。
- SOP 同步：已更新 §库存。

---

### CL-0118 · 2026-07-21 · 新增（B）

- 涉及模块：库存总览成品框、补产单、`production_replenish_orders`、订单出货扣成品仓
- 变更内容：
  - 总览工序格旁增加 **成品库存** 方框，去掉右上角「成品可出货」；
  - **补产单**：排产对照可生成（单号 `BC-YYYYMMDD-序号`），可绑定销售订单号/订单行；列表展示；一期不自动增减库存；
  - **订单出货**自动扣成品仓；不足则拒绝出货并回滚已出货数量。
- 验证：`tests/test_replenish_ship.py`；`/inventory` 看成品框；`/inventory/planning` 生成补产单；有成品库存后再出货。
- SOP 同步：已更新 §库存。

---

### CL-0117 · 2026-07-21 · 优化（A）

- 涉及模块：库存总览/出入库/排产对照文案、`ACTION_LABELS`、`inventory.js`
- 变更内容：
  - 库存状态展示 **外发 → 在途**；动作 **在途出库 / 在途回货**（库内状态码仍为 `outsource`）；
  - 总览工序卡在途>0 时高亮并显示「待回货」，便于跟催回场。
- 验证：打开 `/inventory` 看「在途」「待回货」；`/inventory/entry` 动作下拉文案；全量 unittest。
- SOP 同步：已更新 §库存。

---

### CL-0116 · 2026-07-21 · 优化（A）

- 涉及模块：库存总览演示、`InventoryService.seed_board_demo`、`/api/inventory/seed-board-demo`
- 变更内容：
  - 总览「写入10料号演示」：从订单挑约 10 个料号建 BOM（若缺，工艺轮换乱填）并写入各工序场内/外发/成品库存；
  - 默认查询改为留空查全部，便于一次看到多料号看板。
- 验证：`test_seed_board_demo_ten_parts`；打开 `/inventory` 点「写入10料号演示」。
- SOP 同步：已更新 §库存总览。

---

### CL-0115 · 2026-07-21 · 新增（B）

- 涉及模块：排产对照、`inventory/planning.py`、`/inventory/planning`、`/api/inventory/planning*`、导航
- 变更内容：
  - **排产对照**只读页：未结订单**一行一条**对照成品/半成品库存；
  - 缺口出货（仅成品）、缺口覆盖（成品+半成品）、建议补量；工序明细可展开；
  - 「写入排产演示」：PLAN-A/B/C 各需求 1000、可用库存约 500/600/700。
- 验证：`tests/test_planning.py`；打开 `/inventory/planning` 点「写入排产演示」。
- SOP 同步：已增加 §排产对照。

---

### CL-0114 · 2026-07-20 · 新增（B）

- 涉及模块：库存、`inventory/*`、`/inventory`、`/inventory/entry`、`/api/inventory/*`、导航
- 变更内容：
  - 独立 **库存** 模块：按 BOM 工序监控半成品（场内/外发）与成品；
  - 四种动作：**完工入库**、**外发出库**、**外发回货（进下一道）**、**成品出货（手工）**；
  - 库存总览看板 + 流水；「写入演示数据」一键生成示例流水；
  - SQLite：`inventory_balances`、`inventory_movements`。
- 验证：`tests/test_inventory.py`；打开 `/inventory` 点「写入演示数据」。
- SOP 同步：已增加 §库存。

---

### CL-0113 · 2026-07-20 · 撤销（C）

- 涉及模块：工序在制品 WIP（试跑）
- 变更内容：**撤销** CL-0113 方案 A MVP（在制品查询 / 出入库录入 / `wip_*` 表与 API）；库存方案待重新设计后再做。代码与导航已移除；若本地库曾建表，可手动 `DROP TABLE wip_balances; DROP TABLE wip_movements;`。
- 验证：相关路由/文件已删除；原测试套件不再包含 `test_wip`。
- SOP 同步：已去掉 §4.4 在制品试跑说明。

---

### CL-0112 · 2026-07-20 · 优化（A）

- 涉及模块：BOM 查询表格、`cost_query.html`、`cost_query.js`、`style.css`
- 变更内容：BOM 查询列表对齐全局 `list-table` 样式（列宽、字体、间距、斑马纹、操作列）；料号列等宽字体；文本溢出悬停提示。
- 验证：打开 `/bom/query` 与订单明细表对比字体/表头/行高一致。
- SOP 同步：无需。

---

### CL-0111 · 2026-07-20 · 优化（A）

- 涉及模块：BOM 录入/查询工序供应商、`cost_common.js`、`cost.css`、`record_service`、`models`
- 变更内容：
  - 工序供应商改为 **可搜索下拉**（输入关键字过滤）；
  - 选项列表固定增加 **「场内自制」**（无需在供应商档案中建档）；后端校验同步放行该值；
  - 修复 `cost_common.js` 笔误（`.search.addEventListener`）导致脚本无法加载、工序网格空白。
- 验证：`node --check cost_common.js`；`test_accept_inhouse_supplier_label`；BOM 录入页应显示完整工序卡片。
- SOP 同步：无需（交互增强，流程不变）。

---

### CL-0110 · 2026-07-17 · 重构（B）

- 涉及模块：BOM 主数据、`bom_service`、`line_service`、`cost_store`、`record_service`、`lookup_service`、导航、`/bom/*`、`/api/bom/lookup`、`app.js`、`cost_entry`/`cost_query`、测试
- 变更内容：
  - 顶部 **「成本分析」** 更名为 **「BOM分析」**，子菜单 **BOM录入** / **BOM查询**（原 `/cost/*` 重定向至 `/bom/*`）；
  - **料号主数据**以 `cost_records`（BOM）为权威来源，不再从订单行反查料号绑定；
  - 订单录入填写 **客户料号** 时调用 `GET /api/bom/lookup` 校验并回填品名/单重/材质；未建档则提示先到 **BOM录入** 维护；
  - 订单保存/导入时若带客户料号，须 BOM 中存在且客户一致（支持客户简称与 profile 全称匹配，如「怡利」↔ 档案全称）；
  - 手工「新增料号」入口改为引导至 BOM录入；`/api/health` build=`20260717-bom-master`。
- 验证：`python -m unittest discover -s tests -p "test_*.py"`（168 项通过）。
- SOP 同步：已更新 §二导航、§三（料号/BOM 约束）、§四 BOM 分析；并补全 CL-0108 遗留的录入/查询说明。

---

### CL-0109 · 2026-07-16 · 新增/优化（B）

- 涉及模块：云端同步、客户/供应商档案、对账周期、成本录入 UI、`customer_name`、送货单、Git 脚本
- 变更内容：
  - **云端同步**：`scripts/sync-to-cloud.ps1`、`scripts/server-merge-update.sh`、根目录「同步云端.bat」；同步 `data/`（除 `*.db`、`delivery_notes/`）及配置；
  - **供应商信息维护**：`data/supplier_profiles.json` 与维护页；工序外协供应商下拉联动；
  - **客户档案补全**：批量导入/更新 `customer_profiles.json`；**对账周期** 扩展多种口径（自然月、21～20、26～25、22～21、16～15 等）；
  - **客户名称规范化**：全角/半角括号等同视为同一客户（修复「怡利」等重复建档问题）；
  - **成本录入/查询** UI 与 `record_service` 增强（工序卡片、编辑体验）；送货单 `wkt_document` 小修。
- 验证：单元测试 + 云端同步脚本 dry-run；客户档案对账周期字段可在维护页保存。
- SOP 同步：部分（对账周期见 §3.5.2）；完整录入流程待 CL-0110 一并补全。

---

### CL-0108 · 2026-07-11 · 新增（B）

- 涉及模块：成本分析、客商信息维护、客户档案、对账周期、订单料号、`cost_entry`/`cost_query`、导航
- 变更内容：
  - **成本分析**拆为 **成本录入** + **成本查询**（SQLite 持久化、编辑/删除、料号联想与单重回填）；
  - **客商信息维护**下拉：**客户信息维护** + **供应商信息维护**；
  - 客户 **对账周期** 改为二选一（自然月 / 21日～次月20日），已有客户默认未设置；
  - 供应商默认 21日～次月20日；工艺选择卡片对齐优化；AI 助手入口暂隐藏。
- 验证：`scripts/verify.ps1` 单元测试通过。
- SOP 同步：待后续补全（**CL-0109 / CL-0110 已补写 SOP §二、§三、§四**）。

---

### CL-0107 · 2026-05-30 · 修复（A）

- 涉及模块：专用 Excel 送货单、`delivery_note/service.py`
- 变更内容：恢复 **占位符自动填入**；出货/预览时用 `{{字段}}` 替换订单数据后再打开 Excel；合并出货汇总订单号与数量。
- 验证：`tests/test_delivery_note.py`；专用客户预览下载应含已填示例值。
- SOP 同步：已更新 §3.5.2 占位符说明。

---

### CL-0106 · 2026-05-30 · 优化（A）

- 涉及模块：专用 Excel 出货、`custom_excel_attachment.py`、`app.js`
- 变更内容：专用模板出货时 **本地直接打开 Excel**（`os.startfile`）；用户保存后 **自动写入出货明细附件**（`data/delivery_notes/attachments/` + 后台监听）。
- 验证：专用客户合并出货 → 确认 → Excel 打开 → 保存 → 出货明细可打开附件。
- SOP 同步：已更新 §3.5.2。

---

### CL-0105 · 2026-05-30 · 优化（A）

- 涉及模块：专用送货单流程、`delivery_note/service.py`、`app.js`、`delivery-note-admin.js`、SOP
- 变更内容：**专用 Excel 送货单简化为手动填写**：客户信息维护中**直接上传**模板；出货时**自动打开空白模板**（不再自动填占位符）；新增 `upload-for-customer`、`/raw` 接口。
- 验证：`python -m unittest discover -s tests -p "test_*.py"`；专用客户上传模板后出货应打开 Excel。
- SOP 同步：已更新 §3.5.2 专用模板说明。

---

### CL-0104 · 2026-05-30 · 优化（A）

- 涉及模块：客户信息维护（原送货单维护）、`customer_profile`、`delivery-note-admin.js`
- 变更内容：模块更名为 **客户信息维护**；新增 **新客户录入** 表单；**送货单改为可选项**（不使用 / 威可特统一模板 / 专用模板）；档案增加 `delivery_enabled` 字段。
- 验证：`python -m unittest discover -s tests -p "test_*.py"`；浏览器进入 `/#delivery` 新增客户并保存送货单选项。
- SOP 同步：已更新 §2 导航说明、§3.5.2。

---

### CL-0103 · 2026-05-30 · 重构（B）
- 涉及模块：`_order_sidebar.html`（顶栏）、`index.html`、`cost_analysis.html`、`style.css`、`cost.css`、`app.js`、`delivery-note-admin.js`、SOP、`docs/RESTORE.md`、`snapshots/ui-baseline-20260530/`
- 变更内容：**UI 架构基线**——左侧栏改为 **顶部导航**；订单管理 **下拉子菜单**；模块 **标题+说明移至页脚**；成本分析 **全宽布局**；客户信息维护已并入送货单维护（见 CL-0102 前后会话）。
- 验证：`python -m unittest discover -s tests -p "test_*.py"` → 103/103；顶栏下拉、页脚文案随子模块切换、成本页铺满。
- SOP 同步：已更新第二节「界面长什么样」。
- Git：tag `ui-baseline-20260530`；回退见 `docs/RESTORE.md`。

### CL-0102 · 2026-05-30 · 新增（B）
- 涉及模块：`customer_profile/`、`/api/customer-profiles`、客户维护子菜单、`customer-info-admin.js`、SOP
- 变更内容：**客户维护 → 客户信息维护**：按客户保存公司全称、地址、联系人、电话、邮箱、账期、对账周期。
- 验证：`tests/test_customer_profile.py`；`/#customerInfo` 编辑保存。
- SOP 同步：已更新。

### CL-0101 · 2026-05-30 · 优化（C）
- 涉及模块：`reconciliation/service.py`、`/api/reconciliation/customer-months`、`app.js`、`index.html`、SOP
- 变更内容：对账默认 **客户×收款月份应收汇总**；点 **查看明细** 钻取该月出货对账行，**返回汇总** 回到汇总表。
- 验证：对账页汇总 → 查看明细 → 返回汇总。
- SOP 同步：已更新。

### CL-0100 · 2026-05-30 · 优化（C）
- 涉及模块：`reconciliation/service.py`、`app.js`、`style.css`、SOP
- 变更内容：对账列表 **按客户分组** 展示（应收金额大的客户优先）；每组末尾 **【小计】** 行汇总行数、出货数量与金额。
- 验证：对账页查看多客户数据是否分组+小计行。
- SOP 同步：已更新。

### CL-0099 · 2026-05-30 · 优化（C）
- 涉及模块：`reconciliation/service.py`、`app.js`、`index.html`、SOP、`tests/test_reconciliation.py`
- 变更内容：对账列重排为 **客户→出货时间→订单→料号→数量→单价→金额→出货单号→应收日期→收款时间**；**应付日期/应付月** 改为 **应收日期/收款时间**；同客户+出货时间+订单+料号+单价+出货单号 **合并汇总** 数量与金额。
- 验证：`tests/test_reconciliation.py`；对账页 Ctrl+F5 查看列顺序与合并行。
- SOP 同步：已更新。

### CL-0098 · 2026-05-30 · 新增（B）
- 涉及模块：`reconciliation/`、`line_store`、`/api/reconciliation/*`、对账子菜单、`app.js`、SOP、`data-model.md`
- 变更内容：**对账**子模块：基于出货明细按默认 **月结90天·每月25日付款** 计算应付日与金额；支持应付月/出货月筛选与客户汇总。
- 验证：`tests/test_reconciliation.py`；侧栏「对账」查看明细与合计。
- SOP 同步：已更新。

### CL-0097 · 2026-05-30 · 优化（C）
- 涉及模块：`style.css`
- 变更内容：当日高亮（淡紫）底色略加深，左侧紫条更明显。
- 验证：Ctrl+F5 查看订单/出货列表当日行紫色背景。
- SOP 同步：无需。

### CL-0096 · 2026-05-30 · 优化（C）
- 涉及模块：`_order_sidebar.html`
- 变更内容：侧栏 **AI 数据助手** 移至最底部（成本分析之下）。
- 验证：侧栏顺序为订单管理 → 成本分析 → AI 数据助手。
- SOP 同步：无需。

### CL-0095 · 2026-05-30 · 优化（C）
- 涉及模块：侧栏 `_order_sidebar.html`、`_ai_assistant_panel.html`、`app.js`、`ai-assistant.js`、`style.css`、SOP
- 变更内容：AI 数据助手并入左侧 **业务模块**（与成本分析同级），移除右下角浮层；路由 `/#ai`。
- 验证：侧栏点「AI 数据助手」进入主内容区聊天；成本页侧栏可跳转 `/#ai`。
- SOP 同步：已更新。

### CL-0094 · 2026-05-30 · 新增（B）
- 涉及模块：`ai_memory.py`、`db_assistant.py`、`/api/ai/memory`、`ai-assistant` UI、`data/ai_assistant_memory.example.json`、SOP
- 变更内容：**业务记忆** 持久化到 `data/ai_assistant_memory.json`；支持「记住：…」快捷写入与面板编辑；每次查询自动注入记忆。
- 验证：`tests/test_ai_memory.py`；保存后重启服务再问相关话术应遵循规则。
- SOP 同步：已更新。

### CL-0093 · 2026-05-30 · 修复（C）
- 涉及模块：`db_assistant.py`
- 变更内容：AI 查询注入 **数据快照**（当前日期、出货按月汇总、日期范围）；修正模型默认查 **2024 年** 导致结果为 0；明确按月出货用 `shipped_at`。
- 验证：问「6月份出货」应命中 2026-06 数据；5 月无出货时如实说明。
- SOP 同步：无需。

### CL-0092 · 2026-05-30 · 修复（C）
- 涉及模块：`deepseek_client.py`、`ai-assistant.js`、`style.css`
- 变更内容：DeepSeek 请求增加 **自动重试**（最多 3 次）、`Connection: close`、超时 120s；AI 面板失败时可点 **重试**；缓解 WinError 10054 断连。
- 验证：模拟多轮对话 `DatabaseAssistant.ask`；断网恢复后重试成功。
- SOP 同步：无需。

### CL-0091 · 2026-05-30 · 新增（B）
- 涉及模块：`integrations/deepseek_client.py`、`db_assistant.py`、Web `/api/ai/*`、全局 AI 浮层、`config/secrets.example.json`、SOP
- 变更内容：接入 **DeepSeek AI 数据助手**（右下角浮层），支持自然语言只读查询 SQLite（订单行、出货、客户等）；密钥沿用 `config/secrets.local.json` / `DEEPSEEK_API_KEY`。
- 验证：`tests/test_db_assistant.py`；浏览器打开 AI 面板提问；`/api/health` 含 `ai_db_assistant`。
- SOP 同步：已更新。

### CL-0090 · 2026-05-30 · 优化（C）
- 涉及模块：侧栏 `_order_sidebar.html`、`style.css`、`app.js`
- 变更内容：**结案**、**维护** 改为可展开分组（默认收起，点击后显示子菜单）；进入子页面时自动展开对应分组。
- 验证：浏览器 Ctrl+F5；点击「结案」「维护」展开/收起；进入正常结案/强制结案/送货单维护时自动展开。
- SOP 同步：无需（纯 UI）。

### CL-0089 · 2026-05-30 · 优化（C）
- 涉及模块：侧栏 `_order_sidebar.html`、`_nav_icons.html`、`style.css`
- 变更内容：侧栏导航由单字汉字图标改为 SVG 线框图标（订单录入/明细/出货/未结/结案/送货单/成本分析等）。
- 验证：浏览器 Ctrl+F5 刷新，侧栏各子项与模块头显示图标且选中态颜色正常。
- SOP 同步：无需（纯 UI）。

### CL-0088 · 2026-05-30 · 新增（B）
- 涉及模块：正常/强制结案拆分、`closure_type`、`force-close` API、`app.js`、侧栏、`SOP`、`data-model.md`
- 变更内容：结案拆为 **正常结案**（出货清零）与 **强制结案**；未结订单增加 **结案** 按钮（强制结案，不记出货、不纳入对账）。
- 验证：`tests/test_order_line_service.py` 中 `test_force_close_line`；浏览器验证两个结案子菜单与未结「结案」。
- SOP 同步：已更新。

### CL-0087 · 2026-05-30 · 优化（C）
- 涉及模块：出货明细列表（`app.js`）
- 变更内容：出货明细表增加 **客户料号** 列（数据已由 API 返回，仅补前端展示）。
- 验证：打开「出货明细」可见客户料号列。
- SOP 同步：不涉及。

### CL-0086 · 2026-05-30 · 新增（C）
- 涉及模块：未结订单列表（`app.js`、`style.css`、`SOP`）
- 变更内容：未结订单按 **客户交期** 预警：剩余 ≤10 天黄色、已到/超过交期仍未出完红色；可与当日紫色高亮叠加。
- 验证：未结列表中调整交期日期观察黄/红行。
- SOP 同步：已更新 §3.5.1。

### CL-0085 · 2026-05-30 · 优化（C）
- 涉及模块：`style.css`、`SOP`
- 变更内容：当日行高亮由深绿改为 **紫色**（`#6d28d9`）。
- 验证：浏览器查看今日记录为紫色高亮。
- SOP 同步：已更新 §3.5。

### CL-0084 · 2026-05-30 · 优化（C）
- 涉及模块：结案列表排序、`style.css`、`app.js`、`line_store`、`SOP`
- 变更内容：结案订单按 **最后一次出货时间** 降序（无出货记录则按录入时间）；当日高亮改为 **深绿色**。
- 验证：结案列表最近出货在最上；今日行深绿高亮。
- SOP 同步：已更新 §3.5。

### CL-0083 · 2026-05-30 · 优化（C）
- 涉及模块：订单列表（`app.js`、`style.css`、`SOP`）
- 变更内容：订单明细/未结/出货明细/结案列表对 **当日** 记录整行淡绿高亮（本地日历日），次日 0 点后自动熄灭；午夜自动刷新列表。
- 验证：浏览器查看各列表，当日录入/出货行高亮；改系统日期或次日打开后不再高亮。
- SOP 同步：已更新 §3.5。

### CL-0082 · 2026-05-30 · 新增（B）
- 涉及模块：未结订单合并出货、`wkt_document`、`line_service`、`app.py`、`app.js`、`SOP`
- 变更内容：未结订单支持勾选同一客户多条料号 **合并出货**，共用一张送货单（多行明细、一个送货单号）；出货明细仍按料号各一条记录，补打任一条「送货单」内容一致。
- 验证：`python tests/test_batch_ship.py`；未结列表勾选同客户 ≥2 条 →「合并出货」→ 确认后打开多行送货单。
- SOP 同步：已更新 §3.5.1。

### CL-0081 · 2026-05-30 · 新增（B）
- 涉及模块：结案订单列表、`wkt_document`、`line_store`、`app.js`、`data-model.md`
- 变更内容：结案订单列表增加「出货时间」「出货单号」列（取自该行最后一次出货登记）；送货单号末 4 位改为**自然月内**从 0001 递增（每月 1 日归零），格式仍为 `{前缀}{YYYYMMDD}{序号4位}`。
- 验证：`python -m unittest tests.test_wkt_delivery_document`；浏览器打开「结案订单」可见新列；出货后单号按月递增。
- SOP 同步：不涉及。

### CL-0080 · 2026-05-30 · 优化（C）
- 涉及模块：订单列表（`app.js`、`style.css`、`index.html`、`app.py`）
- 变更内容：悬停高亮改为**整行**淡绿色（去掉列高亮）；新录入/超期行悬停时叠加绿色。
- 验证：浏览器在列表中移动鼠标，当前行整行变绿。
- SOP 同步：不涉及。

### CL-0079 · 2026-05-30 · 优化（C）
- 涉及模块：订单列表（`app.js`、`style.css`、`index.html`、`app.py`）
- 变更内容：列表鼠标悬停某一列时，该列整列（表头+各行）淡绿色高亮，便于横向对照阅读。
- 验证：浏览器在订单四列表中移动鼠标，整列高亮跟随。
- SOP 同步：不涉及。

### CL-0078 · 2026-05-30 · 优化（C）
- 涉及模块：订单明细列表（`app.js`、`index.html`、`app.py`）
- 变更内容：「录入时间」列仅显示日期（YYYY-MM-DD），不显示时分；出货明细「出货时间」仍保留时分。
- 验证：浏览器打开订单明细，录入时间列为日期格式。
- SOP 同步：不涉及。

### CL-0077 · 2026-05-30 · 修复（C）
- 涉及模块：订单列表最后一列（`app.js`、`style.css`、`index.html`、`app.py`）
- 变更内容：操作/送货单列去掉 `td` 的 flex 布局（避免破坏表格列宽）；列宽仅由 colgroup 控制；表头与单元格 padding 统一；列宽百分比凑整为 100%。
- 验证：四模块最后一列表头与按钮列右缘对齐一致。
- SOP 同步：不涉及。

### CL-0076 · 2026-05-30 · 修复（C）
- 涉及模块：订单四列表（`app.js`、`style.css`、`index.html`、`app.py`）
- 变更内容：撤销 spacer/跨表列宽对齐；四模块统一表头/单元格 padding、行高与对齐规则；各表列宽仅在本表内按权重铺满 100%；加大品名/订单号列权重减少截断。
- 验证：切换四列表，样式一致、无大块空白、无底栏横向滚动条。
- SOP 同步：不涉及。

### CL-0075 · 2026-05-30 · 修复（C）
- 涉及模块：订单四列表（`app.js`、`style.css`、`index.html`、`app.py`）
- 变更内容：列宽改为按**字段名**与订单明细同一标尺折算；出货表不足列用 spacer 占位，共有列（客户/订单号/品名等）像素宽一致；统一表头行高与 `border-collapse`。
- 验证：对比订单明细与出货明细同行「客户」「订单号」列宽一致；表头与首行无异常空隙。
- SOP 同步：不涉及。

### CL-0074 · 2026-05-30 · 优化（C）
- 涉及模块：订单四列表（`app.js`、`style.css`、`index.html`、`app.py`）
- 变更内容：去掉列 `min-width` 与表宽撑开，列宽按权重归一化至 100%；序号/操作列统一 2.5%/5.5%；四模块同 padding、表格铺满一屏、无横向滚动条。
- 验证：切换订单明细/出货/未结/结案，表格宽度与行距一致且无需底栏横向拖动。
- SOP 同步：不涉及。

### CL-0073 · 2026-05-30 · 优化（C）
- 涉及模块：订单列表 UI（`style.css`、`app.js`、`index.html`、`app.py`）
- 变更内容：全局列表间距变量（`--wkt-list-*`），对齐出货明细图2：单元格 padding、列最小宽 6.5rem、表宽按列数撑开；出货表补序号列宽。
- 验证：订单明细 / 结案 / 出货明细行高与列间距目视一致。
- SOP 同步：不涉及。

### CL-0072 · 2026-05-30 · 优化（C）
- 涉及模块：订单列表（`app.js`、`style.css`、`index.html`、`app.py`）
- 变更内容：订单明细 / 结案订单等宽表按出货明细同列像素宽推算 `min-width`，列表区恢复横向滚动，列间距与出货明细一致。
- 验证：切换订单明细、结案订单、出货明细对比列宽与单元格留白。
- SOP 同步：不涉及。

### CL-0071 · 2026-05-30 · 优化（C）
- 涉及模块：侧栏（`_order_sidebar.html`、`style.css`、`index.html`、`cost_analysis.html`、`app.py`）
- 变更内容：撤销浮层菜单方案，恢复**窄栏 + 点「订」展宽侧栏**交互；保留图标对齐与无宽度动画优化。
- 验证：进入子模块后侧栏收窄；点「订」展开完整菜单；切换子模块后再次收窄。
- SOP 同步：不涉及。

### CL-0070 · 2026-05-30 · 优化（C）
- 涉及模块：侧栏（`_order_sidebar.html`、`style.css`、`index.html`、`cost_analysis.html`、`app.py`）
- 变更内容：窄栏改为**固定宽度 + 浮层菜单**——点「订」在侧栏右侧弹出子模块面板，侧栏不再展宽；点遮罩、Esc 或选子模块后关闭。
- 验证：桌面端进入子模块后点「订」弹出菜单并切换模块；侧栏宽度保持不变。
- SOP 同步：不涉及。

### CL-0069 · 2026-05-30 · 优化（C）
- 涉及模块：侧栏窄栏样式（`style.css`、`index.html`、`cost_analysis.html`、`app.py`）
- 变更内容：收窄态图标统一为 40×40、列内居中；模块头固定尺寸并去掉 flex gap 占位；窄栏宽度与 logo 对齐。
- 验证：浏览器进入子模块后目视 WKT / 订 / 成 图标大小与垂直对齐一致。
- SOP 同步：不涉及。

### CL-0068 · 2026-05-30 · 优化（C）
- 涉及模块：侧栏（`style.css`、`_order_sidebar.html`、`index.html`、`cost_analysis.html`、`app.py`）
- 变更内容：去掉侧栏 `width`/`padding` 过渡动画（避免主内容区同步重排卡顿）；收窄态文字用 `visibility` 隐藏；子菜单收起改为 `max-height` 折叠。
- 验证：浏览器切换子模块与点击「订单管理」展开，侧栏应瞬时切换无拖影。
- SOP 同步：不涉及。

### CL-0067 · 2026-05-30 · 优化（C）
- 涉及模块：侧栏（`_order_sidebar.html`、`app.js`、`style.css`、`cost_analysis.html`）
- 变更内容：进入任一功能子模块后自动**收起订单管理子菜单**并将侧栏收窄为图标栏，主内容区更宽；再点「订单管理」可展开完整菜单切换模块。
- 验证：浏览器切换各子模块与成本分析页目视。
- SOP 同步：不涉及。

### CL-0066 · 2026-05-30 · 优化（C）
- 涉及模块：订单列表 UI（`index.html`、`app.js`、SOP §3.5）
- 变更内容：列表上方仅保留 **「清空筛选」** 按钮，移除说明文字与条数提示行，节省纵向空间；按钮文案统一为「清空筛选」。
- 验证：浏览器目视。
- SOP 同步：已更新 §3.5 按钮名称。

### CL-0065 · 2026-05-30 · 优化（C）
- 涉及模块：订单列表表头（`app.js`、`style.css`、`index.html`）
- 变更内容：表头标题与 ▾ 筛选改为 flex 布局，标题可换行完整显示；略调窄列宽分配；缩小筛选按钮避免挤压文字。
- 验证：浏览器目视订单明细表头各列文案。
- SOP 同步：不涉及。

### CL-0064 · 2026-05-30 · 修复（C）
- 涉及模块：订单列表 UI（`style.css`、`app.js`）
- 变更内容：表格单元格默认箭头光标；仅文字被省略的列显示问号（`help`）并弹出全文提示。
- 验证：浏览器目视列表与 OCR 预览表。
- SOP 同步：不涉及。

### CL-0063 · 2026-05-30 · 修复（C）
- 涉及模块：订单列表 UI（`app.js`、`style.css`、`index.html`）
- 变更内容：悬停行改为淡蓝高亮（与灰色斑马纹区分）；列表单元格**仅在被省略截断时**显示黑底全文提示，并固定在单元格下方，不再跟随鼠标。
- 验证：浏览器目视列表悬停与长文本列。
- SOP 同步：不涉及。

### CL-0062 · 2026-05-30 · 优化（C）
- 涉及模块：订单列表 UI（`style.css`、`index.html`）
- 变更内容：加深列表斑马纹对比度（偶数行与悬停底色更明显）。
- 验证：浏览器目视。
- SOP 同步：不涉及。

### CL-0061 · 2026-05-30 · 优化（C）
- 涉及模块：订单列表 UI（`style.css`、`index.html`）
- 变更内容：订单明细 / 出货 / 未结 / 结案表格增加**斑马纹**（奇偶行背景分层）；悬停仍高亮；新录入黄标、未结超期橙标、行内编辑态保持原样式。
- 验证：浏览器目视列表。
- SOP 同步：不涉及操作流程变更。

### CL-0060 · 2026-05-30 · 文档（C）
- 涉及模块：`.cursor/skills/`、`.cursor/rules/`、`scripts/sync-superpowers-skills.ps1`、`AGENTS.md`、`docs/architecture/data-model.md`
- 变更内容：安装 **Superpowers**（obra 14 技能）与 **Karpathy guidelines**；新增 `wkt-agent-workflow` 规则；强制改库时同步 `data-model.md`；Superpowers 同步脚本。
- 验证：`.cursor/skills` 含 15 个 SKILL.md；规则在 Settings → Rules 可见。
- SOP 同步：不涉及操作流程变更。

### CL-0059 · 2026-05-30 · 文档（C）
- 涉及模块：`docs/architecture/data-model.md`、`AGENTS.md`
- 变更内容：新增 **数据结构说明**（SQLite 表、JSON 配置、送货单快照、计算字段、数据流图）。
- 验证：文档目视；与 `line_store.py` 表结构对照一致。
- SOP 同步：不涉及操作流程变更。

### CL-0058 · 2026-05-30 · 优化（C）
- 涉及模块：订单列表 UI（`app.js`、`style.css`、`index.html`、SOP §3.5）
- 变更内容：列筛选改为 **Excel 式表头 ▾ 下拉**（勾选唯一值、全选、搜索、确定/重置）；移除表头下方文本输入行；已筛选列按钮高亮。
- 验证：浏览器目视四列表；单元测试 81/81 通过。
- SOP 同步：已更新 §3.5。

### CL-0057 · 2026-05-30 · 优化（C）
- 涉及模块：订单列表 UI（`app.js`、`style.css`、`index.html`、SOP §3.5）
- 变更内容：**订单明细 / 出货明细 / 未结订单 / 结案订单** 表头增加列筛选行，支持按各列关键字即时过滤（多列且条件）；各子模块独立保留筛选；移除原顶部搜索框与客户下拉。
- 验证：浏览器目视四列表筛选；单元测试 81/81 通过。
- SOP 同步：已更新 §3.5 查找与筛选。

### CL-0056 · 2026-05-30 · 文档（C）
- 涉及模块：`AGENTS.md`、`docs/VERSION.md`、`docs/change/CHANGELOG.md`
- 变更内容：新增根目录 **AGENTS.md**（架构速查、合规清单、会话连贯性协议）；发布 **v0.4.0** 里程碑；同步 VERSION 与 CHANGELOG 当前版本。
- 验证：文档目视；`/api/health` build 更新为 `20260531-v0.4.0`。
- SOP 同步：不涉及操作流程变更。

### CL-0055 · 2026-05-30 · 优化（B）
- 涉及模块：OCR 预览（`source_preview.py`、`app.py`、`app.js`、`style.css`、`index.html`、SOP §3.2）
- 变更内容：识别页改为**上原件、下表格**布局；PDF 原件 200 DPI 渲染 PNG 缓存；支持缩放/适应宽度/新窗口/多页切换；不再加载时自动缩小表格。
- 验证：单元测试通过；浏览器上传 PDF 目视清晰度。
- SOP 同步：已更新 §3.2 原件对照说明。

### CL-0054 · 2026-05-30 · 新增（B）
- 涉及模块：飞书集成（`integrations/feishu.py`、`wkt_events.py`、`app.py`、`data/feishu_config.json`、SOP §五）
- 变更内容：配置 Webhook 后推送订单录入、修改、删除、出货、Excel 导入确认等事件；提供 `/api/feishu/config` 与测试接口。
- 验证：`tests/test_feishu_notify.py` 通过。
- SOP 同步：已更新 §五 飞书变动通知。

### CL-0053 · 2026-05-30 · 新增（B）
- 涉及模块：出货流程（`app.py`、`app.js`、`delivery_note_wkt_confirm.html`、SOP §3.4）
- 变更内容：未结出货前弹出**送货单确认** iframe，可编辑抬头/明细后确认；POST ship 接受 `delivery_note` 对象；确认后自动打开打印页；快照写入 `shipment_events.delivery_note_json`。
- 验证：`tests/test_delivery_note.py` 等通过；浏览器走通出货确认。
- SOP 同步：已更新 §3.4 出货与送货单。

### CL-0052 · 2026-05-30 · 新增（B）
- 涉及模块：送货单（`order_management/delivery_note/`、`delivery_note_wkt.html`、`delivery-note-admin.js`、`data/delivery_templates/`、SOP §3.6）
- 变更内容：全客户统一 **WKT 标准送货单**（HTML 打印 + xlsx 导出）；侧边栏**送货单维护**配置各客户收货信息/单号前缀；出货后按事件 ID 打印/下载。
- 验证：`tests/test_wkt_delivery_document.py`、`test_delivery_note.py` 通过。
- SOP 同步：已更新 §3.6 送货单维护。

### CL-0051 · 2026-05-30 · 新增（B）
- 涉及模块：持久化与出货（`line_store.py`、`line_service.py`、`shipment_models.py`、`app.py`、`app.js`、SOP §3.4）
- 变更内容：订单行由内存改为 **SQLite**（`data/wkt_orders.db`）；新增 `shipment_events` 与出货明细视图；未结列表支持部分数量出货；`/api/health` 暴露 `storage`/`line_count`。
- 验证：单元测试 81/81 通过；重启服务后数据仍在。
- SOP 同步：已更新 §3.4 出货明细与未结出货。

### CL-0050 · 2026-05-30 · 优化（B）
- 涉及模块：Excel 导入（`excel_import.py`、`app.py`、`app.js`、`index.html`、SOP）
- 变更内容：解析后分栏「已通过 / 待确认 / 阻断」；先导入已通过；待确认独立栏；阻断输出完整报告（可复制/下载）。
- 验证：单元测试通过。
- SOP 同步：已更新 §3.3 导入流程。

### CL-0049 · 2026-05-30 · 优化（B）
- 涉及模块：Excel 导入、订单录入 UI（`excel_import.py`、`app.js`、`index.html`、SOP）
- 变更内容：账期按 Excel 原文保存（不再限制月结预设）；账期说明误入税率列时自动纠正；去掉无金额列时的警告；手动/OCR 账期改为自由文本。
- 验证：单元测试 55/55 通过。
- SOP 同步：已更新账期说明。

### CL-0048 · 2026-05-30 · 优化（C）
- 涉及模块：Excel 导入模板与预览表头（`excel_import.py`、`app.js`、`index.html`、SOP）
- 变更内容：导入模板/预览表头统一为 15 列（与业务台账一致，去掉模板中的「金额」列；金额仍为可选校验列）。
- 验证：单元测试通过。
- SOP 同步：已更新 §3.3 推荐表头。

### CL-0047 · 2026-05-30 · 新增（B）
- 涉及模块：订单录入 Excel 导入（`excel_import.py`、`app.py`、`app.js`、`index.html`）、依赖 `openpyxl`
- 变更内容：支持 `.xlsx`/`.csv` 批量导入客户订单（含已出货、未结数量）；校验未结=PO−已出货、金额=PO×含税单价；提供导入模板下载与预览后确认导入。
- 验证：单元测试通过；`pip install openpyxl` 后网页解析样表。
- SOP 同步：已更新 §3.3 Excel 批量导入。

### CL-0046 · 2026-05-30 · 新增（B）
- 涉及模块：OCR 识别（`order_archive.py`、`app.py`、`app.js`）、`orders/` 目录
- 变更内容：OCR 识别成功后，将上传的原始订单文件归档至 `orders/{客户名}/{接单日期}_{订单号}.ext`；重名自动加序号；归档失败不阻断识别。
- 验证：单元测试 47/47 通过（含 `test_order_archive.py`）。
- SOP 同步：已更新 §3.2 订单文件自动归档。

### CL-0045 · 2026-05-30 · 重构（B）
- 涉及模块：订单录入（删除客户维护页与 API；`line_service.py`、`app.js`、`index.html`、SOP）
- 变更内容：移除**客户维护**；账期改为下拉（月结30/60/90天 + 自定义天数），OCR 预览与手工录入一致。
- 验证：单元测试 42/42 通过。
- SOP 同步：已更新。

### CL-0043 · 2026-05-30 · 优化（B）
- 涉及模块：UI（`style.css`、`cost.css`、`index.html`、`customers.html`、`cost_analysis.html`）、设计文档（`docs/design/`）
- 变更内容：引入 [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) 设计库；全站切换为 **Linear 深色 SaaS** 主题（薰衣草蓝强调色、Inter 字体、发丝线边框）；新增 `docs/design/DESIGN.md` 与 `awesome-design-md/` 目录。
- 验证：单元测试通过；浏览器目视各页面。
- SOP 同步：不涉及操作流程变更。

### CL-0042 · 2026-05-30 · 新增（B）
- 涉及模块：客户主数据（`line_models.py`、`line_service.py`、`intake_service.py`、`app.py`、`customers.html`、`customers.js`、`app.js`、`index.html`、SOP）
- 变更内容：新增**客户维护**模块（标准账期）；OCR/手工录入匹配客户后**自动填入账期**并覆盖 OCR 多种写法；客户 API CRUD；侧边栏入口。
- 验证：单元测试 43/43 通过。
- SOP 同步：已更新（3.5 客户维护）。

### CL-0041 · 2026-05-30 · 优化（B）
- 涉及模块：订单 OCR（`text_extract.py`、`intake_service.py`、`app.py`、`app.js`、`index.html`、SOP；删除 `ocr_compare.py`）
- 变更内容：关闭双方案（RapidOCR + 百度）对比，恢复**单路 OCR + 一次 AI + 规则校验**，识别速度约为原先一半；**保留多文件批量上传**。`baidu_ocr.py` 保留供后续按需启用。
- 验证：单元测试 41/41 通过。
- SOP 同步：已更新（3.2 单路 OCR）。

### CL-0040 · 2026-05-30 · 新增（B）
- 涉及模块：OCR 上传（`index.html`、`app.js`、`style.css`、SOP）
- 变更内容：订单 OCR 支持**一次选择多个 PDF/图片**，按顺序识别后合并到同一预览表；进度条显示「第 N/M 个文件」；多文件时显示来源文件名及合并后的对比/校验摘要。
- 验证：单文件行为与原先一致。
- SOP 同步：已更新（3.2 多文件上传）。

### CL-0039 · 2026-05-30 · 新增（B）
- 涉及模块：百度 OCR（`baidu_ocr.py`、`config.py`、`text_extract.py`、`ocr_compare.py`、`intake_service.py`、`app.js`、`index.html`、SOP、secrets 示例）
- 变更内容：方案二接入**百度 OCR 高精度版**（云端）；与方案一 RapidOCR 双路识别、双路 AI 结构化后对比准确率；预览仍以方案一为准；保留规则校验与 OCR 原文左右对照。
- 验证：单元测试 44/44 通过；百度 Token 冒烟通过。
- SOP 同步：已更新（3.2 双方案对比、百度密钥配置）。

### CL-0038 · 2026-05-30 · 重构（B）
- 涉及模块：订单 OCR（删除 `paddle_ocr.py`、`ocr_verify.py`；新增 `field_validation.py`；`text_extract.py`、`intake_service.py`、`deepseek.py`、`app.py`、`app.js`、`index.html`、`style.css`、`requirements.txt`、`restart_web.ps1`、SOP、VERSION）
- 变更内容：按方案 A 改为**单路 OCR**（PDF 文字层 / RapidOCR 300 DPI）+ 一次 AI 结构化 + **规则校验**（料号格式、数量、日期等）；移除方案 B PaddleOCR 及双路 AI 比对；保留 OCR 原文查看；扫描识别速度提升。后续可扩展云端 OCR。
- 验证：单元测试通过；依赖仅保留 RapidOCR + PyMuPDF。
- SOP 同步：已更新（3.2 单路 OCR、黄标记规则校验）。

### CL-0037 · 2026-05-30 · 优化（B）
- 涉及模块：双重验证（`intake_service.py`、`app.py`、`app.js`、`index.html`、`style.css`、`deepseek.py`、`ocr_verify.py`、SOP）
- 变更内容：识别完成后可**展开查看两套 OCR 原文**并排对比，便于区分 OCR 漏字与 AI 填错字段；DeepSeek 提示词强化客户料号/交期规则；比对增加全角半角归一化及品名内短编号误填料号的纠偏。
- 验证：单元测试 42/42 通过；识别 API 返回 `ocr_text` 字段。
- SOP 同步：已更新（3.2 查看 OCR 原文）。

### CL-0036 · 2026-05-30 · 优化（B）
- 涉及模块：方案二 OCR（移除 EasyOCR；新增 `paddle_ocr.py` ONNX PaddleOCR；删除 `ocr_engine_b.py`）
- 变更内容：方案二由 EasyOCR 换为 **PaddleOCR PP-OCRv5（onnxocr 包，ONNX 推理）**，启动更快；清理 EasyOCR 依赖与相关文件。
- 合规说明：B 级。
- 验证：单元测试通过；PaddleOCR ONNX 本地冒烟通过。
- SOP 同步：已更新。

### CL-0035 · 2026-05-30 · 优化（B）
- 涉及模块：方案二 OCR（新增 `ocr_engine_b.py` EasyOCR、`text_extract.py`、`intake_service.py`、`requirements.txt`）
- 变更内容：方案二由 RapidOCR 高清改为 **EasyOCR** 独立引擎（中英文）；不可用时回退 RapidOCR 高清；两套 OCR 分别独立 AI 结构化再比对。
- 合规说明：B 级。
- 验证：单元测试通过；需 `pip install easyocr`。
- SOP 同步：已更新。

### CL-0034 · 2026-05-30 · 优化（B）
- 涉及模块：双路 OCR / 双重验证（`text_extract.py`、`deepseek.py`、`intake_service.py`、`ocr_verify.py`）
- 变更内容：方案二改为高清 OCR（取消灰度锐化增强）；OCR 偏少时自动高 DPI 重试；DeepSeek 一次调用双路结构化；方案二漏字段时 AI 重试；方案二 AI 为空但 OCR 原文含值时视为一致。
- 合规说明：B 级。
- 验证：单元测试通过。
- SOP 同步：已更新。

### CL-0033 · 2026-05-30 · 优化（C）
- 涉及模块：OCR 双重验证 UI（`ocr_verify.py`、`app.js`、`style.css`、SOP）
- 变更内容：不一致处增加可点击清单（行号+字段+两方案值）、表格红框+「不一致」标签+方案二副文本、点击定位并闪烁高亮。
- 合规说明：C 级（UI）。
- 验证：静态资源刷新即生效。
- SOP 同步：已更新（3.2 核对标记）。

### CL-0032 · 2026-05-30 · 优化（B）
- 涉及模块：订单 OCR 双重验证（`intake_service.py`、`ocr_verify.py`、`app.js`、SOP）
- 变更内容：双重验证改为**始终**对两套 OCR 分别 DeepSeek 结构化，再比对两套 AI 结果；一致即 OK，不一致红标记；移除 OCR 文字相似度阈值与全文回查逻辑。
- 合规说明：B 级（验证逻辑调整）。
- 验证：单元测试 41/41 通过。
- SOP 同步：已更新（3.2 双重验证说明）。

### CL-0031 · 2026-05-30 · 新增（B）
- 涉及模块：订单 OCR 识别（`text_extract.py`、`ocr_verify.py`、`intake_service.py`、`app.py`、`app.js`、`index.html`、`style.css`）
- 变更内容：双路 OCR 识别与双重验证——电子版 PDF 用文字层+RapidOCR，扫描件用标准+增强 RapidOCR；比对全文相似度，差异大时双路 AI 结构化；预览区黄/红标记需核对字段；识别过程进度条（异步任务+轮询）。
- 合规说明：B 级（识别流程扩展）。
- 验证：单元测试 40/40 通过；手动上传 PDF/图片验证进度与标记。
- SOP 同步：已更新（3.2 OCR 双重验证、常见问题）。

### CL-0030 · 2026-05-30 · 文档（A）
- 涉及模块：《系统操作 SOP》（`docs/SOP/系统操作SOP.md`）
- 变更内容：按业务用户视角重写 SOP：按功能分章（打开系统、界面说明、OCR 录入、手工录入、列表管理、成本分析、常见问题），去除变更编号、开发路径、设计基线等内部术语；维护约定保留在 CHANGELOG / 治理准则，不再写入用户文档。
- 合规说明：A 级（文档）。
- 验证：文档评审。
- SOP 同步：本文档即更新对象。

### CL-0029 · 2026-05-30 · 文档（A）
- 涉及模块：全局文档（`docs/VERSION.md`、`docs/design/ui-style-guide-v1.md`、`docs/SOP/系统操作SOP.md`、`docs/change/CHANGELOG.md`、`docs/change/erp-governance-v1.md`）
- 变更内容：发布 **v0.3.0** 里程碑；建立版本记录与 UI 设计基线 V1.0；全面更新系统操作 SOP（界面说明、模板2 字段、录入流程、维护约定）；规定后续 Web 界面须保持当前风格。
- 合规说明：A 级（文档与基线冻结）。
- 验证：文档评审；`scripts/verify.ps1` 36/36 通过。
- SOP 同步：已全面更新（v0.3.0 基线）。

### CL-0028 · 2026-05-30 · 优化（C）
- 涉及模块：全局 UI 字体层级（Web `style.css`）
- 变更内容：建立菜单/标题统一字体层级变量（侧栏品牌→分组→模块项、页面标题→说明、区块标题→副说明、录入方式 Tab），同级样式一致、层级间字号/字重/颜色区分。
- 合规说明：C 级（纯 UI 样式）。
- 验证：静态资源刷新即生效。
- SOP 同步：无需变更。

### CL-0027 · 2026-05-30 · 修复（C）
- 涉及模块：订单录入 UI（Web `app.js`）
- 变更内容：识别预览/列表悬停时移除浏览器原生 `title` 提示，仅保留自定义深色 tooltip，避免两条提示互相遮挡。
- 合规说明：C 级（纯 UI 交互）。
- 验证：静态资源刷新即生效。
- SOP 同步：无需变更。

### CL-0026 · 2026-05-30 · 优化（C）
- 涉及模块：订单录入 UI（Web `index.html`、`style.css`）
- 变更内容：手动录入表单布局收紧——统一 5 列网格、组间细分隔线、紧凑标签与输入框、「+」快捷新增按钮、操作按钮横向排列；第三行单价字段占两列对齐。
- 合规说明：C 级（纯 UI 交互）。
- 验证：静态资源刷新即生效。
- SOP 同步：无需变更（操作流程不变）。

### CL-0025 · 2026-05-30 · 修复（C）
- 涉及模块：订单录入 UI（Web `index.html`、`app.js`、`style.css`）
- 变更内容：修复录入方式切换无效（`.mode-panel { display:flex }` 覆盖 `[hidden]`）；初始不预选模式、不显示上传/预览/手动表单；OCR 模式仅显示上传区，识别成功后才显示预览；手动模式选中后才显示表单。
- 合规说明：C 级（纯 UI 交互）。
- 验证：静态资源刷新即生效；`scripts/verify.ps1` 36/36 通过。
- SOP 同步：已更新（4.0 录入方式切换）。

### CL-0024 · 2026-05-30 · 优化（C）
- 涉及模块：订单录入 UI（Web `index.html`、`app.js`、`style.css`）
- 变更内容：录入区增加「订单 OCR 识别 / 手动录入」切换；选 OCR 显示上传+识别预览，选手动显示录入表单；已录入列表始终可见；列表「修改」自动切到手动录入。
- 合规说明：C 级（纯 UI 交互）。
- 验证：静态资源刷新即生效。
- SOP 同步：已更新（4.0 录入方式切换）。

### CL-0023 · 2026-05-30 · 优化（C）
- 涉及模块：订单录入 UI（Web `app.js`、`style.css`）
- 变更内容：识别预览/录入表单/已录入列表的输入框与单元格，鼠标悬停时以浮动 tooltip 完整显示内容，便于录入人员核对 OCR 是否有误；同步设置原生 title 兜底。
- 合规说明：C 级（纯 UI 交互）。
- 验证：前端无 lint 错误；静态资源刷新即生效。
- SOP 同步：已更新（4.2 核对说明）。

### CL-0022 · 2026-05-30 · 优化（B）
- 涉及模块：订单录入料号行字段（`line_models.py`、`line_service.py`、`line_mapper.py`、Web `index.html` / `app.js` / `app.py`、`tests/test_order_line_service.py`）
- 变更内容：将全部 item 字段替换为附件2 所示 RMB 口径 15 列。
  - 字段：客户、接单日期、客户交期、订单号、品名规格、客户料号、单重（不含损耗）g、材质、PO数量、已出货、未结数量、单位、税率、人民币单价（含税）、账期。
  - 移除 USD/状态/备注/公司料号；主数据改为品名规格↔客户料号映射。
  - 预览表格、已录入列表、手动录入表单三处统一 15 列；未结数量自动计算只读。
  - OCR 映射 `intake_to_lines` 对齐附件2 全字段；DeepSeek `max_tokens` 提升至 16384 缓解截断。
- 合规说明：B 级（字段对齐）。仍为一料号一行平铺；内存存储。
- 验证：单元测试 36/36 通过。
- SOP 同步：已更新（4.0 字段说明）。

### CL-0021 · 2026-05-30 · 重构（B）
- 涉及模块：订单录入（新增 `line_models.py`、`line_service.py`、`line_mapper.py`；Web `index.html` / `app.js` / `style.css` / `app.py`；`tests/test_order_line_service.py`）
- 变更内容：按附件2 模板重构订单录入为**料号行平铺模型**。
  - 一个料号 = 一条订单行记录（USD 计价）；同一 PO 可多行共用订单编号。
  - 新增 `OrderLineService`（内存存储，仅测试）：主数据（客户/公司料号/状态）、记录 CRUD、搜索过滤。
  - 公司料号 ↔ 客户料号全局一对一映射；选公司料号自动带出客户料号；支持下拉 + 新增。
  - 金额 = 数量 × 单价（单价 4 位、金额 2 位，复用 `common/money.py`）；可手动覆盖金额。
  - Web API：`/api/master`、`/api/lines` CRUD、`/api/lines/recognize`（OCR 识别后每个料号平铺一行预览）。
  - 前端：两排录入表单 + OCR 预览表格（每料号一行）+ 批量提交 + 可搜索/过滤的已录入列表（修改载入表单、删除）。
  - 旧 `OrderEntryService`（RMB/状态机模型）保留不删，页面已切到新服务。
- 合规说明：B 级（模块重构）。旧订单状态机接口仍保留；新模型为测试用内存存储，重启清空。
- 验证：单元测试 36/36 通过（新增 `test_order_line_service.py` 8 项）；首页 200；API 返回 2 条 demo 行、2 个客户。
- SOP 同步：已更新（第 4 节全面重写）。

### CL-0020 · 2026-05-30 · 优化（B）
- 涉及模块：订单识别完整性（`order_intake/deepseek.py`）
- 背景：一张订单含多个料号时，需确保每个料号都识别为一行明细、全部列出不遗漏。
- 变更内容：
  - 强化 DeepSeek 提示词：要求每个料号/每行明细单独成项，有多少行输出多少行，**不得遗漏/合并/去重/截断**，即使几十行也逐行输出。
  - DeepSeek 请求增加 `max_tokens: 8192`，避免明细多时输出 JSON 被截断。
  - 增加截断检测：若 `finish_reason == "length"`，返回明确提示（建议拆分文件分批上传）。
- 合规说明：B 级（识别质量增强）。未改数据模型/状态机；同一订单多料号仍归为一张订单的多行明细，不会错误拆单。
- 验证：单元测试 28/28 通过；端到端用 6 料号单订单 PDF，识别为 1 张订单 6 行明细，料号/数量全部正确无遗漏。
- SOP 同步：已更新（4.0 完整性说明）。

### CL-0019 · 2026-05-30 · 优化（C）
- 涉及模块：订单录入页布局（Web `style.css`）
- 变更内容：移除内容区 `.content-stack` 的 `max-width: 960px` 限制，内容铺满主区域，消除右侧大片留白。
- 合规说明：C 级（纯样式），不涉及数据/接口/状态机。
- 验证：前端无 lint 错误；静态资源即时生效（浏览器 Ctrl+F5 刷新）。
- SOP 同步：不涉及操作步骤（仅视觉宽度）。

### CL-0018 · 2026-05-30 · 优化（C）
- 涉及模块：订单识别可编辑块布局（Web `app.js`、`style.css`）
- 变更内容：调整识别结果可编辑块的布局顺序，明细优先。
  - 明细表格（品名/规格、客户料号、PO数量等）上移至订单标签下方。
  - 订单信息表头字段（客户、订单号、接单日期、客户交期、账期、录入人）下移，加「订单信息」分隔标题。
  - 「增加明细」紧随表格；「保存/放弃」置于订单信息之后。
- 合规说明：C 级（纯展示布局调整），不涉及数据/接口/状态机。
- 验证：首页 `/` 返回 200；前端无 lint 错误。
- SOP 同步：已更新（4.0 第 3 步布局说明）。

### CL-0017 · 2026-05-30 · 新增/优化（B）
- 涉及模块：全局金额标准（新增 `test_impl/common/money.py`）、订单（`order_entry/models.py`、`service.py`、Web `app.py` / `app.js` / `style.css`）、成本分析前端（`cost.js`）、标准文档（`docs/change/money-format-v1.md`）、`tests/test_money.py`
- 变更内容：建立并落地《金额格式统一标准 v1》，单一实现来源 `common/money.py`。
  - 精度：金额/税额/折扣 2 位（`DECIMAL(18,2)`），单价 4 位（`DECIMAL(18,4)`），汇率 6 位；全程 `Decimal`，严禁 float。
  - 舍入：统一财务四舍五入 `ROUND_HALF_UP`，禁止截断（`round_amount/round_price/round_rate`）。
  - 展示：千分位 + 固定小数；负数 `-12,345.67`；整数补 `.00`（`fmt_amount/fmt_price`）。
  - 大写：`rmb_upper`，订单合计返回中文大写并在页面展示。
  - 传输：接口用纯数字字符串、无千分位无符号（`transport`）；订单序列化单价改 4 位、金额 2 位。
  - 输入：录入框限制仅数字/小数点，金额≤2 位、单价≤4 位（前端 `attachDecimalLimit`）。
  - 接入：订单 `amount/total_amount` 经 `round_amount`，单价经 `round_price`；成本分析前端统一 4 位千分位展示。
- 合规说明：B 级（标准 + 落地）。未改业务状态机；金额口径与既有计算一致（仅统一精度/展示/大写/传输）。
- 验证：单元测试 28/28 通过（新增 `test_money.py` 8 项：舍入、千分位、传输串、大写多用例）；接口实测 total `3400.00`／大写「人民币叁仟肆佰元整」、单价 `2.5000`、行金额 `2500.00`。
- SOP 同步：已更新（新增「金额格式规范」小节）。

### CL-0016 · 2026-05-30 · 优化（B）
- 涉及模块：订单录入识别（`order_intake/deepseek.py`、`intake_service.py`、`__init__.py`、Web `index.html` / `app.js` / `style.css`、`tests/test_order_intake.py`）
- 变更内容：录入流程改为"识别 → 可编辑结果 → 逐张保存"，并支持一份文件含多张订单自动拆分。
  - 删除「新建订单」手动表单卡片与「订单明细」录入模板（含明细模板 `itemRowTemplate`）。
  - DeepSeek 提示词改为输出 `{"orders": [...]}`，要求按订单号/客户拆分多张订单；单张时数组仅一项。
  - `normalize_extraction` 重构为返回 `{"orders": [...]}`，并新增 `normalize_order` 处理单张；兼容 DeepSeek 直接返回单张（无 orders 包裹）的旧格式。
  - 前端：识别后在「识别结果（可编辑）」区为每张订单生成**可编辑表格**（表头字段 + 明细行均可改），未结数量、金额、含税合计随输入实时计算；税率以百分比录入，保存时转 0~1。
  - 每张订单独立「保存订单 / 放弃」；保存成功后该块消失并刷新「已保存订单」。支持「增加明细 / 删除行」。
- 合规说明：B 级（交互重构）。**未改动后端订单状态机与服务校验（红线保留）**；保存仍走既有 `create_order`，金额/未结口径不变。
- 验证：
  - 单元测试 20/20 通过（新增多订单拆分、单张兼容、空输入用例）。
  - API：以可编辑块的载荷 POST `/api/orders` 创建成功（含税合计 2500.00、未结 700、行金额 2500.00，与样表一致）。
  - 首页 `/` 返回 200；前端无 lint 错误。
- SOP 同步：已更新（4.0 改为"识别→编辑→保存"，4.1 调整，4.2 录入结果说明）。

### CL-0015 · 2026-05-30 · 优化（B）
- 涉及模块：订单录入页面（Web `index.html`、`app.js`）
- 变更内容：按需求精简订单录入页，聚焦"录入 + 展示"。
  - 删除顶部统计卡片（订单总数 / 待审核 / 已审核 / 合计金额）。
  - 录入结果区移除状态徽章与"审核通过 / 取消订单"按钮（管理类操作暂不在本页面提供）。
  - 保留并明确三块：① 上传订单识别（OCR/手动二选一入口）② 新建订单（手动录入）③ 录入结果（明细表格展示，列与样式对齐业务表）。
  - 列表卡片更名"订单列表"→"录入结果"，页面副标题相应调整。
- 合规说明：B 级（界面精简）。**未触碰后端订单状态机与服务接口（红线保留）**，仅移除前端入口；`approve/cancel` 接口仍在，后续模块可复用。
- 验证：单元测试 18/18 通过；首页 `/` 返回 200；前端无 lint 错误；录入结果表格列＝#/品名规格/客户料号/单重(g)/材质/PO数量/已出货/未结/单位/税率/含税单价/金额。
- SOP 同步：已更新（4.1 步骤、新增 4.2 录入结果展示、移除原 4.2/4.3 审核取消步骤并加说明）。

### CL-0014 · 2026-05-30 · 新增（B）
- 涉及模块：订单识别录入 OCR（`order_intake/text_extract.py`、Web `index.html` / `app.js`、`requirements.txt`）
- 背景：真实客户订单多为**扫描件 PDF / 图片**（无文字层），CL-0013 仅支持电子版 PDF，上传扫描件提示"没有文字层"。本次启用 OCR 第二阶段。
- 变更内容：
  - 经核实，DeepSeek 账号仅 `deepseek-v4-flash` / `deepseek-v4-pro`，均为纯文本模型，官方 V4 API 不支持直接读图 → 采用本地 OCR 方案。
  - 引入 **RapidOCR（onnxruntime）** 作 OCR 引擎：pip 安装、无需系统软件、离线可用、中文识别效果好。
  - `text_extract.py` 升级：电子版 PDF 走文字层；**扫描件 PDF 自动回退到 OCR**（PyMuPDF 200dpi 渲染每页→RapidOCR）；**新增图片文件 OCR**（png/jpg/bmp/tif/webp）。
  - 大图保护：单张最长边超 3000px 自动等比缩小，防止超大扫描件爆内存。
  - 前端：上传控件接受 PDF + 常见图片格式；文案改为"PDF / 图片"，提示扫描件需 OCR 可能数十秒。
- 合规说明：B 级（能力扩展）。未触碰订单状态机与跨域红线；OCR 结果仍需人工核对后才创建订单。
- 验证：
  - 单元测试 18/18 通过（移除原"图片未启用"用例）。
  - 端到端：合成"扫描件"PDF（仅图片、无文字层）→ 自动 OCR → DeepSeek 结构化，正确识别客户、日期、账期、品名、材质、单重、数量、已出货、税率、单价（个别字段受合成图清晰度影响有 OCR 误差，真实扫描件更优）。
- 已知限制 / 注意：识别准确率取决于扫描件清晰度与排版；务必人工核对。建议后续用真实订单样本调优渲染 DPI 与结构化提示词。
- SOP 同步：已更新（第 4.0 节支持图片/扫描件）。

### CL-0013 · 2026-05-30 · 新增（B）
- 涉及模块：订单识别录入（新增 `test_impl/order_management/order_intake/`、Web `app.py` / `index.html` / `app.js` / `style.css`、密钥配置 `config/`、`.gitignore`）
- 变更内容：实现「上传订单自动识别录入」（混合方案第一阶段）。
  - 流程：上传电子版 PDF → 本地 PyMuPDF 提取文字 → DeepSeek V4（文本模型）结构化为订单字段 JSON → 规范化 → 填入新建订单表单，人工核对后再创建（不直接落库）。
  - 模块：`config.py`（密钥读取，环境变量优先，其次本地密钥文件）、`text_extract.py`（PDF 取文字，图片/扫描件 OCR 留可插拔占位）、`deepseek.py`（DeepSeek V4 结构化客户端，JSON 模式）、`intake_service.py`（编排 + 纯函数 `normalize_extraction`：数字清洗、税率归一到 0~1）。
  - Web：新增 `POST /api/orders/recognize` 上传识别接口；订单页新增「上传订单识别」卡片，识别结果自动填充表头与明细行。
  - 安全：密钥写入 `config/secrets.local.json` 并经 `.gitignore` 排除；提供 `config/secrets.example.json` 模板；密钥不进源码、不入库。
- 合规说明：B 级（能力扩展 + 外部集成）。未触碰订单状态机与跨域红线；识别结果需人工确认后才走既有 `create_order`。
- 验证：
  - 单元测试 19/19 通过（新增 `tests/test_order_intake.py` 7 项：数字清洗、税率归一、规范化、不支持类型、图片未启用）。
  - 真实端到端：生成含中文订单 PDF → 完整流程调 DeepSeek，正确识别客户/订单号/日期/账期及两条明细的数量、单位、税率(0.13)、含税单价。
  - HTTP 接口：multipart 上传 `/api/orders/recognize` 返回结构正确。
- 已知限制：图片/扫描件 OCR 暂未启用（接口已留占位，后续接 Tesseract/云 OCR）；电子版 PDF 文字层缺失时给出明确提示。
- SOP 同步：已更新（第 4.0 节「上传订单识别录入」）。

### CL-0012 · 2026-05-30 · 优化（B）
- 涉及模块：订单录入（`order_entry/models.py`、`service.py`、Web `index.html` / `app.js`、`app.py`）
- 变更内容：按业务表头重构订单录入字段。
  - 表头：客户、订单号、接单日期、客户交期、账期、录入人。
  - 明细：品名/规格、客户料号、单重未含损耗(g)、材质、PO数量、已出货数量、未结数量(自动=PO−已出货)、单位、税率、人民币含税单价。
  - 金额口径：行含税金额 = PO数量 × 人民币含税单价；订单含税合计 = 各行之和。
  - 列表改为明细表格展示；保留订单状态机不变（红线）。
  - `create_order` 接收明细数组，为后续"上传订单自动识别录入"预留批量入口。
- 合规说明：B 级（字段扩展），已补充字段映射设计；未触碰状态机与跨域红线。
- 验证：单元测试 12/12 通过；示例单含税合计 3400.00、未结 700；新建单金额 666.66、未结 150 均正确；页面 `/` 正常。
- SOP 同步：已更新（第 4.1 节录入字段、4.4 校验规则）。

### CL-0011 · 2026-05-30 · 优化（A）
- 涉及模块：成本分析 Web（`cost_analysis.html`、`cost.css`）
- 变更内容：将"报价参数"中的 原材（下拉）、原材单价、原材重量 合并到同一行排布，更紧凑；参数行宽度调整为 760px。
- 验证：页面 `/cost` 返回 200。
- SOP 同步：不涉及操作变更（仅布局调整，录入项与步骤不变）。

### CL-0010 · 2026-05-30 · 优化（A）
- 涉及模块：成本分析 Web（`cost_analysis.html`、`cost.js`、`cost.css`）
- 变更内容：按业务方反馈移除"数量"输入字段（报价以单件成本合计为准）；成本分析页加宽至 1180px 并让工艺单价网格自动多列填充，消除右侧大片留白。报价结果简化为：原材成本、工艺合计、客户报价。
- 验证：页面 `/cost` 返回 200，已确认无"数量"字段、加宽样式生效；单元测试 10/10 通过。
- SOP 同步：已更新（第 4.5 节，去除数量步骤）。

### CL-0009 · 2026-05-30 · 修复（A）
- 涉及模块：成本分析（`cost_analysis/models.py`、Web `cost_analysis.html` / `cost.js`）
- 变更内容：按业务方修正工艺清单为 39 项（压铸、埋轴、下料、精冲、去毛边、抛光、过砂、打磨、喷砂、补土、抛丸、震研、磁力研磨、钻孔攻牙、车加工、CNC、铆合、皮模钝化、洗白、超声波清洗、电镀、化镍、电泳、烤漆、喷粉、阳极、镭雕、整形、剥漆、包胶、全检、外购磁铁、外购销钉、外购轴套、制程损耗、包装、运输、管销、利润）。因"利润"已作为独立工艺项，移除页面单独的"利润率"输入框，统一按金额累加；客户报价 = 原材成本 + 各项工艺金额，再 × 数量。
- 验证：单元测试 10/10 通过（含清单 39 项、旧名移除校验）；`/api/cost/options` 返回 39 项。
- SOP 同步：已更新（第 4.5 节，去除利润率说明）。

### CL-0008 · 2026-05-30 · 新增（A）
- 涉及模块：成本分析（`test_impl/order_management/cost_analysis/`、Web `cost_analysis.html` / `cost.js` / `cost.css`）
- 变更内容：新增成本分析子模块。原材改为下拉选择（ADC12 / A380 / ZN-05），其余项为工艺（可逐项填单价）；按"选原材 → 填工艺单价 → 生成客户报价"流程计算（原材成本 + 工艺合计，含数量与利润率）。打通侧边栏"成本分析"导航。
- 待核对：工艺名称由图片识别，部分字可能需修正（如 第二个抛丸/震丸、铝合、皮模化料、锚铜、外发镀锌、外发刷镍、外抛）。清单维护位置：`cost_analysis/models.py` 的 `PROCESS_LIST`。
- 验证：新增 6 个单元测试全部通过（共 10/10）；接口 `/api/cost/options`、`/api/cost/quote`、页面 `/cost` 均返回 200；样例报价计算正确（885.5000）。
- SOP 同步：已更新（新增第 4.5 节 成本分析操作流程）。

### CL-0007 · 2026-05-30 · 优化（A）
- 涉及模块：订单录入 Web 界面（`test_impl/web/static/style.css`、`templates/index.html`）
- 变更内容：UI 改为纯白简洁主题——白色侧边栏 + 浅灰内容背景、细边框、低调阴影，统计卡片改为标签/数值左右排布，订单明细改为双列信息块；移除深色背景层。
- 验证：服务返回 200，CSS 含白色主题变量，本地浏览器查看通过。
- SOP 同步：不涉及操作变更（界面布局与操作步骤不变，仅视觉风格调整）。

### CL-0006 · 2026-05-30 · 新增（A）
- 涉及模块：运维脚本 / Web
- 变更内容：新增一键重启脚本 `scripts/restart_web.ps1` 与文件夹双击入口 `一键启动网页.bat`，自动关闭旧服务、启动新服务并打开浏览器。
- 验证：脚本执行成功，服务返回 HTTP 200，浏览器自动打开。
- SOP 同步：已更新（见 SOP 第 2 节 启动系统）。

### CL-0005 · 2026-05-30 · 优化（A）
- 涉及模块：订单录入 Web 界面
- 变更内容：界面改为全纵向布局——左侧六模块竖排导航，右侧内容单列堆叠；订单明细由表格改为纵向信息卡。
- 验证：本地浏览器查看通过。
- SOP 同步：已更新（见 SOP 第 3 节 界面说明）。

### CL-0004 · 2026-05-28 · 新增（A）
- 涉及模块：订单录入 Web 演示
- 变更内容：新增 Flask Web 演示（`test_impl/web/`），支持订单创建、审核、取消、列表展示。
- 验证：手动操作创建/审核订单通过。
- SOP 同步：已更新。

### CL-0003 · 2026-05-28 · 新增（A）
- 涉及模块：订单录入（后端逻辑）
- 变更内容：实现订单录入领域模型与服务（`test_impl/order_management/order_entry/`），含状态枚举、金额计算、唯一性与审核校验。
- 验证：单元测试 4/4 通过（`tests/test_order_entry_service.py`）。
- SOP 同步：不涉及操作变更。

### CL-0002 · 2026-05-28 · 文档（A）
- 涉及模块：订单管理（全模块）
- 变更内容：固化订单管理 6 个子模块边界、状态机、数据对象与发布门禁（`docs/change/order-module-v1.md`），建立变更单 CR-0001。
- 验证：文档评审。
- SOP 同步：不涉及操作变更。

### CL-0001 · 2026-05-28 · 文档（A）
- 涉及模块：全局治理
- 变更内容：建立 ERP 框架准则与隔离开发流程（`docs/change/erp-governance-v1.md`），搭建 `src/test_impl/tests/scripts` 骨架及 `verify/promote/rollback` 脚本。
- 验证：`scripts/verify.ps1` 通过。
- SOP 同步：不涉及操作变更。

---

## 待办（下一步计划 · v0.5.0 候选）

- 对账子模块
- 送货单多模板 / 客户定制扩展
- 可选恢复百度 OCR 双路对比
- 新模块 UI 须遵循 `docs/design/ui-style-guide-v1.md`
