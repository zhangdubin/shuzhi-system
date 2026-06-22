"""
数字转中文大写金额（人民币）
- 支持小数（角分）
- 支持 0
- 接受 float / int / Decimal / str
- None / 非数字 → ""

金额读法规范（与税法一致）：
  10     -> "壹拾元整"   (十位 1 带"壹")
  12     -> "壹拾贰元整"
  100    -> "壹佰元整"
  1000   -> "壹仟元整"
  880    -> "捌佰捌拾元整"
  1234.56 -> "壹仟贰佰叁拾肆元伍角陆分"
  0.50   -> "伍角"        (没有元不补"零元")
  0.55   -> "伍角伍分"
  1000000000  -> "壹拾亿元整"
  101000000   -> "壹亿零壹拾万元整"
  100100100   -> "壹亿零壹拾万零壹佰元整"
"""
from decimal import Decimal, InvalidOperation
from typing import Union

_DIGITS = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
_CN_UNITS = ["", "拾", "佰", "仟"]   # 个 / 十 / 百 / 千
_BIG_UNITS = ["", "万", "亿", "兆"]   # 万 / 亿 / 兆（4 位一组）


def _to_decimal(amount) -> Decimal:
    if amount is None:
        raise ValueError("amount is None")
    if isinstance(amount, Decimal):
        return amount
    try:
        return Decimal(str(amount))
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"invalid amount: {amount!r}") from e


