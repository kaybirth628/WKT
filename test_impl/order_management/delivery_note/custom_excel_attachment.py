"""专用 Excel 送货单：本地打开编辑，保存后自动写入出货明细附件。"""
from __future__ import annotations

import re
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parents[3]
ATTACHMENTS_DIR = ROOT / "data" / "delivery_notes" / "attachments"

_poll_thread: Optional[threading.Thread] = None
_poll_lock = threading.Lock()
_watchers: Dict[str, dict] = {}
_save_hook: Optional[Callable[[List[int], str], None]] = None


def _safe_part(s: str, limit: int = 40) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", (s or "").strip())[:limit] or "customer"


def attachment_dir() -> Path:
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    return ATTACHMENTS_DIR


def attachment_path(rel_name: str) -> Path:
    rel = (rel_name or "").strip().replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        raise ValueError("无效的附件路径")
    return attachment_dir() / rel


def rel_name_for_event(event_id: int, *, batch: bool = False) -> str:
    if batch:
        return f"batch_{int(event_id)}.xlsx"
    return f"{int(event_id)}.xlsx"


def register_save_hook(fn: Callable[[List[int], str], None]) -> None:
    global _save_hook
    _save_hook = fn


def _commit_saved(path: Path, meta: dict) -> bool:
    event_ids: List[int] = list(meta.get("event_ids") or [])
    rel_name = str(meta.get("rel_name") or "").strip()
    if not event_ids or not rel_name:
        return True
    if not path.is_file():
        return False
    for _ in range(8):
        try:
            with path.open("rb") as f:
                f.read(1)
            break
        except OSError:
            time.sleep(0.4)
    else:
        return False
    if _save_hook:
        _save_hook(event_ids, rel_name)
    return True


def _poll_watchers() -> None:
    while True:
        time.sleep(1.0)
        now = time.time()
        done_keys: List[str] = []
        with _poll_lock:
            items = list(_watchers.items())
        for key, meta in items:
            path = Path(meta.get("path") or "")
            if not path.is_file():
                continue
            try:
                st = path.stat()
            except OSError:
                continue
            mtime = st.st_mtime
            size = st.st_size
            last_mtime = meta.get("last_mtime")
            last_size = meta.get("last_size")
            if mtime != last_mtime or size != last_size:
                meta["last_mtime"] = mtime
                meta["last_size"] = size
                meta["stable_since"] = None
                with _poll_lock:
                    _watchers[key] = meta
                continue
            if meta.get("stable_since") is None:
                meta["stable_since"] = now
                with _poll_lock:
                    _watchers[key] = meta
                continue
            if now - float(meta["stable_since"]) < 1.5:
                continue
            if _commit_saved(path, meta):
                done_keys.append(key)
        if done_keys:
            with _poll_lock:
                for key in done_keys:
                    _watchers.pop(key, None)


def ensure_poll_thread() -> None:
    global _poll_thread
    if _poll_thread and _poll_thread.is_alive():
        return
    _poll_thread = threading.Thread(target=_poll_watchers, name="custom-excel-attachment-watch", daemon=True)
    _poll_thread.start()


def register_watch(event_ids: List[int], rel_name: str, path: Path) -> None:
    ensure_poll_thread()
    key = str(path.resolve())
    try:
        st = path.stat()
        last_mtime = st.st_mtime
        last_size = st.st_size
    except OSError:
        last_mtime = 0.0
        last_size = 0
    with _poll_lock:
        _watchers[key] = {
            "path": path,
            "event_ids": [int(x) for x in event_ids if int(x) > 0],
            "rel_name": rel_name,
            "last_mtime": last_mtime,
            "last_size": last_size,
            "stable_since": None,
        }


def open_in_excel(path: Path) -> None:
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"文件不存在：{path}")
    if sys.platform == "win32":
        import os

        os.startfile(str(path))  # noqa: S606
        return
    import subprocess

    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)], start_new_session=True)  # noqa: S603
    else:
        subprocess.Popen(["xdg-open", str(path)], start_new_session=True)  # noqa: S603


def prepare_attachment_from_bytes(
    event_ids: List[int],
    data: bytes,
    *,
    batch: bool = False,
) -> tuple[str, Path]:
    if not event_ids:
        raise ValueError("缺少出货记录")
    if not data:
        raise ValueError("送货单内容为空")
    primary = int(event_ids[0])
    rel = rel_name_for_event(primary, batch=batch or len(event_ids) > 1)
    dest = attachment_path(rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    register_watch(event_ids, rel, dest)
    return rel, dest


def prepare_attachment_from_template(
    event_ids: List[int],
    template_path: Path,
    *,
    customer: str = "",
    batch: bool = False,
) -> tuple[str, Path]:
    if not event_ids:
        raise ValueError("缺少出货记录")
    primary = int(event_ids[0])
    rel = rel_name_for_event(primary, batch=batch or len(event_ids) > 1)
    dest = attachment_path(rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.is_file():
        shutil.copy2(template_path, dest)
    register_watch(event_ids, rel, dest)
    return rel, dest


def resolve_open_path(
    event_id: int,
    template_path: Path,
    *,
    customer: str = "",
    batch_event_ids: Optional[List[int]] = None,
    existing_rel: str = "",
) -> tuple[str, Path]:
    ids = batch_event_ids if batch_event_ids else [event_id]
    ids = [int(x) for x in ids if int(x) > 0]
    if not ids:
        raise ValueError("缺少出货记录")
    primary = ids[0]
    batch = len(ids) > 1
    rel = (existing_rel or "").strip()
    if rel:
        path = attachment_path(rel)
        if path.is_file():
            register_watch(ids, rel, path)
            return rel, path
    rel, path = prepare_attachment_from_template(
        ids,
        template_path,
        customer=customer,
        batch=batch,
    )
    return rel, path
