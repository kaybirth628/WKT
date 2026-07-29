# -*- coding: utf-8 -*-
"""客户锐霸清单 vs 系统 BOM — 人工映射核对。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "wkt_orders.db"
OUT = ROOT / "data" / "bom_import_audit" / "ruiba_customer_have_not.md"

# 客户清单 → 系统品名（最新批次）；None 表示没有
MAPPING: list[tuple[str, str | None, str]] = [
    ("819/826/826A (头壳通用端盖)", None, "无单独BOM；Excel合并为 SD-头壳/SD-819端盖"),
    ("826头壳（含轴套）", "826头壳", ""),
    ("819/826/826A (世达款) (头壳通用端盖)", None, "无"),
    ("826A头壳（含轴套）", "826A头壳", ""),
    ("826头壳 (世达款)", None, "无单独世达款"),
    ("826A头壳 (世达款)", None, "无单独世达款"),
    ("起子机2108-W头壳 (230N头壳无轴套)", "起子机2108W头壳", ""),
    ("起子机2108头壳-锐霸灰色 (230N头壳含轴套)", "起子机2108头壳-锐霸灰色（230N头壳含轴套）", ""),
    ("起子机2108-W头壳 (230N头壳无轴套)-黑色", None, "无"),
    ("230N 起子机头壳 世达款", None, "无"),
    ("起子机2108-L头壳含轴套 (世达款)", "SD-2108L起子机头壳", ""),
    ("扳手818端盖", "818端盖", ""),
    ("扳手818头壳 (带花纹含轴套)", "818带花纹头壳", ""),
    ("扳手818头壳-不带花纹 (无轴套)", "818S头壳", ""),
    ("扳手818S SATA头壳 (世达)", "SD-818S头壳", ""),
    ("扳手818S SATA端盖 (世达)", "SD-818S端盖", ""),
    ("扳手809头壳(含轴套)", "809头壳", ""),
    ("扳手809头壳-黑色 (TRU)", None, "无"),
    ("扳手809端盖", "809端盖", ""),
    ("扳手809S SATA头壳 (世达)", "SD-809S（550N）牙箱壳", ""),
    ("扳手810头壳 (无轴套)", "810头壳", ""),
    ("扳手810端盖", "810端盖", ""),
    ("扳手810端盖(黑色)", None, "无"),
    ("扳手810STK2头壳", None, "无"),
    ("扳手810STK2头壳 (黑色)", None, "无"),
    ("扳手810S SATA 端盖 (世达)", "SD-810S端盖", ""),
    ("扳手810S头壳 世达款", "SD-810S头壳", ""),
    ("2109左卡钳", "2109左卡钳", ""),
    ("2109右卡钳", "2109右卡钳", ""),
    ("左卡钳 (黑色)", None, "无"),
    ("右卡钳 (黑色)", None, "无"),
    ("电钻2118左卡钳", "电钻2118左卡钳", ""),
    ("电钻2118右卡钳", "电钻2118右卡钳", ""),
    ("扳手828头壳", "828头壳", ""),
    ("扳手828端盖", "828端盖", ""),
    ("扳手828把手支架", "828副把手支架", ""),
    ("827头壳 (带轴套)", "827头壳", ""),
    ("827立式副把手旋钮", "827旋钮", ""),
    ("806轴套 (DTW380输出轴套)", None, "无"),
    ("扳手809轴套 (500N轴套)", None, "无"),
    ("2108起子机轴套 (230N轴套)", None, "无"),
    ("819/826轴套", None, "无"),
    ("826A轴套", None, "无"),
    ("810S轴套", None, "无"),
    ("827轴套", None, "无"),
    ("806S轴套世达款", None, "无"),
    ("2108L轴套世达款", None, "无"),
]


def main() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT product_name, product_part_no FROM cost_records
        WHERE customer_name LIKE '%锐霸%' AND updated_at LIKE '2026-07-29T03:33:26%'
        """
    )
    db_names = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()

    have: list[str] = []
    not_have: list[str] = []

    for label, sys_name, note in MAPPING:
        if sys_name and sys_name in db_names:
            have.append(f"- **{label}** → 系统：`{sys_name}`（`{db_names[sys_name]}`）")
        elif sys_name:
            # 名称略有差异再模糊找
            found = None
            for n, p in db_names.items():
                if sys_name.replace(" ", "") in n.replace(" ", "") or n.replace(" ", "") in sys_name.replace(" ", ""):
                    found = (n, p)
                    break
            if found:
                have.append(f"- **{label}** → 系统：`{found[0]}`（`{found[1]}`）")
            else:
                not_have.append(f"- **{label}**" + (f"（{note}）" if note else ""))
        else:
            not_have.append(f"- **{label}**" + (f"（{note}）" if note else ""))

    lines = [
        "# 锐霸客户清单 · 系统有无",
        "",
        f"对照：系统最新导入 **{len(db_names)}** 条（苏州锐霸，2026-07-29）",
        "",
        f"## ✅ 有（{len(have)} 项）",
        "",
        *have,
        "",
        f"## ❌ 没有（{len(not_have)} 项）",
        "",
        *not_have,
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(len(have), len(not_have))


if __name__ == "__main__":
    main()
