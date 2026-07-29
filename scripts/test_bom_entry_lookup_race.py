#!/usr/bin/env python3
"""Playwright: BOM entry fast-click vs lookup (in-browser fetch delay)."""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:5000"
PART = "TST-PL-001"
PROCESS_CODE = "21"
DELAY_MS = 1500

FETCH_PATCH = f"""
(() => {{
  if (window.__wktLookupDelayPatched) return;
  window.__wktLookupDelayPatched = true;
  const orig = window.fetch.bind(window);
  window.fetch = async (...args) => {{
    const url = String(args[0] || "");
    if (url.includes("/api/cost/lookup")) {{
      await new Promise((r) => setTimeout(r, {DELAY_MS}));
    }}
    return orig(...args);
  }};
}})();
"""


def login(page) -> None:
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    page.fill("#loginUsername", "admin")
    page.fill("#loginPassword", "123456")
    page.locator("#loginForm button[type=submit]").click()
    page.wait_for_timeout(1000)


def open_manual(page) -> None:
    page.goto(f"{BASE}/bom/entry", wait_until="domcontentloaded")
    page.locator("#bomModeManualBtn").click()
    page.wait_for_selector("#processGrid .process-pick", timeout=20000)
    page.wait_for_timeout(500)


def count_checked(page) -> int:
    return page.locator("#processGrid .process-pick:checked").count()


def main() -> int:
    from playwright.sync_api import sync_playwright

    build = json.loads(urllib.request.urlopen(f"{BASE}/api/health").read()).get("build")
    print(f"build={build}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        context.add_init_script(FETCH_PATCH)
        page = context.new_page()
        login(page)
        open_manual(page)

        # 1) 填料号后立刻点工序（模拟手速快）
        page.locator("#productPartNoInput").fill(PART)
        page.locator("#productPartNoInput").press("Tab")
        page.wait_for_timeout(80)
        loading = page.locator("#processGrid.is-lookup-loading").count() > 0
        before = count_checked(page)
        page.locator(f'.process-pick[data-process-code="{PROCESS_CODE}"]').click(force=True)
        page.wait_for_timeout(100)
        during = count_checked(page)
        page.wait_for_function(
            "() => !document.getElementById('processGrid')?.classList.contains('is-lookup-loading')",
            timeout=20000,
        )
        page.wait_for_timeout(300)
        after = count_checked(page)
        hint = page.locator("#partLookupHint").inner_text()
        codes = page.evaluate(
            '() => Array.from(document.querySelectorAll("#processGrid .process-pick:checked"))'
            ".map((x) => x.dataset.processCode)"
        )

        print("--- 场景1：填料号后立刻点工序 ---")
        print(f"  载入锁定出现: {loading}")
        print(f"  载入中勾选数: {during} (点击前 {before})")
        print(f"  载入完成后勾选: {after}  工序: {codes}")
        print(f"  提示: {hint[:80]}")

        page.locator("#productPartNoInput").fill(PART)
        page.locator("#productPartNoInput").press("Tab")
        page.wait_for_timeout(80)
        page.locator(f'.process-pick[data-process-code="{PROCESS_CODE}"]').click(force=True)
        page.wait_for_timeout(100)
        during_fast = page.evaluate(
            '() => Array.from(document.querySelectorAll("#processGrid .process-pick:checked"))'
            ".map((x) => x.dataset.processCode)"
        )
        page.wait_for_timeout(500)
        after_fast = page.evaluate(
            '() => Array.from(document.querySelectorAll("#processGrid .process-pick:checked"))'
            ".map((x) => x.dataset.processCode)"
        )
        print("--- 场景1b：Tab料号后80ms点烤漆 ---")
        print(f"  点击后: {during_fast}  延迟后: {after_fast}")
        if PROCESS_CODE in after_fast:
            print("  ✓ 快点击烤漆保留")

        open_manual(page)
        page.locator(f'.process-pick[data-process-code="{PROCESS_CODE}"]').click(force=True)
        pre = count_checked(page)
        page.locator("#productPartNoInput").fill(PART)
        page.locator("#productPartNoInput").press("Tab")
        page.wait_for_function(
            "() => !document.getElementById('processGrid')?.classList.contains('is-lookup-loading')",
            timeout=20000,
        )
        page.wait_for_timeout(300)
        post = count_checked(page)
        codes2 = page.evaluate(
            '() => Array.from(document.querySelectorAll("#processGrid .process-pick:checked"))'
            ".map((x) => x.dataset.processCode)"
        )
        print("--- 场景2：先勾工序再填料号 ---")
        print(f"  填料号前勾选: {pre}  载入后: {post}  工序: {codes2}")
        print(f"  手工「烤漆21」被覆盖: {PROCESS_CODE not in codes2 and pre >= 1}")
        if PROCESS_CODE in codes2:
            print("  ✓ 先勾工序再填料号 → 烤漆仍保留")

        browser.close()

    print("--- 总结 ---")
    if loading:
        print("已在本地复现并验证：慢网络下工序区会短暂锁定。")
    else:
        print("未看到锁定（请检查是否已 Ctrl+F5 加载新 JS）。")
    if PROCESS_CODE not in codes2 and pre >= 1:
        print("先勾工序再填料号时，载入后会按 BOM 已有工序覆盖（等提示出来再改最稳）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
