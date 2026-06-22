from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Optional

_OCR_DPI_SCAN = 300
_MAX_SIDE = 3000

ProgressCallback = Optional[Callable[[int, str], None]]


class TextExtractionError(Exception):
    pass


@dataclass
class ExtractResult:
    text: str
    scheme: str


def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise TextExtractionError("缺少 PyMuPDF 依赖，请先安装：pip install PyMuPDF") from exc

    parts = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            parts.append(page.get_text("text"))
    return "\n".join(parts).strip()


@lru_cache(maxsize=1)
def _get_rapidocr_engine():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise TextExtractionError(
            "缺少 OCR 依赖，请先安装：pip install rapidocr-onnxruntime"
        ) from exc
    return RapidOCR()


def _rapidocr_image_bytes(image_bytes: bytes) -> str:
    import io

    import numpy as np
    from PIL import Image

    engine = _get_rapidocr_engine()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    longest = max(img.size)
    if longest > _MAX_SIDE:
        scale = _MAX_SIDE / longest
        img = img.resize(
            (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
        )
    arr = np.array(img)
    result, _ = engine(arr)
    if not result:
        return ""
    lines = sorted(result, key=lambda r: (round(r[0][0][1] / 10), r[0][0][0]))
    return "\n".join(item[1] for item in lines).strip()


def ocr_pdf(file_bytes: bytes, *, dpi: int = _OCR_DPI_SCAN) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise TextExtractionError("缺少 PyMuPDF 依赖，请先安装：pip install PyMuPDF") from exc

    parts = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            parts.append(_rapidocr_image_bytes(pix.tobytes("png")))
    text = "\n".join(p for p in parts if p).strip()
    if not text:
        raise TextExtractionError("OCR 未能从该文件中识别出文字，请确认扫描件清晰、文字端正。")
    return text


def ocr_image(file_bytes: bytes) -> str:
    text = _rapidocr_image_bytes(file_bytes)
    if not text:
        raise TextExtractionError("OCR 未能从该图片中识别出文字，请确认图片清晰、文字端正。")
    return text


def extract_text_with_meta(
    file_bytes: bytes,
    filename: str,
    progress: ProgressCallback = None,
) -> ExtractResult:
    """单路 OCR：电子版 PDF 优先文字层，扫描件/图片走 RapidOCR。"""
    name = (filename or "").lower()

    if name.endswith(".pdf"):
        if progress:
            progress(10, "正在检测 PDF 类型…")
        pdf_text = extract_pdf_text(file_bytes)
        if pdf_text:
            if progress:
                progress(35, "已读取 PDF 文字层")
            return ExtractResult(text=pdf_text, scheme="PDF 文字层")
        if progress:
            progress(15, f"RapidOCR 识别（{_OCR_DPI_SCAN} DPI）…")
        text = ocr_pdf(file_bytes, dpi=_OCR_DPI_SCAN)
        if progress:
            progress(35, "OCR 识别完成")
        return ExtractResult(text=text, scheme=f"RapidOCR（{_OCR_DPI_SCAN} DPI）")

    if name.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")):
        if progress:
            progress(15, "RapidOCR 识别图片…")
        text = ocr_image(file_bytes)
        if progress:
            progress(35, "OCR 识别完成")
        return ExtractResult(text=text, scheme="RapidOCR")

    raise TextExtractionError(f"不支持的文件类型：{filename}")


def extract_text(file_bytes: bytes, filename: str) -> str:
    return extract_text_with_meta(file_bytes, filename).text
