# -*- coding: utf-8 -*-
"""核对客户标注的锐霸 BOM 清单 vs Excel 解析 vs 系统库。"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from test_impl.order_management.cost_analysis.bom_form_import import (
    parse_bom_workbook,
    preview_import_batch,
)
from test_impl.order_management.cost_analysis.cost_store import CostStore

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "wkt_orders.db"
XLS = ROOT / "Demo" / "BOM" / "锐霸产品BOM.xls"
OUT = ROOT / "data" / "bom_import_audit" / "ruiba_customer_checklist_audit.md"

# 客户标注清单（来自核对表截图）
CUSTOMER_ITEMS: list[str] = [
    "819/826/826A (头壳通用端盖)",
    "826头壳（含轴套）",
    "819/826/826A (世达款) (头壳通用端盖)",
    "826A头壳（含轴套）",
    "826头壳 (世达款)",
    "826A头壳 (世达款)",
    "起子机2108-W头壳 (230N头壳无轴套)",
    "起子机2108头壳-锐霸灰色 (230N头壳含轴套)",
    "起子机2108-W头壳 (230N头壳无轴套)-黑色",
    "230N 起子机头壳 世达款",
    "起子机2108-L头壳含轴套 (世达款)",
    "扳手818端盖",
    "扳手818头壳 (带花纹含轴套)",
    "扳手818头壳-不带花纹 (无轴套)",
    "扳手818S SATA头壳 (世达)",
    "扳手818S SATA端盖 (世达)",
    "扳手809头壳(含轴套)",
    "扳手809头壳-黑色 (TRU)",
    "扳手809端盖",
    "扳手809S SATA头壳 (世达)",
    "扳手810头壳 (无轴套)",
    "扳手810端盖",
    "扳手810端盖(黑色)",
    "扳手810STK2头壳",
    "扳手810STK2头壳 (黑色)",
    "扳手810S SATA 端盖 (世达)",
    "扳手810S头壳 世达款",
    "2109左卡钳",
    "2109右卡钳",
    "左卡钳 (黑色)",
    "右卡钳 (黑色)",
    "电钻2118左卡钳",
    "电钻2118右卡钳",
    "扳手828头壳",
    "扳手828端盖",
    "扳手828把手支架",
    "827头壳 (带轴套)",
    "827立式副把手旋钮",
    # 右侧标注：配件也要添加
    "806轴套 (DTW380输出轴套)",
    "扳手809轴套 (500N轴套)",
    "2108起子机轴套 (230N轴套)",
    "819/826轴套",
    "826A轴套",
    "810S轴套",
    "827轴套",
    "806S轴套世达款",
    "2108L轴套世达款",
]


def norm_name(s: str) -> str:
    s = str(s or "").strip().lower()
    s = s.replace("（", "(").replace("）", ")")
    s = s.replace(" ", "").replace("\u3000", "")
    s = re.sub(r"[·\-—–_]", "", s)
    return s


def tokens(s: str) -> set[str]:
    s = norm_name(s)
    found = set(re.findall(r"[a-z0-9\u4e00-\u9fff]+", s))
    return {t for t in found if len(t) >= 2 or t.isdigit()}


def score_match(label: str, candidate: str) -> float:
    """简单模糊分：标签 token 在候选名中的覆盖率。"""
    lt = tokens(label)
    ct = norm_name(candidate)
    if not lt:
        return 0.0
    if norm_name(label) in norm_name(candidate) or norm_name(candidate) in norm_name(label):
        return 1.0
    hit = sum(1 for t in lt if t in ct)
    return hit / len(lt)


def best_match(label: str, candidates: list[dict], *, field: str = "product_name") -> tuple[dict | None, float]:
    best: dict | None = None
    best_score = 0.0
    for row in candidates:
        sc = score_match(label, str(row.get(field) or ""))
        if sc > best_score:
            best_score = sc
            best = row
    if best_score < 0.45:
        return None, best_score
    return best, best_score


def load_db_ruiba() -> list[dict]:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, customer_name, product_name, product_part_no, updated_at, created_at
        FROM cost_records
        WHERE customer_name LIKE '%锐霸%'
        ORDER BY updated_at DESC, id DESC
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def load_excel_ruiba() -> list[dict]:
    parsed = parse_bom_workbook(XLS.read_bytes(), filename=XLS.name)
    store = CostStore(db_path=":memory:")
    batch = preview_import_batch(
        parsed,
        store=store,
        filename=XLS.name,
        customer_names=["苏州锐霸智能科技有限公司"],
    )
    out = []
    for item in batch["items"]:
        p = item.get("parsed") or {}
        out.append(
            {
                "sheet_name": item.get("sheet_name") or "",
                "product_name": p.get("product_name") or "",
                "product_part_no": p.get("product_part_no") or "",
            }
        )
    return out


def main() -> None:
    db_rows = load_db_ruiba()
    excel_rows = load_excel_ruiba()
    # 优先用 7/29 最新批次
    latest_prefix = max((str(r["updated_at"])[:19] for r in db_rows), default="")
    db_latest = [r for r in db_rows if str(r["updated_at"])[:19] == latest_prefix]

    lines: list[str] = [
        "# 锐霸 BOM 客户清单核对",
        "",
        f"- 客户标注项：**{len(CUSTOMER_ITEMS)}**",
        f"- Excel 解析（`锐霸产品BOM.xls`）：**{len(excel_rows)}** 行",
        f"- 系统锐霸 BOM：**{len(db_rows)}** 条（最新批次 `{latest_prefix}`：**{len(db_latest)}** 条）",
        "",
        "## 逐项核对",
        "",
        "| # | 客户清单 | Excel | 系统(最新批次) | 备注 |",
        "|---|----------|-------|----------------|------|",
    ]

    stats = {"excel_and_db": 0, "excel_only": 0, "db_only_guess": 0, "missing_both": 0}

    for i, label in enumerate(CUSTOMER_ITEMS, 1):
        ex, ex_sc = best_match(label, excel_rows)
        db, db_sc = best_match(label, db_latest)
        ex_txt = "—"
        db_txt = "—"
        note_parts: list[str] = []

        if ex:
            ex_txt = f"✓ {ex['product_name']} (`{ex['product_part_no']}`)"
        if db:
            db_txt = f"✓ {db['product_name']} (`{db['product_part_no']}`)"

        if ex and db:
            stats["excel_and_db"] += 1
            if norm_name(ex["product_name"]) != norm_name(db["product_name"]):
                note_parts.append("Excel/系统品名略有差异")
        elif ex and not db:
            stats["excel_only"] += 1
            note_parts.append("Excel有，最新批次未入库")
        elif db and not ex:
            stats["db_only_guess"] += 1
            note_parts.append("系统有，Excel未匹配到（可能品名不同）")
        else:
            stats["missing_both"] += 1
            note_parts.append("**Excel与系统均未匹配**")

        if ex_sc and ex_sc < 0.75:
            note_parts.append(f"Excel匹配置信偏低({ex_sc:.0%})")
        if db_sc and db_sc < 0.75:
            note_parts.append(f"系统匹配置信偏低({db_sc:.0%})")

        lines.append(
            f"| {i} | {label} | {ex_txt} | {db_txt} | {'；'.join(note_parts) or '—'} |"
        )

    lines.extend(
        [
            "",
            "## 汇总",
            "",
            f"- 客户清单中 **Excel+系统均有**：{stats['excel_and_db']} 项",
            f"- **仅 Excel 有**（待入库或品名差异）：{stats['excel_only']} 项",
            f"- **仅系统有**（Excel 未对上）：{stats['db_only_guess']} 项",
            f"- **两边都未匹配**：{stats['missing_both']} 项",
            "",
            "## 系统最新批次有、但不在客户 46 项清单内的品名（抽样）",
            "",
        ]
    )

    matched_db_ids: set[int] = set()
    for label in CUSTOMER_ITEMS:
        db, _ = best_match(label, db_latest)
        if db:
            matched_db_ids.add(int(db["id"]))

    extras = [r for r in db_latest if int(r["id"]) not in matched_db_ids]
    lines.append(f"共 **{len(extras)}** 条未与客户清单对上：")
    lines.append("")
    for r in extras[:30]:
        lines.append(f"- `{r['product_part_no']}` · {r['product_name']} (id {r['id']})")
    if len(extras) > 30:
        lines.append(f"- … 还有 {len(extras) - 30} 条")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT)
    print("SUMMARY", stats)


if __name__ == "__main__":
    main()