def _4digits_to_cn(n: int, leading_one_ten: bool) -> str:
    """
    把 0..9999 的整数转中文（4 位一组，不带"万/亿"）
    leading_one_ten: 金额场景始终 True（十位是 1 时也读"壹拾"）
    0     -> ""
    5     -> "伍"
    50    -> "伍拾"
    305   -> "叁佰零伍"
    310   -> "叁佰壹拾"
    1010  -> "壹仟零壹拾"
    """
    if n == 0:
        return ""
    s = ""
    thousands = n // 1000
    hundreds = (n // 100) % 10
    tens = (n // 10) % 10
    ones = n % 10

    if thousands > 0:
        s += _DIGITS[thousands] + "仟"
    if hundreds > 0:
        s += _DIGITS[hundreds] + "佰"
    elif thousands > 0 and (tens > 0 or ones > 0):
        s += "零"

    if tens > 0:
        if tens == 1 and not leading_one_ten and thousands == 0 and hundreds == 0:
            # 数字普通读法：十位是 1 且无前导 → "拾"
            s += "拾"
        else:
            # 金额读法：十位是 1 也读"壹拾"
            s += _DIGITS[tens] + "拾"
    elif hundreds > 0 and ones > 0:
        s += "零"

    if ones > 0:
        s += _DIGITS[ones]

    return s


def _int_to_cn(n: int) -> str:
    """把非负整数转中文（不带"元"），0 -> "零" """
    if n == 0:
        return "零"
    if n < 0:
        return "负" + _int_to_cn(-n)

    # 拆分成 4 位一组（从低位到高位）
    groups = []
    while n > 0:
        groups.append(n % 10000)
        n //= 10000

    # 从高位到低位组合
    # 关键：先标记每个组是否"中间空组"（前后都有非 0 组），需要补"零"
    has_nonzero_before = [False] * len(groups)
    seen_nonzero = False
    for gi in range(len(groups) - 1, -1, -1):
        if groups[gi] != 0:
            seen_nonzero = True
        has_nonzero_before[gi] = seen_nonzero

    has_nonzero_after = [False] * len(groups)
    seen_nonzero = False
    for gi in range(len(groups)):
        if groups[gi] != 0:
            seen_nonzero = True
        has_nonzero_after[gi] = seen_nonzero

    parts = []
    for gi in range(len(groups) - 1, -1, -1):
        g = groups[gi]
        big = _BIG_UNITS[gi] if gi < len(_BIG_UNITS) else ""
        if g == 0:
            # 中间空组（前后都有非 0 组）→ 补"零"
            if has_nonzero_after[gi] and has_nonzero_before[gi]:
                if parts and not parts[-1].endswith("零"):
                    parts.append("零")
            continue
        # 金额读法：所有组的十位 1 都读"壹拾"（不简化）
        seg = _4digits_to_cn(g, leading_one_ten=True)
        # 上一个 part 以大单位（亿/万）结尾（说明上组为 0），且本组以十位/百位开始（千位为 0）→ 补上"零"以避免拼接歧义
        # 上一个 part 末尾是"大单位"或"零+大单位"，且本组不以仟位开头（g<1000）→ 补"零"
        last = parts[-1] if parts else ""
        big_unit_ends = any(last.endswith(u) for u in _BIG_UNITS if u)
        zero_big_ends = any(last.endswith("零" + u) for u in _BIG_UNITS if u)
        if parts and (big_unit_ends or zero_big_ends) and g < 1000:
            seg = "零" + seg
        parts.append(seg + big)

    return "".join(parts)


def cn_capital(amount: Union[float, int, Decimal, str, None]) -> str:
    """把数字转成人民币大写字符串"""
    if amount is None or amount == "":
        return ""
    try:
        v = _to_decimal(amount)
    except ValueError:
        return ""
    if v < 0:
        return "负" + cn_capital(-v)

    # 拆 元 / 角 / 分（量化到分避免浮点误差）
    cents = int((v * 100).to_integral_value(rounding="ROUND_HALF_UP"))
    if cents == 0:
        return "零元整"
    yuan = cents // 100
    jiao = (cents // 10) % 10
    fen = cents % 10

    parts = []
    if yuan > 0:
        parts.append(_int_to_cn(yuan) + "元")
    # 注意：< 1 元时不加"零元"（行业惯例：直接读"伍角""伍分"）

    if jiao > 0:
        parts.append(_DIGITS[jiao] + "角")
    else:
        if fen > 0 and yuan > 0:
            parts.append("零")  # 元和分之间补零

    if fen > 0:
        parts.append(_DIGITS[fen] + "分")

    if jiao == 0 and fen == 0:
        parts.append("整")

    return "".join(parts)


if __name__ == "__main__":
    cases = [
        (0, "零元整"),
        (0.0, "零元整"),
        (0.50, "伍角"),
        (0.05, "伍分"),
        (0.55, "伍角伍分"),
        (1, "壹元整"),
        (10, "壹拾元整"),
        (12, "壹拾贰元整"),
        (20, "贰拾元整"),
        (100, "壹佰元整"),
        (305, "叁佰零伍元整"),
        (310, "叁佰壹拾元整"),
        (1000, "壹仟元整"),
        (1010, "壹仟零壹拾元整"),
        (1100, "壹仟壹佰元整"),
        (880, "捌佰捌拾元整"),
        (880.00, "捌佰捌拾元整"),
        (1234.56, "壹仟贰佰叁拾肆元伍角陆分"),
        (10000, "壹万元整"),
        (100000000, "壹亿元整"),
        (100000000.00, "壹亿元整"),
        (100000001, "壹亿零壹元整"),
        (101000000, "壹亿零壹佰万元整"),
        (100100100, "壹亿零壹拾万零壹佰元整"),
        (1000000000, "壹拾亿元整"),
        (Decimal("880.00"), "捌佰捌拾元整"),
        (Decimal("1234.56"), "壹仟贰佰叁拾肆元伍角陆分"),
        (-100, "负壹佰元整"),
    ]
    fail = 0
    for inp, want in cases:
        got = cn_capital(inp)
        ok = "OK  " if got == want else "FAIL"
        if got != want:
            fail += 1
        print(f"{ok}  cn_capital({inp!r:<22}) = {got!r}   (want {want!r})")
    print()
    print(f"{len(cases) - fail}/{len(cases)} pass")
