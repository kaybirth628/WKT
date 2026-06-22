"""OCR 识别完成后，将原始订单文件归档到项目 orders/ 目录。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

_INVALID = re.compile(r'[\\/:*?"<>|]+')


def sanitize_path_part(value: str, *, default: str = "未知") -> str:
    s = _INVALID.sub("_", (value or "").strip())
    s = re.sub(r"\s+", " ", s).strip(" .")
    if not s:
        return default
    return s[:80]


def build_archive_filename(order_date: str, order_no: str, ext: str) -> str:
    date_part = sanitize_path_part(order_date, default="未知日期")
    no_part = sanitize_path_part(order_no, default="未知订单号")
    suffix = ext if ext.startswith(".") else f".{ext}"
    return f"{date_part}_{no_part}{suffix}"


def archive_order_file(
    file_bytes: bytes,
    original_filename: str,
    lines: List[dict],
    orders_root: Path,
) -> Path:
    """保存到 orders/{客户名}/{接单日期}_{订单号}.ext，重名则追加序号。"""
    if not lines:
        raise ValueError("无识别结果，无法归档订单文件")

    first = lines[0]
    customer = sanitize_path_part(str(first.get("customer") or ""), default="未知客户")
    order_date = str(first.get("order_date") or "").strip()
    order_no = str(first.get("order_no") or "").strip()

    ext = Path(original_filename or "").suffix.lower()
    if not ext:
        ext = ".pdf"

    dest_dir = orders_root / customer
    dest_dir.mkdir(parents=True, exist_ok=True)

    base_name = build_archive_filename(order_date, order_no, ext)
    dest = dest_dir / base_name
    counter = 1
    while dest.exists():
        stem = Path(base_name).stem
        dest = dest_dir / f"{stem}_{counter}{ext}"
        counter += 1

    dest.write_bytes(file_bytes)
    return dest


def try_archive_order_file(
    file_bytes: bytes,
    original_filename: str,
    lines: List[dict],
    orders_root: Path,
) -> tuple[Optional[str], Optional[str]]:
    """返回 (相对路径, 错误信息)。"""
    try:
        saved = archive_order_file(file_bytes, original_filename, lines, orders_root)
        rel = saved.relative_to(orders_root.parent)
        return str(rel).replace("\\", "/"), None
    except Exception as exc:  # noqa: BLE001 — 归档失败不阻断 OCR
        return None, str(exc)
