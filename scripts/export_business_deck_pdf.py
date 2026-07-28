#!/usr/bin/env python3
"""Export SME manufacturing AI deck HTML to PDF via Playwright."""
from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKETING = ROOT / "docs" / "marketing"
VERSIONS = {
    "v1": (
        MARKETING / "AI制造数字化-业务介绍.html",
        MARKETING / "AI制造数字化-业务介绍.pdf",
        MARKETING / "_pdf_build",
    ),
    "v2": (
        MARKETING / "AI制造数字化-业务介绍-v2.html",
        MARKETING / "AI制造数字化-业务介绍-v2.pdf",
        MARKETING / "_pdf_build_v2",
    ),
}


def embed_images(html: str, html_file: Path) -> str:
    def repl(match: re.Match[str]) -> str:
        prefix, rel, suffix = match.group(1), match.group(2), match.group(3)
        path = (html_file.parent / rel).resolve()
        if not path.is_file():
            return match.group(0)
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'{prefix}data:{mime};base64,{b64}{suffix}'

    html = re.sub(r'(src=")(\.\./SOP/images/[^"]+)(")', repl, html)
    html = re.sub(r'(src=")(images/[^"]+)(")', repl, html)
    return html


def export_pdf(version: str = "v1") -> Path:
    if version not in VERSIONS:
        raise SystemExit(f"Unknown version: {version}. Use v1 or v2.")

    html_file, out_pdf, build_dir = VERSIONS[version]
    if not html_file.is_file():
        raise SystemExit(f"Missing {html_file}")

    html = embed_images(html_file.read_text(encoding="utf-8"), html_file)
    build_dir.mkdir(parents=True, exist_ok=True)
    build_html = build_dir / "deck.html"
    build_html.write_text(html, encoding="utf-8")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(build_html.as_uri(), wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2500)
        page.pdf(
            path=str(out_pdf),
            width="1920px",
            height="1080px",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()

    size_mb = out_pdf.stat().st_size / (1024 * 1024)
    print(f"Created {out_pdf} ({size_mb:.2f} MB)")
    return out_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description="Export business deck HTML to PDF")
    parser.add_argument(
        "--version",
        choices=["v1", "v2", "all"],
        default="v1",
        help="Deck version to export (default: v1)",
    )
    args = parser.parse_args()
    if args.version == "all":
        export_pdf("v1")
        export_pdf("v2")
    else:
        export_pdf(args.version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
