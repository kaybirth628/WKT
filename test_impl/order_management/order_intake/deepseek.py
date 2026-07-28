from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

from .config import IntakeConfig

EXTRACT_SCHEMA_HINT = {
    "orders": [
        {
            "customer": "客户名称",
            "order_no": "订单号/PO号",
            "order_date": "接单日期 YYYY-MM-DD",
            "delivery_date": "客户交期 YYYY-MM-DD",
            "payment_terms": "账期（可选，按订单原文填写，如月结天数或开票说明）",
            "items": [
                {
                    "product_spec": "品名/规格",
                    "customer_part_no": "客户料号",
                    "material": "材质",
                    "unit_weight_g": "单重未含损耗(g)，数字",
                    "po_qty": "PO数量，数字",
                    "shipped_qty": "已出货数量，数字，未知填0",
                    "unit": "单位",
                    "tax_rate": "税率，小数(如0.13)，未知填0",
                    "rmb_tax_incl_price": "人民币含税单价，数字",
                }
            ],
        }
    ]
}

SYSTEM_PROMPT = (
    "你是制造业订单录入助手。用户会给你一段从订单PDF/图片中提取的原始文字，"
    "请你把它整理成结构化 JSON。只输出 JSON，不要解释。\n"
    "字段要求（严格使用这些英文键名）：\n"
    + json.dumps(EXTRACT_SCHEMA_HINT, ensure_ascii=False, indent=2)
    + "\n规则：\n"
    "1. orders 是数组。若文字中包含**多张订单**（不同订单号或不同客户/不同表格），"
    "拆分为多个 order 元素分别归类；只有一张订单时 orders 仅含一个元素。\n"
    "2. 每个 order 的 items 是数组，**每一个料号/每一行明细都单独列为一项**，"
    "有多少个料号就输出多少行，**务必完整列全，不得遗漏、不得合并、不得省略、不得只取前几行**；"
    "即使有几十行也要逐行全部输出。找不到的字段用空字符串或 0。\n"
    "3. 同一料号在多处出现时按原单据如实列出，不要自行去重或汇总。\n"
    "4. 数字字段不要带单位或逗号。\n"
    "5. 税率用小数表示（13% => 0.13）。\n"
    "6. 日期统一 YYYY-MM-DD，无法确定则留空字符串。\n"
    "7. 不要编造不存在的订单或明细行。\n"
    "8. **客户料号 customer_part_no** 取自表格中标识物料的独立编码列，列名可能是："
    "客户料号、料号、物料编码、物料号、图号、零件号、原始编码（有值时）等。"
    "常见格式：B 开头 10 位（如 B6010001370）、数字-数字（如 1-000797）、字母数字混合。"
    "**每一行明细必须有 customer_part_no**；若「原始编码」为空但「物料编码」有值，用物料编码。"
    "**禁止**把品名规格路径中的短编号（如「散热片/8513 ADC12…」里的 8513）"
    "或规格尺寸数字误填为客户料号。\n"
    "9. **客户交期 delivery_date** 仅填该行明细对应的交期；"
    "若原文只有表头/订单级日期而该行无交期，则留空，勿把其他行的日期套到每一行。"
)

RETRY_USER_SUFFIX = (
    "\n\n【重要】上次提取中客户料号(customer_part_no)或明细行有遗漏。"
    "请重新通读全文，务必补全每一行的客户料号（含「物料编码/物料号/原始编码」列）、"
    "品名规格、PO数量。"
)


class DeepSeekError(Exception):
    pass


class DeepSeekStructurer:
    """调用 DeepSeek 把原始文字结构化为订单 JSON。"""

    def __init__(self, config: Optional[IntakeConfig] = None) -> None:
        self.config = config or IntakeConfig()

    def structure(self, raw_text: str, timeout: int = 90) -> dict:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "以下是订单原始文字，请输出 json：\n\n" + raw_text},
            ],
            "response_format": {"type": "json_object"},
            "stream": False,
            "temperature": 0,
            "max_tokens": 16384,
        }
        return self._request_json(payload, timeout)

    def structure_retry(self, raw_text: str, timeout: int = 90) -> dict:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "以下是订单原始文字，请输出 json：" + RETRY_USER_SUFFIX + "\n\n" + raw_text,
                },
            ],
            "response_format": {"type": "json_object"},
            "stream": False,
            "temperature": 0,
            "max_tokens": 16384,
        }
        return self._request_json(payload, timeout)

    def _request_json(self, payload: dict, timeout: int) -> dict:
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
            raise DeepSeekError(f"DeepSeek 请求失败 HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise DeepSeekError(f"无法连接 DeepSeek: {exc.reason}") from exc

        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise DeepSeekError(f"DeepSeek 返回结构异常: {data}") from exc

        if choice.get("finish_reason") == "length":
            raise DeepSeekError(
                "订单明细行数过多，识别结果被截断。请将该订单拆分为多个文件分批上传，或联系开发提高输出上限。"
            )
        return self._parse_json(content)

    @staticmethod
    def _parse_json(content: str) -> dict:
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:]
            content = content.strip()
        try:
            return json.loads(content)
        except ValueError as exc:
            raise DeepSeekError(f"DeepSeek 输出非合法 JSON: {content[:500]}") from exc
