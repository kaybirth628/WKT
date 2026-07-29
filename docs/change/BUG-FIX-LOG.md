# WKT · Bug 修复日志（BUG-FIX-LOG）

> **规则**：凡 CHANGELOG 类型为 **修复** 的 CL，**同一任务内**在此登记 **BF-XXXX**（递增不复用）。  
> Agent **修 Bug 前**先查本文件，避免相同错误反复发生。  
> 合规流程见 [`AGENT-COMPLIANCE.md`](AGENT-COMPLIANCE.md)。

---

## 登记格式

| 字段 | 说明 |
|------|------|
| BF 编号 | BF-XXXX |
| 关联 CL | CL-XXXX |
| 模块 | 子系统/文件 |
| 现象 | 用户可见失败表现 |
| 根因 | 技术/业务原因 |
| 修复 | 解决方案摘要 |
| 防复发 | 测试、SOP、规则、代码约束 |
| 验证 | 如何确认已修复 |

---

## 索引（按模块）

| 模块 | BF 编号 |
|------|---------|
| BOM 批量导入 | BF-0001～BF-0008、BF-0013、BF-0014 |
| BOM 查询 | BF-0006、BF-0015 |
| BOM 录入 | BF-0016、BF-0017、BF-0018 |
| Agent 治理 | BF-0009 |
| Git 推送 | BF-0010 |
| OCR 识别 | BF-0011 |
| 工序库存 | BF-0012 |

---

## 变更记录

### BF-0018 · 2026-07-29

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0245 |
| 模块 | `cost_entry.js` |
| 现象 | 本地手速快仍被刷回；云端旧版快操作反而不复现；员工慢操作也投诉 |
| 根因 | 快网络 lookup 完成早于用户点击，立即 `applyProcessPrices`；下拉选料号误清 `processGridTouched` |
| 修复 | 工序回填延迟 400ms，期间 mousedown 即视为手工编辑并取消回填；去掉 onSelect 清标记 |
| 防复发 | `test_bom_entry_lookup_race.py` |
| 验证 | Tab 料号后 400ms 内点工序应保留 |

### BF-0017 · 2026-07-29

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0244 |
| 模块 | `cost_entry.js` |
| 现象 | 员工手速快时 BOM 录入工序/供应商刚勾选就被刷没，本地可稳定复现 |
| 根因 | 用户先改工序或 lookup 未完成时编辑，返回后 `applyProcessPrices` 仍整段覆盖 |
| 修复 | `processGridTouched`：已手工编辑则 lookup 跳过工序回填；去掉 blur 双次 lookup |
| 防复发 | `test_bom_entry_lookup_race.py` 场景2 |
| 验证 | 先勾「烤漆」再填料号 → 载入后仍保留 |

### BF-0016 · 2026-07-29

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0243 |
| 模块 | `cost_entry.js` |
| 现象 | BOM 录入勾选工序、添加供应商到一半，工序区突然全部回到未勾选/供应商清空；订单模块无此反馈 |
| 根因 | 料号 lookup 异步返回时 `applyProcessPrices` 先取消全部工序再回填；若 BOM 无已存工序则 early return 导致整页工序被清空；用户可在 lookup 完成前编辑，产生竞态 |
| 修复 | 先构建工序 map，无数据则不改动 DOM；lookup in-flight 锁定工序区并提示；忽略过期 lookup 响应 |
| 防复发 | 手工：录料号后立即点工序应短暂不可点；空工序 BOM 载入不清空已勾选项 |
| 验证 | BOM 录入页 Ctrl+F5 后复测；不涉及数据库变更 |

### BF-0014 · 2026-07-29

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0218 |
| 模块 | `bom_form_import.py` |
| 现象 | `11*000000/08016-01` 被拆成 `11*000000` 与 `08016-01` 两条 BOM |
| 根因 | 料号与品名共用 `/` 分隔逻辑 |
| 修复 | 料号仅换行拆分；`/` 原样保留 |
| 防复发 | `test_part_no_slash_preserved_ruiba` |
| 验证 | 锐霸 819/826/826A 头壳各 1 条完整料号 |

### BF-0013 · 2026-07-29

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0217 |
| 模块 | `bom_form_import.py` |
| 现象 | 多 Sheet Excel 批量导入后只余 1 条 BOM，品名如 `SD-819/826/826A头壳`、料号 `11000061.0` |
| 根因 | 各 Sheet 共用表头（多型号品名 + 相同客户料号）；解析未按 Sheet 区分，导入时同料号互相覆盖 |
| 修复 | 一 Sheet 一 BOM：表内品名含 `/` 或 workbook 内料号重复时，按 Sheet 名生成独立料号/品名；Excel 数值料号去 `.0` |
| 防复发 | `test_one_sheet_one_bom_shared_header`、`test_coerce_excel_float_part_no` |
| 验证 | `python -m unittest discover -s tests -p test_bom_form_import.py` |

