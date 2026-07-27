#!/usr/bin/env python3
"""Export 员工培训手册-图文版.md to PDF via Playwright."""
from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOP = ROOT / "docs" / "SOP"
MD_FILE = SOP / "员工培训手册-图文版.md"
OUT_PDF = SOP / "员工培训手册-图文版.pdf"
BUILD_DIR = SOP / "_pdf_build"


def md_to_html(md_text: str, *, images_dir: Path) -> str:
    import markdown

    text = md_text
    # Mermaid -> readable flow text for PDF
    def mermaid_repl(match: re.Match[str]) -> str:
        body = match.group(1).strip()
        lines = [ln.strip() for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("flowchart")]
        flow = " → ".join(
            re.sub(r"[\[\]{}|]", "", ln).replace("-->", "→").replace(" ", "")
            for ln in lines
            if "-->" in ln or "→" in ln
        )
        if not flow:
            flow = body.replace("\n", " · ")
        return f"\n\n> **流程示意**：{flow}\n\n"

    text = re.sub(r"```mermaid\n(.*?)```", mermaid_repl, text, flags=re.DOTALL)

    # Relative images -> base64 embed (self-contained PDF)
    def img_repl(match: re.Match[str]) -> str:
        alt, rel = match.group(1), match.group(2)
        path = (SOP / rel).resolve()
        if not path.is_file():
            return match.group(0)
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
  <title>WKT 销售管理系统 · 员工培训手册</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    @page {{ size: A4; margin: 18mm 16mm 20mm 16mm; }}
    html {{ font-size: 11pt; }}
    body {{
      font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.65;
      color: #1e293b;
      max-width: 100%;
      margin: 0;
      padding: 0;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}
    h1 {{
      font-size: 22pt;
      font-weight: 700;
      color: #0f172a;
      border-bottom: 3px solid #5e6ad2;
      padding-bottom: 0.35em;
      margin: 0 0 0.8em;
      page-break-after: avoid;
    }}
    h2 {{
      font-size: 15pt;
      font-weight: 700;
      color: #1e293b;
      margin: 1.6em 0 0.6em;
      padding-top: 0.2em;
      border-bottom: 1px solid #cbd5e1;
      page-break-after: avoid;
    }}
    h3 {{
      font-size: 12.5pt;
      font-weight: 600;
      margin: 1.2em 0 0.5em;
      page-break-after: avoid;
    }}
    h4 {{ font-size: 11pt; font-weight: 600; margin: 1em 0 0.4em; }}
    p, li {{ margin: 0.35em 0; }}
    blockquote {{
      margin: 0.8em 0;
      padding: 0.6em 1em;
      background: #f8fafc;
      border-left: 4px solid #5e6ad2;
      color: #334155;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 0.8em 0 1em;
      font-size: 10pt;
      page-break-inside: avoid;
    }}
    th, td {{
      border: 1px solid #cbd5e1;
      padding: 0.35em 0.55em;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #f1f5f9; font-weight: 600; }}
    tr:nth-child(even) td {{ background: #fafafa; }}
    code {{
      font-family: Consolas, "Courier New", ui-monospace, monospace;
      font-size: 0.92em;
      background: #f1f5f9;
      padding: 0.1em 0.35em;
      border-radius: 3px;
    }}
    pre {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      padding: 0.75em 1em;
      overflow-x: auto;
      font-size: 9pt;
      line-height: 1.45;
      page-break-inside: avoid;
    }}
    pre code {{ background: none; padding: 0; }}
    img {{
      display: block;
      max-width: 100%;
      height: auto;
      margin: 0.6em auto 1em;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      page-break-inside: avoid;
    }}
    hr {{
      border: none;
      border-top: 1px solid #e2e8f0;
      margin: 1.5em 0;
    }}
    ul, ol {{ padding-left: 1.4em; }}
    a {{ color: #4338ca; text-decoration: none; }}
    h2, h3 {{ page-break-before: auto; }}
    .cover {{
      text-align: center;
      padding: 3em 1em 2em;
      page-break-after: always;
    }}
    .cover h1 {{ border: none; font-size: 26pt; }}
    .cover p {{ color: #64748b; font-size: 12pt; }}
  </style>
</head>
<body>
  <div class="cover">
    <h1>WKT 销售管理系统</h1>
    <p>员工培训手册（图文版）</p>
    <p>威可特 · 正式测试用 · 2026-07-23</p>
  </div>
  {body}
</body>
</html>"""


def export_pdf() -> Path:
    if not MD_FILE.is_file():
        raise SystemExit(f"Missing {MD_FILE}")

    md_text = MD_FILE.read_text(encoding="utf-8")
    html = md_to_html(md_text, images_dir=SOP / "images")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    html_path = BUILD_DIR / "manual.html"
    html_path.write_text(html, encoding="utf-8")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 1600})
        page.goto(html_path.as_uri(), wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        page.pdf(
            path=str(OUT_PDF),
            format="A4",
            print_background=True,
            margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
            display_header_footer=True,
            header_template=(
                '<div style="font-size:8px;width:100%;text-align:center;color:#94a3b8;'
                'padding-top:4mm;font-family:Noto Sans SC,sans-serif;">'
                "WKT 销售管理系统 · 员工培训手册</div>"
            ),
            footer_template=(
                '<div style="font-size:8px;width:100%;text-align:center;color:#94a3b8;'
                'padding-bottom:4mm;font-family:Noto Sans SC,sans-serif;">'
                "第 <span class=\"pageNumber\"></span> 页 / 共 <span class=\"totalPages\"></span> 页</div>"
            ),
        )
        browser.close()

    size_mb = OUT_PDF.stat().st_size / (1024 * 1024)
    print(f"Created {OUT_PDF} ({size_mb:.2f} MB)")
    return OUT_PDF


def main() -> int:
    export_pdf()
    return 0


if __name__ == "__main__":
    sys.exit(main())
