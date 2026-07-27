# BOM Excel 数据清洗 · 待审计文件放这里

把需要清洗的 BOM Excel（`.xls` / `.xlsx`）**复制到此目录**，然后：

```powershell
cd P:\WKT
python scripts/audit_bom_excel.py
```

会生成 **`audit_report.md`**：列出所有模糊点（客户、料号、工序别名、缺失字段、跨文件冲突等），供你找员工逐条确认。

## 文件命名建议

- `东硕BOM.xls` → 系统自动匹配客户「苏州鑫福泰电子科技有限公司-东硕」
- 每个 sheet 一个产品（sheet 名常为料号，如 `HUV9142V1`）

## 确认后

- 在 `audit_report.md` 的「确认结果」列填写员工答复
- 确认无误后在 **BOM录入 → BOM 表单批量导入** 上传同一文件导入
