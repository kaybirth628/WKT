"""按威可特统一版式生成 Excel 送货单。"""
from __future__ import annotations

import io
from typing import TYPE_CHECKING

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side
except ImportError:
    Workbook = None  # type: ignore

if TYPE_CHECKING:
    from .wkt_document import WktDeliveryDocument

_THIN = Side(style="thin", color="000000")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)


def build_xlsx_bytes(doc: "WktDeliveryDocument") -> bytes:
    if Workbook is None:
        raise ValueError("openpyxl 未安装，无法生成 Excel 送货单")
    wb = Workbook()
    ws = wb.active
    ws.title = "送货单"

    ws.merge_cells("A1:I1")
    c = ws["A1"]
    c.value = doc.title_company
    c.font = Font(size=16, bold=True)
    c.alignment = _CENTER

    ws.merge_cells("A2:I2")
    c2 = ws["A2"]
    c2.value = "送货单"
    c2.font = Font(size=14, bold=True)
    c2.alignment = _CENTER

    meta = [
        ("A4", "送货单号：", doc.doc_no, "F4", "日期：", doc.ship_date_cn),
        ("A5", "收货公司：", doc.receiver_company, "F5", "供应商：", doc.supplier_name),
        ("A6", "收货地点：", doc.receiver_address, "F6", "供应商地址：", doc.supplier_address),
        ("A7", "联系人及电话：", doc.receiver_contact, "F7", "供应商电话：", doc.supplier_phone),
    ]
    for left_cell, left_lbl, left_val, right_cell, right_lbl, right_val in meta:
        ws[left_cell] = left_lbl + (left_val or "")
        ws[right_cell] = right_lbl + (right_val or "")
        ws[left_cell].alignment = _LEFT
        ws[right_cell].alignment = _LEFT

    headers = [
        "订单号",
        "客户物料编码",
        "物料名称",
        "规格型号",
        "单位",
        "数量",
        "生产批号",
        "箱数",
        "备注",
    ]
    start_row = 9
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=col, value=h)
        cell.font = Font(bold=True)
        cell.alignment = _CENTER
        cell.border = _BORDER

    row = start_row + 1
    for ln in doc.lines:
        vals = [
            ln.order_no or "/",
            ln.customer_part_no,
            ln.product_name,
            ln.spec,
            ln.unit,
            ln.qty,
            ln.batch_no,
            ln.box_count,
            ln.remark,
        ]
        for col, v in enumerate(vals, 1):
            cell = ws.cell(row=row, column=col, value=v)
            cell.border = _BORDER
            cell.alignment = _CENTER if col in (5, 6, 7, 8) else _LEFT
        row += 1

    ws.cell(row=row, column=1, value="以下空白").border = _BORDER
    for col in range(2, 10):
        ws.cell(row=row, column=col).border = _BORDER
    row += 1

    ws.cell(row=row, column=1, value="合计").font = Font(bold=True)
    ws.cell(row=row, column=6, value=doc.total_qty).font = Font(bold=True)
    for col in range(1, 10):
        ws.cell(row=row, column=col).border = _BORDER

    sign_row = row + 2
    ws.cell(row=sign_row, column=1, value="送货人：" + (doc.deliverer or ""))
    ws.cell(row=sign_row, column=4, value="仓管：" + (doc.warehouse_manager or ""))
    ws.cell(row=sign_row, column=7, value="收货：" + (doc.receiver_sign or ""))

    ws.cell(row=sign_row + 2, column=1, value=doc.footer_note)

    widths = [14, 14, 16, 14, 6, 8, 12, 8, 12]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
