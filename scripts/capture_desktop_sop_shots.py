#!/usr/bin/env python3
"""Capture Windows desktop shots for SOP: Explorer (bat) + service window."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "SOP" / "images"
BAT = ROOT / "一键启动网页.bat"


def ensure_deps() -> None:
    try:
        import mss  # noqa: F401
        import pygetwindow  # noqa: F401
    except ImportError as exc:
        raise SystemExit("Run: pip install mss pygetwindow") from exc


def capture_window(
    title_keywords: list[str],
    out_name: str,
    *,
    timeout: float = 8.0,
    exclude_keywords: list[str] | None = None,
) -> bool:
    import mss
    import pygetwindow as gw
    from PIL import Image

    exclude = [k.lower() for k in (exclude_keywords or [])]
    deadline = time.time() + timeout
    win = None
    while time.time() < deadline:
        for w in gw.getAllWindows():
            t = w.title or ""
            if not t.strip():
                continue
            tl = t.lower()
            if exclude and any(k in tl for k in exclude):
                continue
            if any(k.lower() in tl for k in title_keywords):
                if w.width > 200 and w.height > 150:
                    win = w
                    break
        if win:
            break
        time.sleep(0.4)

    if not win:
        return False

    try:
        if win.isMinimized:
            win.restore()
        win.activate()
    except Exception:
        pass
    time.sleep(0.8)

    left = max(0, win.left)
    top = max(0, win.top)
    width = max(200, win.width)
    height = max(150, win.height)

    with mss.mss() as sct:
        shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        path = OUT / out_name
        img.save(path, optimize=True)
        print(f"  OK  {out_name}  ({win.title!r})")
        return True


def capture_explorer_bat() -> bool:
    if not BAT.is_file():
        print(f"  skip explorer: missing {BAT}")
        return False
    subprocess.Popen(
        ["explorer.exe", f"/select,{BAT}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2.0)
    return capture_window(
        ["WKT", "一键启动", "explorer", "文件资源管理器", "File Explorer"],
        "00-start-bat.png",
        timeout=10.0,
    )


def _close_explorer_wkt() -> None:
    import pygetwindow as gw

    for w in gw.getAllWindows():
        t = w.title or ""
        if "WKT" in t and ("资源管理器" in t or "Explorer" in t):
            try:
                w.close()
            except Exception:
                pass
    time.sleep(0.5)


def capture_service_window() -> bool:
    _close_explorer_wkt()
    # Prefer existing Flask/PowerShell service window (not Explorer)
    if capture_window(
        ["WKT Web Service", "app.py"],
        "00-cmd-window.png",
        timeout=4.0,
        exclude_keywords=["资源管理器", "explorer", "cursor", "visual studio"],
    ):
        return True
    if capture_window(
        ["python", "Flask"],
        "00-cmd-window.png",
        timeout=4.0,
        exclude_keywords=["资源管理器", "explorer", "cursor"],
    ):
        return True

    # Open a demo service window matching restart_web.ps1 style
    ps_cmd = (
        "$host.ui.RawUI.WindowTitle='WKT Web Service'; "
        "Write-Host ''; "
        "Write-Host '==========================================' -ForegroundColor Cyan; "
        "Write-Host '  WKT - web service (demo for SOP)' -ForegroundColor Cyan; "
        "Write-Host '==========================================' -ForegroundColor Cyan; "
        "Write-Host ''; "
        "Write-Host '  OK: http://127.0.0.1:5000' -ForegroundColor Green; "
        "Write-Host '  Service runs in this window. Close it to stop.' -ForegroundColor DarkGray; "
        "Write-Host ''; "
        "Write-Host '  * Running on http://127.0.0.1:5000' -ForegroundColor Yellow; "
        "Write-Host '  Press CTRL+C to quit' -ForegroundColor DarkGray; "
        "while ($true) { Start-Sleep 60 }"
    )
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoExit",
            "-Command",
            ps_cmd,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    time.sleep(2.5)
    ok = capture_window(
        ["WKT Web Service"],
        "00-cmd-window.png",
        timeout=12.0,
        exclude_keywords=["资源管理器", "explorer", "cursor"],
    )
    return ok


def main() -> int:
    ensure_deps()
    OUT.mkdir(parents=True, exist_ok=True)

    print("Desktop captures ->", OUT)
    ok1 = capture_explorer_bat()
    ok2 = capture_service_window()

    if not ok1:
        print("  WARN  explorer bat shot failed; keeping previous 00-start-bat.png if any")
    if not ok2:
        print("  WARN  service window shot failed; keeping previous 00-cmd-window.png if any")

    return 0 if (ok1 or ok2) else 1


if __name__ == "__main__":
    sys.exit(main())
