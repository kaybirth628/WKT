"""Scan docs/design/awesome-design-md and expose DESIGN.md metadata for the gallery."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_ROOT = ROOT / "docs" / "design" / "awesome-design-md" / "design-md"
README = ROOT / "docs" / "design" / "awesome-design-md" / "README.md"

WKT_THEMES = {"hp", "classic", "stripe", "ibm", "notion", "minimal-white"}


def _parse_yaml_block(text: str) -> dict:
    data: dict = {}
    current_key: str | None = None
    nested: dict | None = None

    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith("  ") and current_key and nested is not None:
            m = re.match(r"\s+(\w[\w-]*):\s*(.+)$", line)
            if m:
                nested[m.group(1)] = m.group(2).strip().strip('"')
            continue
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            current_key = key
            nested = {}
            data[key] = nested
        else:
            current_key = None
            nested = None
            data[key] = val.strip('"')
    return data


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    if not m:
        return {}
    return _parse_yaml_block(m.group(1))


def _hex_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return 0.5
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _pick_color(colors: dict, *keys: str) -> str | None:
    for key in keys:
        val = colors.get(key)
        if val and re.match(r"^#[0-9a-fA-F]{3,8}$", val):
            return val
    return None


def _parse_readme_index() -> dict[str, dict]:
    """slug -> {display_name, category, tagline}"""
    index: dict[str, dict] = {}
    if not README.is_file():
        return index
    text = README.read_text(encoding="utf-8")
    category = "其他"
    for line in text.splitlines():
        if line.startswith("### "):
            category = line[4:].strip()
            continue
        m = re.match(
            r"^- \[\*\*(.+?)\*\*\]\([^)]+/([^/]+)/design-md\)\s*-\s*(.+)$",
            line.strip(),
        )
        if m:
            display, slug, tagline = m.group(1), m.group(2), m.group(3).strip()
            index[slug] = {
                "display_name": display,
                "category": category,
                "tagline": tagline,
            }
    return index


def _slug_label(slug: str) -> str:
    return slug.replace("-", " ").replace(".", " ").title()


@lru_cache(maxsize=1)
def load_design_catalog() -> list[dict]:
    readme = _parse_readme_index()
    items: list[dict] = []

    if not DESIGN_ROOT.is_dir():
        return items

    for design_dir in sorted(DESIGN_ROOT.iterdir()):
        if not design_dir.is_dir():
            continue
        md = design_dir / "DESIGN.md"
        if not md.is_file():
            continue
        slug = design_dir.name
        meta = _read_frontmatter(md)
        colors = meta.get("colors") if isinstance(meta.get("colors"), dict) else {}
        if not colors:
            colors = {k: v for k, v in meta.items() if isinstance(v, str) and v.startswith("#")}

        primary = _pick_color(colors, "primary", "brand-blue", "brand-secure")
        canvas = _pick_color(
            colors,
            "canvas",
            "inverse-canvas",
            "paper",
            "bg",
            "surface-1",
            "cloud",
        )
        ink = _pick_color(colors, "ink", "text", "inverse-ink", "ink-deep")
        accent = _pick_color(colors, "primary-hover", "primary-soft", "brand-purple", "link")

        readme_info = readme.get(slug, {})
        display = readme_info.get("display_name") or meta.get("name") or _slug_label(slug)
        if isinstance(display, str) and display.endswith("-design-analysis"):
            display = _slug_label(slug)

        description = readme_info.get("tagline") or meta.get("description") or ""
        if isinstance(description, str) and len(description) > 220:
            description = description[:217] + "..."

        lum = _hex_luminance(canvas) if canvas else 0.9
        tone = "light" if lum >= 0.55 else "dark"

        swatches = [c for c in [primary, canvas, ink, accent] if c]

        items.append(
            {
                "slug": slug,
                "name": display,
                "category": readme_info.get("category", "其他"),
                "description": description,
                "tone": tone,
                "primary": primary,
                "canvas": canvas,
                "ink": ink,
                "swatches": swatches,
                "colors": {k: v for k, v in colors.items() if isinstance(v, str) and v.startswith("#")},
                "wkt_enabled": slug in WKT_THEMES,
                "design_path": f"docs/design/awesome-design-md/design-md/{slug}/DESIGN.md",
            }
        )

    return items


def catalog_summary() -> dict:
    items = load_design_catalog()
    categories: dict[str, int] = {}
    for item in items:
        cat = item["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "total": len(items),
        "light": sum(1 for i in items if i["tone"] == "light"),
        "dark": sum(1 for i in items if i["tone"] == "dark"),
        "wkt_enabled": sum(1 for i in items if i["wkt_enabled"]),
        "categories": [{"name": k, "count": v} for k, v in sorted(categories.items())],
        "source": "https://github.com/VoltAgent/awesome-design-md",
    }
