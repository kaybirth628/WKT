#!/usr/bin/env python3
"""输出 BOM 审计摘要（UTF-8）。"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_bom_excel import _collect_files, _load_customer_names, audit_all
from test_impl.order_management.cost_analysis.bom_form_import import (
    parse_bom_workbook,
    preview_import_batch,
)
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.order_entry.line_store import default_db_path

IN_DIR = ROOT / "data" / "bom_import_audit"
OUT = IN_DIR / "audit_summary.md"


def main() -> None:
    files = _collect_files([IN_DIR])
    customers = _load_customer_names()
    store = CostStore(db_path=default_db_path())
    items = audit_all(files, store, customers)
    store._conn.close()

    lines = [
        "# BOM 导入审计摘要",
        "",
        f"- 文件：**{len(files)}** 个",
        f"- 待确认条目：**{len(items)}**（必确认 {sum(1 for i in items if i.severity == '必确认')} / 建议确认 {sum(1 for i in items if i.severity == '建议确认')}）",
        "",
        "## 各文件概况",
        "",
        "| 文件 | Sheet数 | 通过 | 待核 | 阻断 | 客户匹配 |",
        "|------|---------|------|------|------|----------|",
    ]

    for f in files:
        parsed = parse_bom_workbook(f.read_bytes(), filename=f.name)
        mem = CostStore(":memory:")
        batch = preview_import_batch(
            parsed, store=mem, filename=f.name, customer_names=customers
        )
        mem._conn.close()
        tiers = Counter(p["tier"] for p in batch["items"])
        cust = batch.get("customer_resolved") or batch.get("customer_error", "")
        lines.append(
            f"| {f.name} | {len(batch['items'])} | {tiers.get('passed', 0)} | "
            f"{tiers.get('pending', 0)} | {tiers.get('blocked', 0)} | {cust} |"
        )

    unk = Counter(
        i.detail.replace("无法识别工序：", "")
        for i in items
        if "无法识别工序" in i.detail
    )
    lines.extend(["", "## 无法识别的工序（请统一确认系统映射）", ""])
    for name, cnt in unk.most_common():
        lines.append(f"- **{name}**（{cnt} 次）→ 应映射为系统哪道工序？____")

    alias_qs = sorted(
        {
            i.question
            for i in items
            if i.category in ("工序别名", "阻断") and "按「" in i.question
        }
    )
    lines.extend(["", "## 常见模糊工序别名（抽样确认即可）", ""])
    for q in alias_qs[:30]:
        lines.append(f"- {q}")
    if len(alias_qs) > 30:
        lines.append(f"- … 另有 {len(alias_qs) - 30} 条，见 `audit_report.md`")

    missing = Counter(i.detail for i in items if i.detail.startswith("缺少"))
    lines.extend(["", "## 缺失字段（是否 Excel 里确实没有？）", ""])
    for name, cnt in missing.most_common():
        lines.append(f"- {name}：**{cnt}** 条")

    lines.extend(
        [
            "",
            "## 优先处理（文件名 / 客户）",
            "",
            "| 现文件名 | 问题 | 建议 |",
            "|----------|------|------|",
            "| 日月照明BOM格式.xls | 简称含「BOM格式」未匹配 | 改名为 **日月照明BOM.xls**，或确认对应 **江苏日月照明电器有限公司** |",
            "| 欧菲光BOM.xls | 「欧菲光」未匹配 | 确认是否 **安徽欧菲智能车联科技有限公司** |",
            "| 红黑BOM格式.xls | 简称含「BOM格式」未匹配 | 改名为 **红黑BOM.xls**，或确认 **浙江红黑科技有限公司** |",
            "",
            "完整逐条清单：`data/bom_import_audit/audit_report.md`",
        ]
    )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
