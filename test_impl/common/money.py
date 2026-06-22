"""
金额格式统一标准（单一来源）。

口径（全系统统一，严禁用 float 做金额运算）：
- 金额 / 税额 / 折扣 / 合计：DECIMAL(18,2)，2 位小数。
- 订单数量（PO数量、已出货、未结数量）：DECIMAL(18,1)，1 位小数。
- 单重（g，数字录入）：DECIMAL(18,2)，2 位小数；非数字备注原样保留。
- 单价（含税/未税、物料单价等）：DECIMAL(18,4)，4 位小数。
- 汇率：DECIMAL(12,6)，6 位小数。
- 舍入：财务四舍五入 ROUND_HALF_UP，禁止截断。
- 展示：千分位分隔；整数不补小数，有小数则保留（去掉尾部零，不超过字段精度）。
- 传输/接口：纯数字字符串，无千分位、无货币符号；整数不写小数点。
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Union

Number = Union[str, int, float, Decimal, None]

AMOUNT_DP = 2   # 金额小数位
QTY_DP = 1      # 订单数量小数位（PO / 已出货 / 未结）
WEIGHT_DP = 2   # 单重 g（数字）
PRICE_DP = 4    # 单价小数位
RATE_DP = 6     # 汇率小数位
OPEN_QTY_EPS = Decimal("0.05")  # 未结数量与 Excel 比对容差（0.1 位数量的一半）


def to_decimal(value: Number, default: str = "0", *, field: str = "") -> Decimal:
    """安全转 Decimal。空值取默认；float 先转字符串避免精度污染。"""
    if value is None or value == "":
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip().replace(",", ""))
    except InvalidOperation as exc:
        label = f"「{field}」" if field else "该字段"
        raise ValueError(f"{label}不是有效数字：{value!r}") from exc


def _round(value: Number, dp: int) -> Decimal:
    q = Decimal(1).scaleb(-dp)  # 10^-dp，如 dp=2 -> 0.01
    return to_decimal(value).quantize(q, rounding=ROUND_HALF_UP)


def round_amount(value: Number) -> Decimal:
    return _round(value, AMOUNT_DP)


def round_qty(value: Number) -> Decimal:
    """订单数量：PO、已出货、未结（1 位，ROUND_HALF_UP）。"""
    return _round(value, QTY_DP)


def round_weight(value: Number) -> Decimal:
    """单重 g（数字，2 位，ROUND_HALF_UP）。"""
    return _round(value, WEIGHT_DP)


def round_price(value: Number) -> Decimal:
    return _round(value, PRICE_DP)


def round_rate(value: Number) -> Decimal:
    return _round(value, RATE_DP)


def transport(value: Number, dp: int = AMOUNT_DP) -> str:
    """对外传输/接口用：纯数字字符串，无千分位（兼容固定小数位）。"""
    return f"{_round(value, dp):.{dp}f}"


def _plain_decimal_str(d: Decimal, max_dp: int) -> str:
    """整数无小数点；有小数则保留有效位（去尾部零）。"""
    negative = d < 0
    d = abs(_round(d, max_dp))
    if d == d.to_integral_value():
        body = str(int(d.to_integral_value()))
    else:
        body = format(d, f".{max_dp}f").rstrip("0").rstrip(".") or "0"
    return f"-{body}" if negative else body


def serialize_decimal(value: Number, max_dp: int) -> str:
    """接口/存储：无千分位，整数不写小数点。"""
    return _plain_decimal_str(to_decimal(value), max_dp)


def serialize_qty(value: Number) -> str:
    return serialize_decimal(value, QTY_DP)


def serialize_amount(value: Number) -> str:
    return serialize_decimal(value, AMOUNT_DP)


def serialize_price(value: Number) -> str:
    return serialize_decimal(value, PRICE_DP)


def serialize_weight(value: Number) -> str:
    return serialize_decimal(value, WEIGHT_DP)


def fmt_smart(value: Number, max_dp: int) -> str:
    """展示：千分位；整数不补小数，有小数则保留（最多 max_dp 位）。"""
    d = _round(value, max_dp)
    negative = d < 0
    d = abs(d)
    if d == d.to_integral_value():
        s = f"{d.to_integral_value():,}"
    else:
        s = f"{d:,.{max_dp}f}".rstrip("0").rstrip(".")
    return f"-{s}" if negative else s


def fmt_amount(value: Number) -> str:
    return fmt_smart(value, AMOUNT_DP)


def fmt_qty(value: Number) -> str:
    return fmt_smart(value, QTY_DP)


def fmt_weight(value: Number) -> str:
    return fmt_smart(value, WEIGHT_DP)


def fmt_price(value: Number) -> str:
    return fmt_smart(value, PRICE_DP)


def fmt_rate(value: Number) -> str:
    return _fmt(value, RATE_DP)


# ------------------ 人民币大写 ------------------
_CN_NUM = "零壹贰叁肆伍陆柒捌玖"
_CN_UNIT = ["", "拾", "佰", "仟"]
_CN_BIG = ["", "万", "亿", "兆"]


def _four_to_cn(seg: str) -> str:
    """把不超过 4 位的整数字符串转大写（不含万/亿等大单位）。"""
    res = ""
    zero = False
    length = len(seg)
    for i, ch in enumerate(seg):
        n = int(ch)
        pos = length - i - 1
        if n == 0:
            zero = True
        else:
            if zero and res:
                res += "零"
            zero = False
            res += _CN_NUM[n] + _CN_UNIT[pos]
    return res


def rmb_upper(value: Number) -> str:
    """金额转中文大写，标准财务写法。例：12345.67 -> 人民币壹万贰仟叁佰肆拾伍元陆角柒分。"""
    d = round_amount(value)
    if d == 0:
        return "人民币零元整"
    negative = d < 0
    d = abs(d)

    s = f"{d:.2f}"
    int_str, frac_str = s.split(".")

    # 整数部分（按 4 位分组）
    int_cn = ""
    if int(int_str) != 0:
        groups = []
        t = int_str
        while t:
            groups.append(t[-4:])
            t = t[:-4]
        parts = []
        for gi in range(len(groups) - 1, -1, -1):
            seg = groups[gi]
            seg_cn = _four_to_cn(seg)
            if seg_cn == "":
                # 整组为 0：若更低位仍有非零，补一个"零"
                lower_nonzero = any(int(groups[k]) != 0 for k in range(gi - 1, -1, -1))
                if parts and lower_nonzero and not parts[-1].endswith("零"):
                    parts.append("零")
            else:
                # 本组有前导 0 且前面已有内容，补"零"
                if parts and len(seg) == 4 and seg[0] == "0" and not parts[-1].endswith("零"):
                    parts.append("零")
                parts.append(seg_cn + _CN_BIG[gi])
        int_cn = "".join(parts)

    result = int_cn + "元" if int_cn else ""

    jiao = int(frac_str[0])
    fen = int(frac_str[1])
    if jiao == 0 and fen == 0:
        result = (result + "整") if result else "零元整"
    else:
        if jiao > 0:
            result += _CN_NUM[jiao] + "角"
        elif result:  # 有元、角为0、分非0 -> 元后补零
            result += "零"
        if fen > 0:
            result += _CN_NUM[fen] + "分"

    return ("人民币负" + result) if negative else ("人民币" + result)
