#!/usr/bin/env python3
"""Capture SOP training screenshots via Playwright (headless Chromium)."""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "SOP" / "images"
BASE = "http://127.0.0.1:5000"


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError as exc:
        raise SystemExit("Run: pip install playwright && python -m playwright install chromium") from exc


def goto(page, url: str, *, wait_ms: int = 800) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(wait_ms)


def shot(page, name: str, *, full_page: bool = True, wait_ms: int = 800) -> None:
    page.wait_for_timeout(wait_ms)
    path = OUT / name
    page.screenshot(path=str(path), full_page=full_page)
    print(f"  OK  {name}")


def make_static_png(name: str, title: str, lines: list[str]) -> None:
    from PIL import Image, ImageDraw, ImageFont

    w, h = 1280, 720
    img = Image.new("RGB", (w, h), "#f3f4f6")
    draw = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype("msyh.ttc", 28)
        font_body = ImageFont.truetype("msyh.ttc", 20)
    except OSError:
        font_title = ImageFont.load_default()
        font_body = font_title

    draw.rectangle([0, 0, w, 72], fill="#1e293b")
    draw.text((24, 20), title, fill="#f8fafc", font=font_title)
    y = 100
    for line in lines:
        for chunk in textwrap.wrap(line, width=52) or [""]:
            draw.text((40, y), chunk, fill="#334155", font=font_body)
            y += 32
    img.save(OUT / name)
    print(f"  OK  {name} (static)")