### BF-0012 · 2026-07-28

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0209 |
| 模块 | `inventory/service.py` · 流动记录展示 |
| 现象 | 载入 TST-PL-002 报 `Unexpected token '<'`；004 正常 |
| 根因 | `_movement_route_display` 的 `stage_flow` 分支使用未定义变量 `from_st` |
| 修复 | 从 row 读取 `from_status`/`to_status` 再拼接展示 |
| 防复发 | `test_stage_flow_movement_route_display` |
| 验证 | 002/004 均可 `list_movements`；页面载入无红字 |

### BF-0011 · 2026-07-28

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0205 |
| 模块 | `order_intake/deepseek.py`、`part_no_fill.py` |
| 现象 | 苏州大沃 PO 表格「物料编码」列有值（如 1-000797），识别后 10 行全部「客户料号为空」 |
| 根因 | DeepSeek SYSTEM_PROMPT 规则 8 仅认「客户料号/料号」列且举例 B 开头；该客户用「物料编码」列名、原始编码为空 |
| 修复 | 提示词增加物料编码/物料号/原始编码映射；`fill_part_no_from_raw_text` 从 OCR 原文按行或顺序补全 |
| 防复发 | `test_fill_dawo_material_code_by_product_spec`；`test_material_code_format_ok` |
| 验证 | 单元测试通过；重启后上传 `苏州大沃-威可特6.11.1.pdf` 应带出 1-000797 等料号 |

### BF-0010 · 2026-07-28

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0204 |
| 模块 | `git-push.ps1` |
| 现象 | 一键推送云端和 GitHub 报 Refusing to commit order database files，列出大量 data.local.bak-* |
| 根因 | 本地备份目录未 ignore，git add -A 暂存备份内 wkt_orders.db / .db.bak |
| 修复 | gitignore + Invoke-SafeGitStage 提交前 unstage |
| 防复发 | CL-0204；gitignore |
| 验证 | 推送 bat commit 步骤通过 |

### BF-0009 · 2026-07-28

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0200 |
| 模块 | Agent 工作流 / 文档 |
| 现象 | 多次改动未同步 SOP；Bug 修复未记根因，相同问题重复排查 |
| 根因 | 仅有 CHANGELOG 头部规则，无独立 BF 日志与强制 checklist；CL 大量标 SOP=否 无原因 |
| 修复 | 新增 `AGENT-COMPLIANCE.md`、`BUG-FIX-LOG.md`、`.cursor/rules/wkt-change-governance.mdc`；补写 SOP BOM § |
| 防复发 | Agent 规则 alwaysApply；修 Bug 前必读 BUG-FIX-LOG；CL 模板增加根因/防复发字段 |
| 验证 | 文档存在；SOP §4.1 与 CL-0194～0197 一致 |

### BF-0008 · 2026-07-28

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0195 |
| 模块 | `cost_bom_import.js` |
| 现象 | 批量上传「成功」后界面仍像选文件/预览前，用户以为没导入 |
| 根因 | 成功后仍保留预览区或 silent re-parse，成功提示被覆盖 |
| 修复 | `resetToUploadScreen()`：清空预览、恢复上传卡、绿色成功横幅（含查询链接）；不再成功后自动 re-parse |
| 防复发 | 手动验证导入流程；SOP §4.1 步骤 5 |
| 验证 | 上传成功后见绿色横幅，预览隐藏 |

### BF-0007 · 2026-07-28

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0191 |
| 模块 | `cost_store.py` |
| 现象 | 重复导入覆盖 BOM 后，查询列表里记录仍排在后面，像没更新 |
| 根因 | 排序用 `created_at`；且 SQLite `datetime()` 无法解析 ISO 带时区字符串，ORDER BY 失效回退 id |
| 修复 | 改为 `ORDER BY updated_at DESC`；解析 updated_at 时去掉时区或统一格式 |
| 防复发 | `test_list_records_ordered_by_updated_at` |
| 验证 | 重复导入同一 Excel 后，查询顶部为刚覆盖记录 |

---

## 记录

### BF-0016 · 2026-07-29

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0243 |
| 模块 | `cost_entry.js` |
| 现象 | BOM 录入勾选工序、添加供应商到一半，工序区突然全部回到未勾选/供应商清空；订单模块无此反馈 |
| 根因 | 料号 lookup 异步返回时 `applyProcessPrices` 先取消全部工序再回填；若 BOM 无已存工序则 early return 导致整页工序被清空；用户可在 lookup 完成前编辑，产生竞态 |
| 修复 | 先构建工序 map，无数据则不改动 DOM；lookup in-flight 锁定工序区并提示；忽略过期 lookup 响应 |
| 防复发 | 手工：录料号后立即点工序应短暂不可点；空工序 BOM 载入不清空已勾选项 |
| 验证 | BOM 录入页 Ctrl+F5 后复测；不涉及数据库变更 |

