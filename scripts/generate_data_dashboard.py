#!/usr/bin/env python3
"""生成本地树杈形数据看板（data/dashboard/index.html）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_impl.order_management.data_mapping.service import DataMappingService

OUT_DIR = ROOT / "data" / "dashboard"
TEMPLATE = OUT_DIR / "template.html"
STATUS_LABELS = {
    "complete": "完整",
    "partial": "部分",
    "profile_only": "仅档案",
    "delivery_only": "仅送货单",
    "master_only": "仅主数据",
}
STATUS_COLORS = {
    "complete": "green",
    "partial": "orange",
    "profile_only": "purple",
    "delivery_only": "blue",
    "master_only": "gray",
}


def _leaf(label: str, meta: str = "", hint: str = "", warn: bool = False) -> dict:
    n: dict = {"label": label, "meta": meta}
    if hint:
        n["hint"] = hint
    if warn:
        n["warn"] = True
    return n


def build_overview_map(report: dict) -> dict:
    stats = report.get("stats") or {}
    summary = report.get("summary") or {}
    json_files = {jf["id"]: jf for jf in (report.get("json_files") or [])}
    prof = json_files.get("customer_profiles", {})
    delivery = json_files.get("customer_delivery", {})
    wkt = json_files.get("wkt_company", {})
    recon = json_files.get("reconciliation_config", {})

    base_rows = stats.get("customers", 0) + stats.get("parts", 0) + prof.get("key_count", 0)
    sales_rows = stats.get("order_lines", 0) + stats.get("shipment_events", 0)
    json_rows = (
        prof.get("key_count", 0)
        + delivery.get("key_count", 0)
        + wkt.get("key_count", 0)
        + recon.get("key_count", 0)
    )

    return {
        "title": "数据总览",
        "root": {
            "label": "WKT 本地数据",
            "meta": f"SQLite + JSON · 客户 {summary.get('customers_with_orders', 0)} 家有订单",
        },
        "branches": [
            {
                "id": "base",
                "label": "基础资料",
                "color": "blue",
                "summary": f"3 源 · {base_rows} 行/键",
                "leaves": [
                    _leaf("customers", f"{stats.get('customers', 0)} 行", "name 唯一 · 客户主数据"),
                    _leaf("parts", f"{stats.get('parts', 0)} 行", "product_spec 唯一 · 品名料号"),
                    _leaf("customer_profiles.json", f"{prof.get('key_count', 0)} 键", "键名 = 客户名称"),
                ],
            },
            {
                "id": "sales",
                "label": "销售 · 订单出货",
                "color": "orange",
                "summary": f"2 表 · {sales_rows} 行",
                "leaves": [
                    _leaf("order_lines", f"{stats.get('order_lines', 0)} 行", "customer 文本 · 无 FK"),
                    _leaf("shipment_events", f"{stats.get('shipment_events', 0)} 行", "line_id → order_lines.id"),
                ],
            },
            {
                "id": "json",
                "label": "JSON 配置",
                "color": "purple",
                "summary": f"4 文件 · {json_rows} 项",
                "leaves": [
                    _leaf("customer_delivery.json", f"{delivery.get('key_count', 0)} 键", "送货单 · 键=客户名"),
                    _leaf("wkt_company.json", f"{wkt.get('key_count', 0)} 项", "威可特抬头"),
                    _leaf(
                        "reconciliation_config.json",
                        f"{recon.get('key_count', 0)} 项",
                        report.get("global_config", {}).get("reconciliation_terms", "") or "对账规则",
                    ),
                ],
            },
        ],
        "links": [
            {"from": "customers", "to": "order_lines", "label": "客户名称"},
            {"from": "order_lines", "to": "shipment_events", "label": "line_id"},
            {"from": "customers", "to": "customer_profiles.json", "label": "键名匹配"},
            {"from": "customers", "to": "customer_delivery.json", "label": "键名匹配"},
            {"from": "parts", "to": "order_lines", "label": "product_spec"},
        ],
    }


def build_customer_maps(report: dict) -> list[dict]:
    maps: list[dict] = []
    rows = [r for r in (report.get("customer_matrix") or []) if r.get("order_lines", 0) > 0]
    rows.sort(key=lambda r: (-r.get("order_lines", 0), r.get("customer", "")))
    for row in rows:
        status = row.get("status", "partial")
        maps.append(
            {
                "id": f"cust-{len(maps)}",
                "root": {
                    "label": row["customer"],
                    "meta": f"{STATUS_LABELS.get(status, status)} · {row.get('order_lines', 0)} 行",
                },
                "color": STATUS_COLORS.get(status, "orange"),
                "leaves": [
                    _leaf("customers", "✓" if row.get("in_master") else "✗", "主数据", warn=not row.get("in_master")),
                    _leaf("order_lines", f"{row.get('order_lines', 0)} 行", "订单"),
                    _leaf("shipment_events", f"{row.get('shipments', 0)} 次", "出货"),
                    _leaf(
                        "customer_profiles.json",
                        f"{row.get('profile_filled', 0)}/{row.get('profile_total', 6)}"
                        if row.get("has_profile")
                        else "未配置",
                        "档案",
                        warn=not row.get("has_profile"),
                    ),
                    _leaf(
                        "customer_delivery.json",
                        f"{row.get('delivery_filled', 0)}/{row.get('delivery_total', 4)}"
                        if row.get("has_delivery")
                        else "未配置",
                        "送货单",
                        warn=not row.get("has_delivery"),
                    ),
                ],
            }
        )
    return maps


PROFILE_FIELD_LABELS = {
    "address": "地址",
    "contact": "联系人",
    "phone": "电话",
    "email": "邮箱",
    "payment_terms": "账期",
    "reconciliation_cycle": "对账周期",
}
DELIVERY_FIELD_LABELS = {
    "receiver_company": "收货公司",
    "receiver_address": "收货地址",
    "receiver_contact": "收货联系人",
    "doc_no_prefix": "单号前缀",
}
PROFILE_FIELDS = tuple(PROFILE_FIELD_LABELS.keys())
DELIVERY_FIELDS = tuple(DELIVERY_FIELD_LABELS.keys())


def _empty_fields(row: dict, fields: tuple[str, ...]) -> list[str]:
    return [f for f in fields if not str(row.get(f) or "").strip()]


def _missing_field_labels(row: dict, fields: tuple[str, ...], labels: dict[str, str]) -> list[str]:
    return [labels[f] for f in _empty_fields(row, fields)]


def _similar_profile_keys(name: str, profile_keys: list[str]) -> list[str]:
    if not name:
        return []
    out: list[str] = []
    name_cf = name.casefold()
    for key in profile_keys:
        if key == name:
            continue
        kcf = key.casefold()
        if name_cf in kcf or kcf in name_cf:
            out.append(key)
        elif "鑫福泰" in name and "鑫福泰" in key:
            out.append(key)
    return sorted(set(out), key=lambda x: (x.casefold(), x))[:3]


def _item(
    category: str,
    category_id: str,
    subject: str,
    reason: str,
    impact: str = "",
    suggestion: str = "",
    severity: str = "warn",
) -> dict:
    return {
        "category": category,
        "category_id": category_id,
        "subject": subject,
        "reason": reason,
        "impact": impact,
        "suggestion": suggestion,
        "severity": severity,
    }


def build_inconsistency_details(report: dict) -> list[dict]:
    from test_impl.order_management.customer_profile.store import load_all_profiles
    from test_impl.order_management.delivery_note.wkt_document import load_customer_delivery_config

    profiles = load_all_profiles()
    delivery_cfg = load_customer_delivery_config()
    profile_keys = list(profiles.keys())
    items: list[dict] = []

    for row in report.get("customer_matrix") or []:
        name = row.get("customer") or ""
        if not name:
            continue
        orders = int(row.get("order_lines") or 0)
        ships = int(row.get("shipments") or 0)
        profile = profiles.get(name, {})
        delivery = delivery_cfg.get(name, {})
        has_profile = bool(row.get("has_profile"))
        has_delivery = bool(row.get("has_delivery"))
        in_master = bool(row.get("in_master"))

        if orders > 0 and not has_profile:
            similar = _similar_profile_keys(name, profile_keys)
            detail = (
                f"order_lines.customer =「{name}」共 {orders} 行，"
                f"但 customer_profiles.json 中没有同名键（或 6 个字段均为空）。"
            )
            if similar:
                detail += f" 档案中存在名称相近的键：{'、'.join(similar)}，可能是简称/全称不一致。"
            items.append(
                _item(
                    "有订单但缺客户档案",
                    "missing_profile",
                    name,
                    detail,
                    f"{orders} 行订单 · {ships} 次出货",
                    "在「客户信息维护」中以订单中的客户名称保存档案，或统一订单客户名为档案键名。",
                )
            )
        elif orders > 0 and has_profile:
            missing = _missing_field_labels(profile, PROFILE_FIELDS, PROFILE_FIELD_LABELS)
            if missing:
                items.append(
                    _item(
                        "客户档案字段未填全",
                        "incomplete_profile",
                        name,
                        f"档案键已存在，但以下字段为空：{'、'.join(missing)}。",
                        f"{orders} 行订单",
                        "补全 customer_profiles.json 中该客户的空字段。",
                        "info",
                    )
                )

        if orders > 0 and not has_delivery:
            items.append(
                _item(
                    "有订单但缺送货单配置",
                    "missing_delivery",
                    name,
                    f"order_lines 有 {orders} 行，但 customer_delivery.json 中没有键「{name}」"
                    f"（或 receiver_* / doc_no_prefix 均为空）。出货打印送货单时将缺少收货地址/联系人。",
                    f"{orders} 行订单 · {ships} 次出货",
                    "在「送货单维护」中为该客户名称配置收货地址与联系人。",
                )
            )
        elif orders > 0 and has_delivery:
            missing = _missing_field_labels(delivery, DELIVERY_FIELDS, DELIVERY_FIELD_LABELS)
            if missing:
                items.append(
                    _item(
                        "送货单配置字段未填全",
                        "incomplete_delivery",
                        name,
                        f"送货单键已存在，但以下字段为空：{'、'.join(missing)}。",
                        f"{orders} 行订单",
                        "补全 customer_delivery.json 中该客户的空字段。",
                        "info",
                    )
                )

        if orders > 0 and not in_master:
            items.append(
                _item(
                    "有订单但未入 customers 主数据",
                    "not_in_master",
                    name,
                    f"order_lines 有 {orders} 行，但 SQLite customers 表中没有 name='{name}'。"
                    f"通常应在录入订单时自动写入主数据表。",
                    f"{orders} 行订单",
                    "检查订单录入流程；可手动 POST /api/master/customer 或重新保存一条该客户订单。",
                )
            )

        if has_profile and orders == 0:
            items.append(
                _item(
                    "档案存在但无订单",
                    "orphan_profile",
                    name,
                    f"customer_profiles.json 有键「{name}」（已填 {row.get('profile_filled', 0)}/"
                    f"{row.get('profile_total', 6)} 字段），但 order_lines 中没有任何订单使用此客户名。",
                    "0 行订单",
                    "预录入客户可保留；若曾用简称下单，需把订单 customer 改为与此键一致。",
                    "info",
                )
            )

        if has_delivery and orders == 0:
            items.append(
                _item(
                    "送货单配置存在但无订单",
                    "orphan_delivery",
                    name,
                    f"customer_delivery.json 有键「{name}」，但 order_lines 中无对应订单。",
                    "0 行订单",
                    "确认客户名称是否与订单一致；无用键可删除。",
                    "info",
                )
            )

    for spec in report.get("gaps", {}).get("specs_not_in_parts_master") or []:
        refs = 0
        for p in report.get("parts_matrix") or []:
            if p.get("product_spec") == spec:
                refs = int(p.get("order_line_refs") or 0)
                break
        items.append(
            _item(
                "品名未入 parts 主数据",
                "parts_not_in_master",
                spec,
                f"order_lines.product_spec =「{spec}」被 {refs} 行订单引用，"
                f"但 SQLite parts 表中没有此 product_spec，customer_part_no 无法从主数据带出。",
                f"{refs} 行订单",
                "通过订单录入或 /api/master/part 补充品名与客户料号映射。",
            )
        )

    partial_customers = [r for r in report.get("customer_matrix") or [] if r.get("status") == "partial"]
    if len(partial_customers) > 1:
        only_missing_delivery = [
            r["customer"]
            for r in partial_customers
            if r.get("has_profile") and not r.get("has_delivery")
        ]
        if len(only_missing_delivery) >= 5:
            items.append(
                _item(
                    "批量缺口（汇总）",
                    "batch_summary",
                    f"{len(only_missing_delivery)} 个客户",
                    f"以下客户已有档案但普遍缺少送货单配置："
                    f"{'、'.join(only_missing_delivery[:8])}"
                    f"{'…' if len(only_missing_delivery) > 8 else ''}。"
                    f"这是当前「部分映射」状态的主要原因。",
                    f"{len(only_missing_delivery)} 家客户",
                    "优先在「送货单维护」批量补收货地址。",
                    "info",
                )
            )

    severity_order = {"warn": 0, "info": 1}
    cat_order = {
        "missing_profile": 0,
        "missing_delivery": 1,
        "not_in_master": 2,
        "parts_not_in_master": 3,
        "incomplete_profile": 4,
        "incomplete_delivery": 5,
        "orphan_profile": 6,
        "orphan_delivery": 7,
        "batch_summary": 8,
    }
    items.sort(key=lambda x: (severity_order.get(x["severity"], 9), cat_order.get(x["category_id"], 99), x["subject"]))
    return items


def build_gap_map(report: dict, inconsistencies: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for it in inconsistencies:
        groups.setdefault(it["category"], []).append(it)

    branches: list[dict] = []
    colors = ["red", "orange", "purple", "gray"]
    for idx, (cat, group) in enumerate(groups.items()):
        leaves = [
            _leaf(
                it["subject"],
                it["impact"] or "—",
                it["reason"],
                warn=it.get("severity") == "warn",
            )
            for it in group
        ]
        branches.append(
            {
                "id": f"gap-{idx}",
                "label": cat,
                "color": colors[idx % len(colors)],
                "summary": f"{len(group)} 条",
                "leaves": leaves,
            }
        )

    if not branches:
        branches = [
            {
                "id": "ok",
                "label": "无不一致",
                "color": "green",
                "summary": "0 条",
                "leaves": [_leaf("全部一致", "—", "SQLite 与 JSON 键名、档案、送货单均已对齐")],
            }
        ]

    return {
        "title": "缺口与不一致",
        "root": {"label": "数据不一致", "meta": f"共 {len(inconsistencies)} 条明细"},
        "branches": branches,
    }


def build_dashboard_payload(report: dict) -> dict:
    inconsistencies = build_inconsistency_details(report)
    return {
        "generated_at": report.get("generated_at", ""),
        "db_path": report.get("db_path", ""),
        "join_key": report.get("join_key", ""),
        "summary": report.get("summary", {}),
        "overview": build_overview_map(report),
        "customers": build_customer_maps(report),
        "gaps": build_gap_map(report, inconsistencies),
        "inconsistencies": inconsistencies,
    }


def main() -> None:
    report = DataMappingService().build_report()
    payload = build_dashboard_payload(report)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    (OUT_DIR / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "dashboard.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    template = TEMPLATE.read_text(encoding="utf-8")
    generated = (report.get("generated_at") or "").replace("T", " ")[:19] + " UTC"
    html = template.replace("__GENERATED__", generated).replace(
        "__DATA_JSON__", json.dumps(payload, ensure_ascii=False)
    )
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")

    print(f"Wrote {OUT_DIR / 'index.html'}")
    print(f"Wrote {OUT_DIR / 'dashboard.json'}")
    print("Open index.html in your browser.")


if __name__ == "__main__":
    main()
