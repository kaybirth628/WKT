#!/usr/bin/env python3
"""扫描待导入 BOM Excel，生成「需找员工确认」清单。

用法:
  python scripts/audit_bom_excel.py
  python scripts/audit_bom_excel.py path/to/file.xls path/to/dir

默认扫描: data/bom_import_audit/
输出:     data/bom_import_audit/audit_report.md
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_impl.order_management.cost_analysis.bom_form_import import (
    parse_bom_workbook,
    preview_import_batch,
)
from test_impl.order_management.cost_analysis.cost_store import CostStore, normalize_part_no
from test_impl.order_management.customer_name import (
    extract_customer_hint_from_filename,
    resolve_customer_from_hint,
)
from test_impl.order_management.customer_profile.store import list_profile_customers
from test_impl.order_management.order_entry.line_store import default_db_path

DEFAULT_IN = ROOT / "data" / "bom_import_audit"
DEFAULT_OUT = DEFAULT_IN / "audit_report.md"

_SEVERITY_ORDER = {"必确认": 0, "建议确认": 1, "提示": 2}


@dataclass
class AuditItem:
    file: str
    sheet: str
    category: str
    severity: str
    question: str
    detail: str = ""


def _load_customer_names() -> List[str]:
    names: Set[str] = set(list_profile_customers())
    profiles = ROOT / "data" / "customer_profiles.json"
    if profiles.is_file():
        try:
            data = json.loads(profiles.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                names.update(str(k).strip() for k in data if str(k).strip())
        except (OSError, ValueError):
            pass
    return sorted(names)


def _collect_files(paths: List[Path]) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        if p.is_file() and p.suffix.lower() in (".xls", ".xlsx", ".xlsm"):
            files.append(p)
        elif p.is_dir():
            for ext in ("*.xls", "*.xlsx", "*.xlsm"):
                files.extend(sorted(p.glob(ext)))
    seen: Set[str] = set()
    out: List[Path] = []
    for f in files:
        key = str(f.resolve()).casefold()
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def _add(items: List[AuditItem], **kwargs) -> None:
    items.append(AuditItem(**kwargs))


def audit_file(path: Path, store: CostStore, customer_names: List[str]) -> List[AuditItem]:
    items: List[AuditItem] = []
    fname = path.name
    hint = extract_customer_hint_from_filename(fname)
    resolved, customer_err = resolve_customer_from_hint(hint, customer_names)

    if customer_err:
        _add(
            items,
            file=fname,
            sheet="—",
            category="客户",
            severity="必确认",
            question=f"文件名「{hint or fname}」无法匹配系统客户，请确认是否已在客商信息维护建档？",
            detail=customer_err,
        )
    elif hint and resolved:
        _add(
            items,
            file=fname,
            sheet="—",
            category="客户",
            severity="提示",
            question=f"文件名简称「{hint}」将导入为客户「{resolved}」，是否正确？",
            detail="",
        )

    try:
        raw = path.read_bytes()
    except OSError as exc:
        _add(
            items,
            file=fname,
            sheet="—",
            category="文件",
            severity="必确认",
            question="文件无法读取，请检查是否损坏或被占用",
            detail=str(exc),
        )
        return items

    try:
        parsed = parse_bom_workbook(raw, filename=fname)
    except ValueError as exc:
        _add(
            items,
            file=fname,
            sheet="—",
            category="文件",
            severity="必确认",
            question="Excel 解析失败，请确认格式或另存为 .xlsx",
            detail=str(exc),
        )
        return items

    if not parsed:
        _add(
            items,
            file=fname,
            sheet="—",
            category="文件",
            severity="必确认",
            question="未解析到任何有效 sheet，是否为空表或非 BOM 格式？",
            detail="",
        )
        return items

    batch = preview_import_batch(
        parsed,
        store=store,
        filename=fname,
        customer_names=customer_names,
    )

    for preview in batch["items"]:
        sheet = str(preview.get("sheet_name") or "")
        row = preview.get("parsed") or {}
        part = normalize_part_no(str(row.get("product_part_no") or ""))
        tier = str(preview.get("tier") or "")
        issues = list(preview.get("issues") or [])

        if tier == "blocked":
            for issue in issues:
                sev = "必确认"
                if issue.startswith("料号已存在"):
                    q = f"料号「{part or sheet}」系统中已有 BOM，是跳过、覆盖还是合并？"
                elif "未找到客户" in issue or "未找到客户" in issue:
                    q = "请确认该料号归属哪个客户"
                elif "未解析" in issue or "制程" in issue:
                    q = f"sheet「{sheet}」制程/工序无法识别，请对照 Excel 确认工序名称"
                elif "无法识别工序" in issue:
                    q = f"工序「{issue}」应映射为系统哪道工序？"
                else:
                    q = issue
                _add(
                    items,
                    file=fname,
                    sheet=sheet,
                    category="阻断",
                    severity=sev,
                    question=q,
                    detail=issue,
                )

        if tier == "pending":
            for issue in issues:
                if issue.startswith("缺少"):
                    _add(
                        items,
                        file=fname,
                        sheet=sheet,
                        category="缺失字段",
                        severity="建议确认",
                        question=f"「{part or sheet}」{issue}，请补填或确认可否先用默认值导入",
                        detail=issue,
                    )
                elif "工序" in issue:
                    _add(
                        items,
                        file=fname,
                        sheet=sheet,
                        category="工序",
                        severity="建议确认",
                        question=f"「{part or sheet}」{issue}",
                        detail=issue,
                    )
                elif "外发工序" in issue and "供应商" in issue:
                    _add(
                        items,
                        file=fname,
                        sheet=sheet,
                        category="供应商",
                        severity="建议确认",
                        question=f"「{part or sheet}」{issue}，供应商是否已在系统建档？",
                        detail=issue,
                    )
                else:
                    _add(
                        items,
                        file=fname,
                        sheet=sheet,
                        category="待核",
                        severity="建议确认",
                        question=issue,
                        detail=issue,
                    )

        # 料号来自 sheet 名时的确认
        if part and part == normalize_part_no(sheet):
            _add(
                items,
                file=fname,
                sheet=sheet,
                category="料号",
                severity="建议确认",
                question=f"料号取自 sheet 名「{sheet}」，与 Excel 内实际客户料号是否一致？",
                detail=f"产品名称: {row.get('product_name', '')}",
            )

        for proc in row.get("processes") or []:
            raw_name = str(proc.get("raw_name") or "")
            mapped = str(proc.get("name") or "")
            if raw_name and mapped and raw_name != mapped:
                _add(
                    items,
                    file=fname,
                    sheet=sheet,
                    category="工序别名",
                    severity="建议确认",
                    question=f"Excel 写「{raw_name}」，系统按「{mapped}」导入，是否正确？",
                    detail=f"料号: {part or sheet}",
                )
            sup = str(proc.get("supplier") or "").strip()
            if sup and sup not in ("", "场内自制") and not is_inhouse_supplier_name(sup):
                _add(
                    items,
                    file=fname,
                    sheet=sheet,
                    category="供应商",
                    severity="建议确认",
                    question=f"外发供应商「{sup}」（工序 {mapped or raw_name}）是否已在供应商信息维护建档？",
                    detail=f"料号: {part or sheet}",
                )

    return items


def is_inhouse_supplier_name(name: str) -> bool:
    return name in ("厂内", "场内", "场内自制", "自制")


def audit_all(files: List[Path], store: CostStore, customer_names: List[str]) -> List[AuditItem]:
    all_items: List[AuditItem] = []
    part_sources: Dict[str, List[str]] = defaultdict(list)

    for path in files:
        all_items.extend(audit_file(path, store, customer_names))

    # 跨文件料号冲突
    for path in files:
        try:
            parsed = parse_bom_workbook(path.read_bytes(), filename=path.name)
        except ValueError:
            continue
        for row in parsed:
            part = normalize_part_no(str(row.get("product_part_no") or ""))
            if part:
                part_sources[part].append(f"{path.name}/{row.get('sheet_name', '')}")

    for part, sources in part_sources.items():
        if len(sources) > 1:
            all_items.append(
                AuditItem(
                    file="跨文件",
                    sheet="—",
                    category="料号冲突",
                    severity="必确认",
                    question=f"料号「{part}」在多个 sheet/文件中出现，是否为同一产品？",
                    detail="；".join(sources[:8])
                    + (f" 等{len(sources)}处" if len(sources) > 8 else ""),
                )
            )

    all_items.sort(
        key=lambda x: (
            _SEVERITY_ORDER.get(x.severity, 9),
            x.file,
            x.sheet,
            x.category,
        )
    )
    return all_items


def render_markdown(items: List[AuditItem], files: List[Path]) -> str:
    lines = [
        "# BOM Excel 导入 · 待确认清单",
        "",
        f"- 扫描文件数：**{len(files)}**",
        f"- 待确认条目：**{len(items)}**",
        f"- 必确认：**{sum(1 for i in items if i.severity == '必确认')}**",
        f"- 建议确认：**{sum(1 for i in items if i.severity == '建议确认')}**",
        "",
        "> 请逐条找对应员工确认，在「确认结果」列填写后交回 IT 导入。",
        "",
    ]
    if not items:
        lines.append("未发现待确认项（或目录内无 Excel 文件）。")
        return "\n".join(lines)

    lines.extend(
        [
            "| # | 级别 | 文件 | Sheet | 类别 | 待确认问题 | 详情 | 确认结果 |",
            "|---|------|------|-------|------|------------|------|----------|",
        ]
    )
    for idx, item in enumerate(items, start=1):
        q = item.question.replace("|", "\\|")
        d = (item.detail or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {idx} | {item.severity} | {item.file} | {item.sheet} | "
            f"{item.category} | {q} | {d} |  |"
        )
    lines.append("")
    lines.append("## 扫描文件列表")
    lines.append("")
    for f in files:
        lines.append(f"- `{f.name}`")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if args:
        paths = [Path(a) for a in args]
    else:
        paths = [DEFAULT_IN]

    files = _collect_files(paths)
    store = CostStore(db_path=default_db_path())
    try:
        customer_names = _load_customer_names()
        items = audit_all(files, store, customer_names)
        out_path = DEFAULT_OUT if not args else Path(args[-1]) / "audit_report.md" if len(args) == 1 and Path(args[0]).is_dir() else DEFAULT_OUT
        if args and len(args) == 1 and Path(args[0]).is_dir():
            out_path = Path(args[0]) / "audit_report.md"
        DEFAULT_IN.mkdir(parents=True, exist_ok=True)
        md = render_markdown(items, files)
        out_path.write_text(md, encoding="utf-8")
        print(f"Scanned {len(files)} file(s), {len(items)} item(s)")
        print(f"Report: {out_path}")
        return 0 if files else 1
    finally:
        store._conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
