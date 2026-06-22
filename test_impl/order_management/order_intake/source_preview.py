"""订单原件高清预览（PDF 转 PNG，供 OCR 审核对照）。"""
from __future__ import annotations

PREVIEW_DPI = 200


def render_document_preview_pages(
    file_bytes: bytes,
    filename: str,
    *,
    dpi: int = PREVIEW_DPI,
) -> list[bytes]:
    """
    返回每页 PNG 字节。图片文件原样返回单元素列表。
    PDF 按 dpi 渲染，比浏览器 iframe 嵌入更清晰。
    """
    name = (filename or "").lower()
    if name.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")):
        return [file_bytes]
    if not name.endswith(".pdf"):
        return []
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return []
    pages: list[bytes] = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            pages.append(pix.tobytes("png"))
    return pages
