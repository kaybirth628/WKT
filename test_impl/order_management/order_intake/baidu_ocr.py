"""百度 OCR 高精度版（方案二，云端在线识别）。"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, Tuple

from .config import IntakeConfig

SCHEME_B_NAME = "百度 OCR 高精度"
_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
_OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
_MAX_SIDE = 4096

_token_cache: dict = {"token": "", "expires_at": 0.0}


class BaiduOcrError(Exception):
    pass


def _get_credentials(config: Optional[IntakeConfig] = None) -> Tuple[str, str]:
    cfg = config or IntakeConfig()
    api_key = cfg.baidu_ocr_api_key
    secret_key = cfg.baidu_ocr_secret_key
    if not api_key or not secret_key:
        raise BaiduOcrError(
            "未配置百度 OCR。请在 config/secrets.local.json 填写 "
            "baidu_ocr_api_key / baidu_ocr_secret_key，"
            "或设置环境变量 BAIDU_OCR_API_KEY / BAIDU_OCR_SECRET_KEY。"
        )
    return api_key, secret_key


def _get_access_token(api_key: str, secret_key: str) -> str:
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 120:
        return _token_cache["token"]

    qs = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": secret_key,
        }
    )
    req = urllib.request.Request(f"{_TOKEN_URL}?{qs}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as exc:
        raise BaiduOcrError(f"获取百度 Access Token 失败：{exc.reason}") from exc

    token = data.get("access_token")
    if not token:
        raise BaiduOcrError(f"百度 Token 响应异常：{data}")
    expires_in = int(data.get("expires_in", 2592000))
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + expires_in
    return token


def _resize_image_bytes(image_bytes: bytes) -> bytes:
    import io

    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    longest = max(img.size)
    if longest > _MAX_SIDE:
        scale = _MAX_SIDE / longest
        img = img.resize(
            (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
        )
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def ocr_image_bytes(image_bytes: bytes, config: Optional[IntakeConfig] = None) -> str:
    api_key, secret_key = _get_credentials(config)
    token = _get_access_token(api_key, secret_key)
    image_bytes = _resize_image_bytes(image_bytes)
    b64 = base64.b64encode(image_bytes).decode("ascii")
    body = urllib.parse.urlencode(
        {
            "image": b64,
            "language_type": "CHN_ENG",
            "detect_direction": "true",
        }
    ).encode("utf-8")
    url = f"{_OCR_URL}?access_token={token}"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise BaiduOcrError(f"百度 OCR 请求失败 HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise BaiduOcrError(f"无法连接百度 OCR：{exc.reason}") from exc

    if result.get("error_code"):
        raise BaiduOcrError(
            f"百度 OCR 错误 {result.get('error_code')}：{result.get('error_msg', result)}"
        )

    words = result.get("words_result") or []
    if not words:
        return ""

    def _sort_key(item: dict) -> tuple:
        loc = item.get("location") or {}
        return (round(loc.get("top", 0) / 12), loc.get("left", 0))

    if any((item.get("location") for item in words)):
        words = sorted(words, key=_sort_key)
    return "\n".join(str(item.get("words", "")).strip() for item in words if item.get("words")).strip()


def ocr_pdf(file_bytes: bytes, *, dpi: int = 300, config: Optional[IntakeConfig] = None) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise BaiduOcrError("缺少 PyMuPDF 依赖") from exc

    parts = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            parts.append(ocr_image_bytes(pix.tobytes("png"), config=config))
    text = "\n".join(p for p in parts if p).strip()
    if not text:
        raise BaiduOcrError("百度 OCR 未能从该 PDF 识别出文字。")
    return text


def extract_scheme_b(
    file_bytes: bytes,
    *,
    is_pdf: bool,
    config: Optional[IntakeConfig] = None,
) -> str:
    if is_pdf:
        return ocr_pdf(file_bytes, config=config)
    return ocr_image_bytes(file_bytes, config=config)
