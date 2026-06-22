"""飞书自定义机器人 Webhook 通知。"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_FILE = _ROOT / "data" / "feishu_config.json"

_DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "webhook_url": "",
    "sign_secret": "",
    "app_name": "WKT销售系统",
    "events": {
        "line_created": True,
        "line_updated": True,
        "line_deleted": True,
        "line_shipped": True,
        "import_completed": True,
    },
}


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def load_feishu_config() -> dict:
    cfg = dict(_DEFAULT_CONFIG)
    cfg.update(_load_json(_CONFIG_FILE))
    env_url = (os.environ.get("FEISHU_WEBHOOK_URL") or "").strip()
    if env_url:
        cfg["webhook_url"] = env_url
    env_secret = (os.environ.get("FEISHU_SIGN_SECRET") or "").strip()
    if env_secret:
        cfg["sign_secret"] = env_secret
    if os.environ.get("FEISHU_ENABLED", "").strip().lower() in ("1", "true", "yes"):
        cfg["enabled"] = True
    events = dict(_DEFAULT_CONFIG["events"])
    if isinstance(cfg.get("events"), dict):
        events.update({k: bool(v) for k, v in cfg["events"].items()})
    cfg["events"] = events
    return cfg


def save_feishu_config(data: dict) -> dict:
    cfg = load_feishu_config()
    if "enabled" in data:
        cfg["enabled"] = bool(data["enabled"])
    if "webhook_url" in data:
        cfg["webhook_url"] = str(data["webhook_url"] or "").strip()
    if "sign_secret" in data:
        cfg["sign_secret"] = str(data["sign_secret"] or "").strip()
    if "app_name" in data:
        cfg["app_name"] = str(data["app_name"] or "WKT销售系统").strip() or "WKT销售系统"
    if isinstance(data.get("events"), dict):
        ev = dict(cfg["events"])
        ev.update({k: bool(v) for k, v in data["events"].items()})
        cfg["events"] = ev
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    to_save = {
        "enabled": cfg["enabled"],
        "webhook_url": cfg["webhook_url"],
        "sign_secret": cfg["sign_secret"],
        "app_name": cfg["app_name"],
        "events": cfg["events"],
    }
    _CONFIG_FILE.write_text(json.dumps(to_save, ensure_ascii=False, indent=2), encoding="utf-8")
    return public_feishu_config(cfg)


def public_feishu_config(cfg: Optional[dict] = None) -> dict:
    cfg = cfg or load_feishu_config()
    url = (cfg.get("webhook_url") or "").strip()
    return {
        "enabled": bool(cfg.get("enabled")),
        "configured": bool(url),
        "webhook_url_masked": _mask_url(url),
        "has_sign_secret": bool((cfg.get("sign_secret") or "").strip()),
        "app_name": cfg.get("app_name") or "WKT销售系统",
        "events": dict(cfg.get("events") or {}),
    }


def _mask_url(url: str) -> str:
    if not url:
        return ""
    if len(url) <= 24:
        return url[:8] + "…"
    return url[:20] + "…" + url[-6:]


def _sign_payload(secret: str, timestamp: str) -> str:
    s = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(s, digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def send_text(webhook_url: str, text: str, *, sign_secret: str = "") -> None:
    webhook_url = (webhook_url or "").strip()
    if not webhook_url:
        raise ValueError("未配置飞书 Webhook 地址")
    body = {"msg_type": "text", "content": {"text": text}}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    if sign_secret:
        ts = str(int(time.time()))
        req.add_header("timestamp", ts)
        req.add_header("sign", _sign_payload(sign_secret, ts))
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if resp.status >= 400:
                raise ValueError(f"飞书返回 HTTP {resp.status}: {raw[:200]}")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                return
            if isinstance(payload, dict) and payload.get("code") not in (0, None):
                raise ValueError(f"飞书返回错误: {payload.get('msg') or payload}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:200]
        raise ValueError(f"飞书 HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"无法连接飞书: {exc.reason}") from exc


class FeishuNotifier:
    def __init__(self) -> None:
        self._suppress = threading.local()

    def is_configured(self) -> bool:
        cfg = load_feishu_config()
        return bool(cfg.get("enabled")) and bool((cfg.get("webhook_url") or "").strip())

    def event_enabled(self, event: str) -> bool:
        cfg = load_feishu_config()
        if not cfg.get("enabled"):
            return False
        if not (cfg.get("webhook_url") or "").strip():
            return False
        return bool((cfg.get("events") or {}).get(event, True))

    def notify_text(self, text: str, *, event: str = "") -> bool:
        if getattr(self._suppress, "active", False):
            return False
        if event and not self.event_enabled(event):
            return False
        cfg = load_feishu_config()
        if not cfg.get("enabled") or not (cfg.get("webhook_url") or "").strip():
            return False
        send_text(
            cfg["webhook_url"],
            text,
            sign_secret=str(cfg.get("sign_secret") or ""),
        )
        return True

    def notify_async(self, text: str, *, event: str = "") -> None:
        def _run() -> None:
            try:
                self.notify_text(text, event=event)
            except Exception:
                logger.exception("飞书通知发送失败 event=%s", event)

        threading.Thread(target=_run, daemon=True).start()

    def suppress(self):
        return _NotifySuppress(self)


class _NotifySuppress:
    def __init__(self, notifier: FeishuNotifier) -> None:
        self._notifier = notifier
        self._prev = False

    def __enter__(self):
        self._prev = bool(getattr(self._notifier._suppress, "active", False))
        self._notifier._suppress.active = True
        return self

    def __exit__(self, *args):
        self._notifier._suppress.active = self._prev


feishu_notifier = FeishuNotifier()
