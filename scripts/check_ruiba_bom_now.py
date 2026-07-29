# -*- coding: utf-8 -*-
"""对比本地锐霸 BOM 与 Demo/BOM/锐霸产品BOM.xls 解析结果。"""
from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

from test_impl.order_management.cost_analysis.bom_form_import import (
    parse_bom_workbook,
    preview_import_batch,
)
from test_impl.order_management.cost_analysis.cost_store import (
    CostStore,
    is_unfilled_part_no,
    normalize_part_no,
)

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "wkt_orders.db"
XLS = ROOT / "Demo" / "BOM" / "锐霸产品BOM.xls"
OUT = ROOT / "data" / "bom_import_audit" / "ruiba_check_now.md"


def main() -> None:
    lines: list[str] = []

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, product_part_no, product_name, created_at, updated_at
        FROM cost_records
        WHERE customer_name LIKE '%锐霸%'
        ORDER BY id
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    lines.append(f"# 锐霸 BOM 核对 ({DB.name})\n")
    lines.append(f"- **库内锐霸 BOM 总数**：{len(rows)} 条\n")

    upd = Counter(str(r["updated_at"])[:19] for r in rows)
    lines.append("## 按更新时间批次\n")
    for k, v in upd.most_common(10):
        lines.append(f"- `{k}`：{v} 条")
    lines.append("")

    latest_prefix = max(str(r["updated_at"])[:19] for r in rows)
    latest = [r for r in rows if str(r["updated_at"])[:19] == latest_prefix]
    created_new = [r for r in latest if r["created_at"] == r["updated_at"]]
    updated_old = [r for r in latest if r["created_at"] != r["updated_at"]]
    lines.append(f"## 最近一次上传批次 (`{latest_prefix}`)\n")
    lines.append(f"- 本批触及：**{len(latest)}** 条")
    lines.append(f"- **新增**：{len(created_new)} 条")
    lines.append(f"- **覆盖（created_at 更早）**：{len(updated_old)} 条\n")
    if updated_old:
        lines.append("| id | 料号 | 原创建时间 |")
        lines.append("|----|------|------------|")
        for r in updated_old:
            lines.append(
                f"| {r['id']} | `{r['product_part_no']}` | {r['created_at'][:19]} |"
            )
        lines.append("")

    db_parts: dict[str, list[int]] = {}
    for r in rows:
        p = normalize_part_no(r["product_part_no"])
        db_parts.setdefault(p, []).append(r["id"])
    lines.append(f"- 库内 **不同料号**（含 `/`）：{len(db_parts)} 个\n")

    dup_in_db = {k: v for k, v in db_parts.items() if len(v) > 1}
    if dup_in_db:
        lines.append("## 库内同料号多条（异常）\n")
        for k, ids in sorted(dup_in_db.items(), key=lambda x: -len(x[1])):
            lines.append(f"- `{k}`：{len(ids)} 条 → id {ids}")
        lines.append("")

    conn.close()

    parsed = parse_bom_workbook(XLS.read_bytes(), filename=XLS.name)
    store = CostStore(db_path=":memory:")
    batch = preview_import_batch(
        parsed,
        store=store,
        filename=XLS.name,
        customer_names=["苏州锐霸智能科技有限公司"],
    )
    items = batch["items"]
    excel_parts: list[str] = []
    for item in items:
        p = normalize_part_no((item.get("parsed") or {}).get("product_part_no", ""))
        excel_parts.append(p)

    lines.append("## Excel 解析 (`锐霸产品BOM.xls`)\n")
    lines.append(f"- 解析行数：**{len(items)}**（Sheet 数应对齐）")
    lines.append(
        f"- 档位：通过 {sum(1 for i in items if i['tier']=='passed')} / "
        f"待核 {sum(1 for i in items if i['tier']=='pending')} / "
        f"阻断 {sum(1 for i in items if i['tier']=='blocked')}"
    )
    lines.append(f"- 可导入（通过+待核）：**{len([i for i in items if i['tier'] in ('passed','pending')])}**")
    lines.append(f"- 本批料号重复高亮：**{sum(1 for i in items if i.get('duplicate_part_no'))}** 行\n")

    excel_set = set(excel_parts)
    db_set = set(db_parts.keys())
    both = db_set & excel_set
    db_only = db_set - excel_set
    excel_only = excel_set - db_set

    lines.append("## 料号集合对比\n")
    lines.append(f"| 对比项 | 数量 |")
    lines.append(f"|--------|------|")
    lines.append(f"| Excel 解析行 | {len(excel_parts)} |")
    lines.append(f"| Excel 不同料号 | {len(excel_set)} |")
    lines.append(f"| 库内锐霸记录 | {len(rows)} |")
    lines.append(f"| 库内不同料号 | {len(db_set)} |")
    lines.append(f"| 两边都有 | {len(both)} |")
    lines.append(f"| 仅在库（Excel 已无） | {len(db_only)} |")
    lines.append(f"| 仅在 Excel（库中无） | {len(excel_only)} |")
    lines.append("")

    if db_only:
        lines.append("### 仅在库中（可能是旧导入残留）\n")
        for p in sorted(db_only):
            ids = db_parts[p]
            lines.append(f"- `{p}` → id {ids}")
        lines.append("")

    if excel_only:
        lines.append("### 仅在 Excel（上传应新增但未入库？）\n")
        for p in sorted(excel_only):
            lines.append(f"- `{p}`")
        lines.append("")

    untouched_old = [r for r in rows if str(r["updated_at"])[:19] != latest_prefix]
    lines.append(f"## 未被本次覆盖的旧记录（仍留在库中）\n")
    lines.append(f"- **{len(untouched_old)}** 条（7/28 等历史导入，料号格式与现 Excel 不一致，故未匹配覆盖）\n")

    def _base_part(p: str) -> str:
        p = normalize_part_no(p)
        if p.endswith(".0"):
            stem = p[:-2]
            if stem.replace(".", "", 1).isdigit():
                return stem
        return p

    orphan_pairs: list[tuple] = []
    new_by_part = {
        normalize_part_no(r["product_part_no"]): r
        for r in latest
        if not is_unfilled_part_no(r["product_part_no"])
    }
    for r in untouched_old:
        op = normalize_part_no(r["product_part_no"])
        bp = _base_part(op)
        nr = new_by_part.get(bp)
        if nr:
            orphan_pairs.append((r, nr))
    if orphan_pairs:
        lines.append("### 新旧料号成对残留（语义相同、字符串不同）\n")
        lines.append("| 旧 id | 旧料号 | 新 id | 新料号 |")
        lines.append("|-------|--------|-------|--------|")
        for old, new in orphan_pairs[:25]:
            lines.append(
                f"| {old['id']} | `{old['product_part_no']}` | {new['id']} | `{new['product_part_no']}` |"
            )
        if len(orphan_pairs) > 25:
            lines.append(f"| … | 还有 {len(orphan_pairs) - 25} 对 | | |")
        lines.append("")

    # simulate overwrite if re-import excel now
    would_update = sum(
        1 for p in excel_parts if p in db_parts and not is_unfilled_part_no(p)
    )
    would_create = sum(
        1
        for p in excel_parts
        if p not in db_parts or is_unfilled_part_no(p)
    )
    slash_rows = sum(1 for p in excel_parts if is_unfilled_part_no(p))
    lines.append("## 若再次上传同一 Excel（理论）\n")
    lines.append(f"- 按料号覆盖已有：**约 {would_update - slash_rows}** 条（不含 `/`）")
    lines.append(f"- 新增（含 `/` 占位各建一条）：**约 {would_create}** 条")
    lines.append(f"- Excel 中 `/` 行数：{slash_rows}\n")

    OUT.write_text("\n".join(lines), encoding="utf-8")

    # stdout summary for agent
    print(f"DB={len(rows)} Excel={len(items)} latest_batch={len(latest)} created={len(created_new)} updated={len(updated_old)} untouched_old={len(rows)-len(latest)}")


if __name__ == "__main__":
    main()
