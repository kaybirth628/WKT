"""上传文件名编码修复（Windows 浏览器 multipart 常见 Latin-1 误解析 UTF-8）。"""
from __future__ import annotations


def repair_utf8_mojibake(text: str) -> str:
    """将误按 Latin-1 解码的 UTF-8 中文文件名还原。"""
    s = (text or "").strip()
    if not s or not any(ord(c) > 127 for c in s):
        return s
    try:
        repaired = s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s
    if not repaired or repaired == s:
        return s
    # 修复后应更像合法文件名（含中文或常见扩展名）
    if any("\u4e00" <= ch <= "\u9fff" for ch in repaired):
        return repaired
    if repaired.endswith((".xlsx", ".xlsm")) and len(repaired) <= len(s):
        return repaired
    return s


def normalize_upload_filename(name: str) -> str:
    """规范化浏览器上传的原始文件名。"""
    from pathlib import Path

    raw = (name or "").strip().replace("\\", "/")
    raw = Path(raw).name
    return repair_utf8_mojibake(raw)
