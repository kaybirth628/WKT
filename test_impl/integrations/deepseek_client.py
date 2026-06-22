from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, List, Optional

from test_impl.order_management.order_intake.config import IntakeConfig

_MAX_RETRIES = 3
_RETRY_DELAYS_SEC = (1.0, 2.0, 4.0)


class DeepSeekClientError(Exception):
    pass


class DeepSeekChatClient:
    """DeepSeek Chat Completions（与 OCR 结构化共用密钥配置）。"""

    def __init__(self, config: Optional[IntakeConfig] = None) -> None:
        self.config = config or IntakeConfig()

    @property
    def assistant_model(self) -> str:
        return self.config.assistant_model

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    def chat(
        self,
        messages: List[dict[str, str]],
        *,
        model: Optional[str] = None,
        response_format: Optional[dict[str, str]] = None,
        temperature: float = 0,
        max_tokens: int = 4096,
        timeout: int = 120,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model or self.assistant_model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        api_key = self.config.require_api_key()
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Connection": "close",
            "User-Agent": "WKT-SalesAssistant/1.0",
        }

        data = self._request_json(url, body, headers, timeout)

        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise DeepSeekClientError(f"DeepSeek 返回结构异常: {data}") from exc

        if choice.get("finish_reason") == "length":
            raise DeepSeekClientError("模型输出被截断，请缩小问题范围或分批查询。")
        return str(content or "").strip()

    def _request_json(
        self, url: str, body: bytes, headers: dict[str, str], timeout: int
    ) -> dict:
        last_error: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")
                if exc.code in (429, 502, 503, 504) and attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_DELAYS_SEC[attempt])
                    last_error = exc
                    continue
                raise DeepSeekClientError(
                    f"DeepSeek 请求失败 HTTP {exc.code}: {detail}"
                ) from exc
            except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError) as exc:
                last_error = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_DELAYS_SEC[attempt])
                    continue
                reason = getattr(exc, "reason", exc)
                hint = ""
                if "10054" in str(reason) or "10054" in str(exc):
                    hint = "（网络连接被中断，已自动重试仍失败，请稍后再试或检查网络/代理）"
                raise DeepSeekClientError(f"无法连接 DeepSeek: {reason}{hint}") from exc

        if last_error is not None:
            raise DeepSeekClientError(f"无法连接 DeepSeek: {last_error}") from last_error
        raise DeepSeekClientError("无法连接 DeepSeek")

    @staticmethod
    def parse_json_object(content: str) -> dict:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            parsed = json.loads(text)
        except ValueError as exc:
            raise DeepSeekClientError(f"输出非合法 JSON: {text[:500]}") from exc
        if not isinstance(parsed, dict):
            raise DeepSeekClientError("JSON 根节点必须是对象")
        return parsed
