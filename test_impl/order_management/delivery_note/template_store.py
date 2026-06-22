"""送货单模板：按客户映射到 data/delivery_templates/files 下的 Excel 或内置 HTML。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[3]
TEMPLATES_ROOT = ROOT / "data" / "delivery_templates"
FILES_DIR = TEMPLATES_ROOT / "files"
MAPPING_FILE = TEMPLATES_ROOT / "mapping.json"
BUILTIN_HTML = "builtin_html"
WKT_STANDARD = "wkt_standard"


def _safe_filename(name: str) -> str:
    base = re.sub(r'[<>:"/\\|?*]', "_", (name or "").strip())
    return base[:120] or "template"


class DeliveryTemplateStore:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root else TEMPLATES_ROOT
        self.files_dir = self.root / "files"
        self.mapping_file = self.root / "mapping.json"
        self.files_dir.mkdir(parents=True, exist_ok=True)
        if not self.mapping_file.exists():
            self.mapping_file.write_text("{}", encoding="utf-8")

    def load_mapping(self) -> Dict[str, str]:
        try:
            data = json.loads(self.mapping_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k).strip(): str(v).strip() for k, v in data.items() if str(k).strip()}
        except (json.JSONDecodeError, OSError):
            pass
        return {}

    def save_mapping(self, mapping: Dict[str, str]) -> None:
        clean = {str(k).strip(): str(v).strip() for k, v in mapping.items() if str(k).strip() and str(v).strip()}
        self.mapping_file.write_text(
            json.dumps(clean, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def set_customer_template(self, customer: str, template_file: str) -> None:
        customer = (customer or "").strip()
        if not customer:
            raise ValueError("客户名称不能为空")
        mapping = self.load_mapping()
        mapping[customer] = (template_file or "").strip() or BUILTIN_HTML
        self.save_mapping(mapping)

    def remove_customer_mapping(self, customer: str) -> None:
        mapping = self.load_mapping()
        mapping.pop((customer or "").strip(), None)
        self.save_mapping(mapping)

    def list_template_files(self) -> List[str]:
        out: List[str] = []
        if not self.files_dir.is_dir():
            return out
        for p in sorted(self.files_dir.iterdir()):
            if p.is_file() and p.suffix.lower() in (".xlsx", ".xlsm"):
                out.append(p.name)
        return out

    def resolve_template_name(self, customer: str) -> str:
        customer = (customer or "").strip()
        mapping = self.load_mapping()
        if customer in mapping:
            return mapping[customer]
        return WKT_STANDARD

    def is_custom_template(self, customer: str) -> bool:
        name = self.resolve_template_name(customer)
        return name not in (WKT_STANDARD, BUILTIN_HTML)

    def resolve_template_path(self, customer: str) -> Optional[Path]:
        name = self.resolve_template_name(customer)
        if name in (WKT_STANDARD, BUILTIN_HTML):
            return None
        path = self.files_dir / name
        return path if path.is_file() else None

    def template_status(self, customer: str) -> dict:
        customer = (customer or "").strip()
        name = self.resolve_template_name(customer)
        if name in (WKT_STANDARD, BUILTIN_HTML):
            return {
                "template": WKT_STANDARD,
                "template_file": "",
                "is_wkt_standard": True,
                "is_custom_excel": False,
                "template_missing": False,
            }
        path = self.files_dir / name
        return {
            "template": name,
            "template_file": name,
            "is_wkt_standard": False,
            "is_custom_excel": True,
            "template_missing": not path.is_file(),
        }

    def save_upload(self, filename: str, data: bytes) -> str:
        if not data:
            raise ValueError("文件为空")
        ext = Path(filename).suffix.lower()
        if ext not in (".xlsx", ".xlsm"):
            raise ValueError("仅支持 .xlsx / .xlsm 送货单模板")
        safe = _safe_filename(Path(filename).stem) + ext
        dest = self.files_dir / safe
        dest.write_bytes(data)
        return safe
