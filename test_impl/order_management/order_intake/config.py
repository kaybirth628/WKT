from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

# 项目根目录：.../WKT
ROOT = Path(__file__).resolve().parents[3]
SECRETS_FILE = ROOT / "config" / "secrets.local.json"


class IntakeConfig:
    """读取 DeepSeek 配置。优先环境变量，其次本地密钥文件。密钥不入源码、不入库。"""

    def __init__(self) -> None:
        self._file_cfg = self._load_file()

    @staticmethod
    def _load_file() -> dict:
        if SECRETS_FILE.exists():
            try:
                return json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                return {}
        return {}

    @property
    def api_key(self) -> Optional[str]:
        return os.environ.get("DEEPSEEK_API_KEY") or self._file_cfg.get("deepseek_api_key")

    @property
    def base_url(self) -> str:
        return (
            os.environ.get("DEEPSEEK_BASE_URL")
            or self._file_cfg.get("deepseek_base_url")
            or "https://api.deepseek.com"
        )

    @property
    def model(self) -> str:
        return (
            os.environ.get("DEEPSEEK_MODEL")
            or self._file_cfg.get("deepseek_model")
            or "deepseek-v4-pro"
        )

    @property
    def assistant_model(self) -> str:
        return (
            os.environ.get("DEEPSEEK_ASSISTANT_MODEL")
            or self._file_cfg.get("deepseek_assistant_model")
            or "deepseek-chat"
        )

    def require_api_key(self) -> str:
        key = self.api_key
        if not key:
            raise ValueError(
                "未配置 DeepSeek API Key。请在 config/secrets.local.json 填写 "
                "deepseek_api_key，或设置环境变量 DEEPSEEK_API_KEY。"
            )
        return key

    @property
    def baidu_ocr_api_key(self) -> Optional[str]:
        return os.environ.get("BAIDU_OCR_API_KEY") or self._file_cfg.get("baidu_ocr_api_key")

    @property
    def baidu_ocr_secret_key(self) -> Optional[str]:
        return os.environ.get("BAIDU_OCR_SECRET_KEY") or self._file_cfg.get("baidu_ocr_secret_key")

    def baidu_ocr_configured(self) -> bool:
        return bool(self.baidu_ocr_api_key and self.baidu_ocr_secret_key)