def main() -> int:
    ensure_playwright()
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)

    desktop_script = ROOT / "scripts" / "capture_desktop_sop_shots.py"
    if desktop_script.is_file():
        print("Desktop captures...")
        subprocess.run([sys.executable, str(desktop_script)], check=False)
    else:
        make_static_png(
            "00-start-bat.png",
            "启动系统 · 双击一键启动网页.bat",
            [
                f"文件夹：{ROOT}",
                "找到文件：一键启动网页.bat",
                "双击运行 → 稍等浏览器自动打开",
                "若未打开，手动访问 http://127.0.0.1:5000",
            ],
        )
        make_static_png(
            "00-cmd-window.png",
            "请勿关闭此命令行窗口",
            [
                "启动后会出现黑色/蓝色命令行窗口",
                "窗口标题通常含 python 或 flask",
                "关闭窗口 = 网页无法访问",
                "结束使用时可在窗口内按 Ctrl+C",
            ],
        )

    sample_po_script = ROOT / "scripts" / "create_sop_sample_po.py"
    if sample_po_script.is_file() and not (ROOT / "data" / "sop_samples" / "sample_po.pdf").is_file():
        subprocess.run([sys.executable, str(sample_po_script)], check=False)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page = context.new_page()

        # Top nav composite: open orders dropdown
        goto(page, f"{BASE}/#entry")
        page.locator("#topNavOrdersTrigger").click()
        page.wait_for_timeout(400)
        shot(page, "01-top-nav.png", full_page=False, wait_ms=200)

        goto(page, f"{BASE}/#entry")
        shot(page, "01-page-footer.png", full_page=False)

        # Entry modes
        shot(page, "02-entry-mode-select.png", full_page=False)

        page.locator("#modeOcrBtn").click()
        page.wait_for_timeout(300)
        shot(page, "03-ocr-upload.png", full_page=False)

        # Manual form
        page.locator("#modeManualBtn").click()
        page.wait_for_timeout(300)
        shot(page, "04-manual-form.png", full_page=True)

        # Lists
        for hash_key, fname, fp in [
            ("detail", "05-order-detail-list.png", False),
            ("open", "06-open-ship.png", False),
            ("shipped", "07-shipped-list.png", False),
            ("reconcile", "08-reconcile-outlook.png", True),
            ("payable", "09-payable-outlook.png", True),
            ("delivery", "10-customer-maint.png", False),
            ("supplier", "11-supplier-maint.png", False),
        ]:
            goto(page, f"{BASE}/#{hash_key}", wait_ms=1200)
            shot(page, fname, full_page=fp, wait_ms=200)

        # Reconcile detail drill-down
        goto(page, f"{BASE}/#reconcile", wait_ms=1500)
        btn = page.locator(".reconcile-detail-btn").first
        if btn.count() > 0:
            btn.click()
            page.wait_for_timeout(1200)
            shot(page, "08-reconcile-detail.png", full_page=True)
        else:
            make_static_png(
                "08-reconcile-detail.png",
                "应收 · 查看明细",
                ["当前数据库暂无到期客户行", "请先完成出货后再钻取明细", "操作：应收页 → 某月客户行 → 查看明细"],
            )

        # Customer delivery preview
        goto(page, f"{BASE}/#delivery", wait_ms=1000)
        preview_btn = page.locator(".dn-preview-row-btn:not([disabled])").first
        if preview_btn.count() > 0:
            preview_btn.click()
            page.wait_for_timeout(1500)
            shot(page, "10-delivery-preview.png", full_page=True)
        else:
            shot(page, "10-delivery-preview.png", full_page=True)

        # Column filter on detail list
        goto(page, f"{BASE}/#detail", wait_ms=1000)
        filter_btn = page.locator("#listHead .list-filter-btn").first
        if filter_btn.count() > 0:
            filter_btn.click()
            page.wait_for_timeout(400)
            shot(page, "14-col-filter.png", full_page=False)
        else:
            make_static_png(
                "14-col-filter.png",
                "表头列筛选 ▾",
                ["在订单明细等列表", "点击表头列名右侧 ▾", "勾选要显示的值 → 确定"],
            )

        # Ship confirm modal
        goto(page, f"{BASE}/#open", wait_ms=1200)
        ship_btn = page.locator(".ship-open-btn").first
        got_ship_modal = False
        if ship_btn.count() > 0:
            ship_btn.click()
            page.wait_for_timeout(1500)
            backdrop = page.locator("#shipDnBackdrop")
            if backdrop.count() and backdrop.evaluate("el => !el.classList.contains('is-hidden')"):
                shot(page, "06-ship-confirm.png", full_page=False, wait_ms=500)
                got_ship_modal = True
                close = page.locator("#shipDnCancel").first
                if close.count():
                    close.click()
        if not got_ship_modal:
            try:
                with urllib.request.urlopen(f"{BASE}/api/lines?view=open") as resp:
                    lines = json.loads(resp.read().decode())
                if lines:
                    lid = lines[0]["id"]
                    goto(page, f"{BASE}/delivery-note/ship-confirm?line_id={lid}&qty=1", wait_ms=1500)
                    shot(page, "06-ship-confirm.png", full_page=True, wait_ms=300)
                    got_ship_modal = True
            except Exception:
                pass
        if not got_ship_modal:
            make_static_png(
                "06-ship-confirm.png",
                "出货确认 · 送货单",
                ["未结订单 → 点击「出货」", "弹出送货单确认页", "填写本次出货数量后确认"],
            )

        # Batch ship hint
        goto(page, f"{BASE}/#open", wait_ms=1000)
        checks = page.locator(".open-ship-check")
        if checks.count() >= 2:
            checks.nth(0).check()
            checks.nth(1).check()
            page.wait_for_timeout(500)
            shot(page, "06-batch-ship.png", full_page=False)
        else:
            make_static_png(
                "06-batch-ship.png",
                "合并出货",
                ["未结订单勾选同一客户多行", "点击「合并出货（N 条）」", "在弹窗中填写各料号出货数量"],
            )

        # BOM pages
        goto(page, f"{BASE}/bom/entry")
        shot(page, "12-bom-entry.png", full_page=True)

        goto(page, f"{BASE}/bom/query")
        shot(page, "12-bom-query.png", full_page=True)

        goto(page, f"{BASE}/inventory", wait_ms=1500)
        shot(page, "13-inventory-board.png", full_page=True)

        goto(page, f"{BASE}/inventory")
        shot(page, "13-inventory-entry.png", full_page=True)

        # OCR preview needs a sample PO file; static placeholder until one is added under data/sop_samples/
        ocr_preview_done = False
        sample_po = ROOT / "data" / "sop_samples" / "sample_po.pdf"
        if sample_po.is_file():
            goto(page, f"{BASE}/#entry")
            page.locator("#modeOcrBtn").click()
            page.wait_for_timeout(300)
            page.locator("#orderFile").set_input_files(str(sample_po))
            page.locator("#recognizeBtn").click()
            # OCR + AI may take 1–2 min
            for _ in range(90):
                page.wait_for_timeout(2000)
                preview = page.locator("#previewArea")
                if preview.count() and preview.evaluate("el => !el.classList.contains('is-hidden')"):
                    body = page.locator("#previewBody tr")
                    if body.count() > 0:
                        shot(page, "03-ocr-preview.png", full_page=True, wait_ms=800)
                        ocr_preview_done = True
                        break
        if not ocr_preview_done:
            make_static_png(
                "03-ocr-preview.png",
                "OCR 识别预览（示意）",
                [
                    "上传 PDF/图片 → 点「识别」",
                    "上方：订单原件（200 DPI 高清图，可缩放）",
                    "下方：识别表格；黄色 = 须核对修改",
                    "无误后点「批量提交录入」",
                ],
            )

        browser.close()

    print(f"\nDone. {len(list(OUT.glob('*.png')))} PNG files in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
