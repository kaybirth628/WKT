#!/usr/bin/env python3
"""Re-capture only OCR preview screenshot."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.capture_sop_screenshots import BASE, OUT, goto, make_static_png, shot  # noqa: E402


def main() -> int:
    from playwright.sync_api import sync_playwright

    sample_po = ROOT / "data" / "sop_samples" / "sample_po.pdf"
    if not sample_po.is_file():
        print("Missing sample_po.pdf; run scripts/create_sop_sample_po.py")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN").new_page()
        goto(page, f"{BASE}/#entry")
        page.locator("#modeOcrBtn").click()
        page.wait_for_timeout(300)
        page.locator("#orderFile").set_input_files(str(sample_po))
        page.locator("#recognizeBtn").click()
        print("Recognizing (up to 3 min)...")
        done = False
        for i in range(90):
            page.wait_for_timeout(2000)
            preview = page.locator("#previewArea")
            hidden = preview.count() == 0 or preview.evaluate("el => el.classList.contains('is-hidden')")
            rows = page.locator("#previewBody tr").count()
            msg = ""
            if page.locator("#recognizeMsg").count():
                msg = page.locator("#recognizeMsg").inner_text()
                msg = msg.encode("ascii", "replace").decode("ascii")
            print(f"  wait {(i+1)*2}s  preview_hidden={hidden} rows={rows} msg={msg[:80]!r}")
            if not hidden and rows > 0:
                shot(page, "03-ocr-preview.png", full_page=True, wait_ms=800)
                done = True
                break
            err = page.locator("#recognizeMsg").inner_text()
            if err and ("失败" in err or "error" in err.lower()):
                print("OCR failed:", err)
                break
        browser.close()

    if not done:
        make_static_png(
            "03-ocr-preview.png",
            "OCR 识别预览（示意）",
            ["识别未完成或依赖未配置", "请确认 RapidOCR / DeepSeek 可用", "手动上传 PO 后重跑本脚本"],
        )
        return 1
    print("OK 03-ocr-preview.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
