from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, List, Optional

from test_impl.order_management.order_intake.config import IntakeConfig


class DeepSeekClientError(Exception):
    pass


class DeepSeekChatClient:
    """DeepSeek Chat Completions（与 OCR 结构化共用密钥配置）。"""

    def __init__(self, config: Optional[IntakeConfig] = None) -> None:
        self.config = config or IntakeConfig()

    @property
    def assistant_model(self) -> str:
        import os

        return (
            os.environ.get("DEEPSEEK_ASSISTANT_MODEL")
            or self.config._file_cfg.get("deepseek_assistant_model")
            or "deepseek-chat"
        )

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
        timeout: int = 90,
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
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise DeepSeekClientError(f"DeepSeek 请求失败 HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise DeepSeekClientError(f"无法连接 DeepSeek: {exc.reason}") from exc

        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise DeepSeekClientError(f"DeepSeek 返回结构异常: {data}") from exc

        if choice.get("finish_reason") == "length":
            raise DeepSeekClientError("模型输出被截断，请缩小问题范围或分批查询。")
        return str(content or "").strip()

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
