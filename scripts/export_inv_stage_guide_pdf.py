#!/usr/bin/env python3
"""Export 工序出入库-操作说明.md to PDF via Playwright."""
from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOP = ROOT / "docs" / "SOP"
MD_FILE = SOP / "工序出入库-操作说明.md"
OUT_PDF = SOP / "工序出入库-操作说明.pdf"
BUILD_DIR = SOP / "_pdf_build"


def md_to_html(md_text: str) -> str:
    import markdown

    text = md_text

    def img_repl(match: re.Match[str]) -> str:
        alt, rel = match.group(1), match.group(2)
        path = (SOP / rel).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Missing image: {path}")
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'![{alt}](data:{mime};base64,{b64})'

    text = re.sub(r"!\[([^\]]*)\]\((\./images/[^)]+)\)", img_repl, text)

    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
        output_format="html5",
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>WKT · 工序出入库操作说明</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    @page {{ size: A4; margin: 16mm 14mm 18mm 14mm; }}
    html {{ font-size: 11pt; }}
    body {{
      font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.65;
      color: #1e293b;
      margin: 0;
      padding: 0;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}
    h1 {{
      font-size: 20pt;
      font-weight: 700;
      color: #0f172a;
      border-bottom: 3px solid #5e6ad2;
      padding-bottom: 0.35em;
      margin: 0 0 0.75em;
    }}
    h2 {{
      font-size: 13.5pt;
      font-weight: 700;
      color: #1e293b;
      margin: 1.1em 0 0.45em;
      page-break-after: avoid;
    }}
    p, li {{ margin: 0.35em 0; }}
    blockquote {{
      margin: 0.75em 0 1em;
      padding: 0.65em 1em;
      background: #eef2ff;
      border-left: 4px solid #5e6ad2;
      color: #312e81;
      font-size: 12.5pt;
      font-weight: 600;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 0.6em 0 0.8em;
      font-size: 10pt;
    }}
    th, td {{
      border: 1px solid #cbd5e1;
      padding: 0.35em 0.55em;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #f1f5f9; font-weight: 600; }}
    img {{
      display: block;
      max-width: 92%;
      height: auto;
      margin: 0.5em auto 0.8em;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      page-break-inside: avoid;
    }}
    hr {{
      border: none;
      border-top: 1px solid #e2e8f0;
      margin: 1em 0;
    }}
    ul {{ padding-left: 1.3em; }}
    strong {{ color: #0f172a; }}
  </style>
</head>
<body>
  {body}
</body>
</html>"""


def export_pdf() -> Path:
    if not MD_FILE.is_file():
        raise SystemExit(f"Missing {MD_FILE}")

    md_text = MD_FILE.read_text(encoding="utf-8")
    html = md_to_html(md_text)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    html_path = BUILD_DIR / "inv-stage-guide.html"
    html_path.write_text(html, encoding="utf-8")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1100, "height": 1400})
        page.goto(html_path.as_uri(), wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(1500)
        page.pdf(
            path=str(OUT_PDF),
            format="A4",
            print_background=True,
            margin={"top": "14mm", "bottom": "16mm", "left": "12mm", "right": "12mm"},
            display_header_footer=True,
            header_template=(
                '<div style="font-size:8px;width:100%;text-align:center;color:#94a3b8;'
                'padding-top:3mm;font-family:Noto Sans SC,sans-serif;">'
                "WKT 销售管理系统 · 工序出入库</div>"
            ),
            footer_template=(
                '<div style="font-size:8px;width:100%;text-align:center;color:#94a3b8;'
                'padding-bottom:3mm;font-family:Noto Sans SC,sans-serif;">'
                "第 <span class=\"pageNumber\"></span> 页 / 共 <span class=\"totalPages\"></span> 页</div>"
            ),
        )
        browser.close()

    size_kb = OUT_PDF.stat().st_size / 1024
    print(f"Created {OUT_PDF} ({size_kb:.0f} KB)")
    return OUT_PDF


def main() -> int:
    export_pdf()
    return 0


if __name__ == "__main__":
    sys.exit(main())