### BF-0015 · 2026-07-29

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0224 |
| 模块 | `cost_query.js`、`cost_common.js` |
| 现象 | BOM 查询点 **修改** 后填表，界面突然回到列表（编辑弹窗关闭），本人难复现、员工常遇到 |
| 根因 | ① 工序 **供应商** 搜索框按 **Esc** 关下拉时事件冒泡，全局 Esc 同时关闭编辑弹窗；② 文本框按 **Enter** 触发表单默认提交（校验通过则保存并关窗）；③ 误点弹窗外灰色遮罩会关窗 |
| 修复 | 供应商 Esc/Enter `stopPropagation`；编辑表单 Enter 不默认提交；取消遮罩点击关窗；Esc 优先关下拉再关弹窗 |
| 防复发 | 手工：修改 BOM → 外发供应商字段按 Esc/Enter |
| 验证 | 弹窗保持打开；仅点「关闭/取消」或 Esc（下拉已关）才退出 |

### BF-0006 · 2026-07-28

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0189 |
| 模块 | `cost_bom_import.js`、`cost_query.js` |
| 现象 | 导入显示成功但 BOM 查询「找不到」；或导入后无任何成功提示 |
| 根因 | ① 查询用客户 **精确匹配**，简称「大沃」与档案全称不一致；② 成功 UI 被后续 parse 清掉或未渲染结果区 |
| 修复 | 查询客户 **模糊匹配** + URL `?q=`；导入结果横幅保留明细与「前往 BOM 查询」链接；payload 展开客户别名 |
| 防复发 | `test_bom_form_import` 别名相关用例；SOP §七 |
| 验证 | 导入后见结果横幅；`/bom/query?q=大沃` 能搜到 |

### BF-0005 · 2026-07-28

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0190 |
| 模块 | `record_service.py`、`bom_form_import.py` |
| 现象 | 重复上传同一 Excel 产生重复料号；或覆盖时因客户简称/全称不一致失败 |
| 根因 | 覆盖键不明确；覆盖更新仍做客户严格校验 |
| 修复 | **仅按 `product_part_no` 覆盖**，后导入胜；覆盖时 `skip_customer_check=True` |
| 防复发 | `test_import_overwrite_reupload_same_excel`、`test_import_overwrite_same_part_different_customer_alias` |
| 验证 | 同一文件上传两次，库内每料号一行且为最新数据 |

### BF-0004 · 2026-07-28

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0188 |
| 模块 | `bom_form_import.py` |
| 现象 | 文件名 `大沃产品BOM(1)(1)` 误报客户未匹配；表内已识别客户仍显示文件名错误 |
| 根因 | 文件名剥离 copy 后缀规则不全；顶栏 meta 优先文件名错误而非 sheet 客户 |
| 修复 | 增强文件名解析；`preview_meta` 优先 sheet 已匹配客户；新增「大沃」别名 |
| 防复发 | `test_filename_dawo_product_bom_copy_suffix`、`test_preview_meta_uses_sheet_customer_when_filename_fails` |
| 验证 | 上述 xlsx 文件名解析预览通过 |

### BF-0003 · 2026-07-28

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0186 |
| 模块 | `bom_form_import.py` |
| 现象 | BOM 导入客户匹配到 **供应商** 档案（如大沃），客户错误 |
| 根因 | CL-0185 误将 BOM 客户匹配逻辑改为供应商档案 |
| 修复 | BOM 导入 **只匹配客户档案**；工序供应商按 Excel 原文写入 |
| 防复发 | `test_sheet_customer_short_name_resolved_on_preview`；代码注释区分客户/供应商 |
| 验证 | 东硕/大沃 BOM 预览客户为客商全称 |

### BF-0002 · 2026-07-28

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0192 |
| 模块 | BOM 导入预览 |
| 现象 | 东硕 BOM 等文件 DLS/XFT 客户识别错误，整批 **阻断** 无法导入 |
| 根因 | 文件名/表内客户与档案不完全一致；阻断级校验过严 |
| 修复 | 预览表 **可编辑客户**；「统一客户」批量应用；`POST .../revalidate` 再导入 |
| 防复发 | `test_revalidate_manual_customer_unblocks_row`；SOP §4.1 步骤 3 |
| 验证 | 批量改客户后 revalidate，阻断行变通过/待核 |

### BF-0001 · 2026-07-28

| 字段 | 内容 |
|------|------|
| 关联 CL | CL-0189 |
| 模块 | BOM 导入 commit |
| 现象 | 预览「导入通过+待核」后无成功反馈，用户重复操作 |
| 根因 | 前端未持久展示 commit 结果；或结果被后续请求覆盖 |
| 修复 | 独立结果区 + 成功横幅；见 BF-0006、BF-0008 |
| 防复发 | 与 BF-0006、BF-0008 一并解决 |
| 验证 | 见 CL-0189、CL-0195 验证项 |

---

## Agent 备忘

- 修 BOM 导入/查询问题：**先读 BF-0001～BF-0008**
- 新增 BF 时更新上方 **索引表**
- 若 Bug 与已有 BF 相同根因复发：新增 BF 并在旧 BF 的「防复发」补强化措施，不要 silent 重复 CL 不写 BF
