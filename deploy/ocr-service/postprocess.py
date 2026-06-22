"""
发票字段抽取（基于正则 + 启发式位置）
- 入参：PaddleOCR 原始识别结果 [ (poly, text, conf), ... ]
- 出参：dict 字段（invoiceNo/invoiceCode/issueDate/buyerName/sellerName/totalAmount/taxAmount/...）

关键策略：
1. **多行合并**：把垂直距离近的相邻行合并为一条（避免标题被拆成多行）
2. **位置估算**：增值税电子发票字段位置是国标固定的
   - 顶部：「电子发票」+「普通发票/专用发票」
   - 右上：发票号码（8 位数字）+ 开票日期
   - 左上：购买方信息（名称 + 纳税人识别号）
   - 左下：销售方信息（名称 + 纳税人识别号）
   - 右上角：价税合计 + 大写金额
   - 中下：金额（不含税）+ 税率 + 税额
3. **正则优先**：发票号 8-20 位数字、金额 X.XX、税号 18 位（大写字母+数字）
4. **置信度回退**：缺字段的 confidence 用整页平均补

不依赖版面分析（layout），只依赖 OCR 行文本 + Y 轴排序。
"""
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple


# ============================================================
# 正则
# ============================================================
# 发票号码：8-20 位数字（电子普票 8 位、专票 8-12 位、电子专用 20 位）
RE_INVOICE_NO = re.compile(r"\b(\d{8,20})\b")
# 发票代码：10-12 位数字（部分新版电子发票已无发票代码）
RE_INVOICE_CODE = re.compile(r"\b(\d{10,12})\b")
# 纳税人识别号：18 位（A-Z 0-9）
RE_TAX_NO = re.compile(r"[0-9A-Z]{15,20}")
# 开票日期：YYYY年MM月DD日 或 YYYY-MM-DD
RE_DATE_CN = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
RE_DATE_DASH = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
# 金额（不含税、税额、价税合计）：¥1,234.56 或 1234.56
RE_AMOUNT = re.compile(r"[¥￥]\s*((?:[0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)\.[0-9]{1,2})")
# 税率：13%、6%、3%、9%
RE_TAX_RATE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
# 大写金额：零壹贰叁肆伍陆柒捌玖
RE_CN_UPPER = re.compile(r"[零壹贰叁肆伍陆柒捌玖佰仟万亿圆元角分整]+")


# ============================================================
# 多行合并
# ============================================================
def _merge_lines(items: List[Tuple], y_threshold: int = 15) -> List[Tuple]:
    """
    把垂直距离 < y_threshold **且 X 范围重叠** 的相邻行合并
    items: [(poly, text, conf), ...]（已按 Y 排序）
    返回：[(merged_poly, merged_text, merged_conf), ...]
    """
    if not items:
        return []
    # 算每行的 Y 中心 + X 范围
    yx = []
    for it in items:
        poly, text, conf = it
        ys = [p[1] for p in poly]
        xs = [p[0] for p in poly]
        cy = sum(ys) / 4
        cx = sum(xs) / 4
        x_min = min(xs)
        x_max = max(xs)
        yx.append((it, cy, cx, x_min, x_max))
    yx.sort(key=lambda t: t[1])

    merged = []
    current = [yx[0]]
    for it, cy, cx, xmin, xmax in yx[1:]:
        prev_it, prev_cy, prev_cx, prev_xmin, prev_xmax = current[-1]
        # 条件：Y 接近 **且** X 范围重叠
        y_close = abs(cy - prev_cy) < y_threshold
        x_overlap = not (xmax < prev_xmin or xmin > prev_xmax)  # 区间相交
        if y_close and x_overlap:
            current.append((it, cy, cx, xmin, xmax))
        else:
            merged.append(_merge_one_group(current))
            current = [(it, cy, cx, xmin, xmax)]
    if current:
        merged.append(_merge_one_group(current))
    return merged


def _merge_one_group(group: List[Tuple]) -> Tuple:
    """把同组按 X 排序拼成一个 (poly, text, conf)
    group: [(it, cy, cx, xmin, xmax), ...]
    """
    # 按 cx（X 中心）排序
    group.sort(key=lambda t: t[2])
    polys = []
    texts = []
    confs = []
    for entry in group:
        # entry = (it, cy, cx, xmin, xmax) 或老格式 (it, cy, cx)
        it = entry[0]
        polys.append(it[0])
        texts.append(it[1])
        confs.append(it[2])
    first_poly = polys[0]
    last_poly = polys[-1]
    merged_poly = [
        first_poly[0],
        last_poly[1],
        last_poly[2],
        first_poly[3],
    ]
    merged_text = "".join(texts)
    merged_conf = sum(confs) / len(confs)
    return (merged_poly, merged_text, merged_conf)


# ============================================================
# 字段抽取
# ============================================================
def extract_invoice_fields(items: List[Tuple]) -> Dict[str, dict]:
    """
    抽取增值税电子发票字段
    items: PaddleOCR 原始识别结果 [ (poly, text, conf), ... ]
    """
    if not items:
        return {}

    # 0. 类型检测：航空电子客票 / 火车票 / 通用增值税发票
    full_text_raw = " ".join(t for _, t, _ in items)

    # 航空电子客票行程单（优先级最高，避免被火车票分支抢走）
    # 考虑 PaddleOCR 误识："航空" 可能变成 "抗空"/"抗空运输"/"航室"等，多策略匹配
    flight_kw = ("民航发展基金", "燃油附加费", "航班号", "承运人", "机票", "客票生效日期", "免费行李")
    flight_kw_weak = ("航空运输电子客票行程单", "航空运输电子客票", "抗空运输", "舱位", "乘机人")
    has_strong = any(kw in full_text_raw for kw in flight_kw)
    has_weak = any(kw in full_text_raw for kw in flight_kw_weak)
    # 强特征必中，或弱特征 + 背景口录在同一份里同时出现两个以上
    if has_strong or has_weak:
        return _extract_flight_ticket_fields(items)

    # 火车票
    train_kw = ("铁路电子客票", "电子客票号", "车次", "二等座", "硬座", "软座", "商务座", "特等座", "动车", "高铁")
    if any(kw in full_text_raw for kw in train_kw):
        return _extract_train_ticket_fields(items)

    # 1. 多行合并
    merged = _merge_lines(items, y_threshold=25)

    # 2. 抽每行的纯文本
    lines = [(it[0], it[1].strip(), it[2]) for it in merged if it[1].strip()]

    print(f"[ocr] raw={len(items)} merged={len(merged)} non_empty={len(lines)}", flush=True)

    # 3. 综合置信度（整页平均）
    overall_conf = sum(c for _, _, c in items) / max(1, len(items))

    fields: Dict[str, dict] = {}
    full_text = "\n".join(t for _, t, _ in lines)

    # ===== 发票号（8-20 位数字，最高置信度的那行）=====
    invoice_no_candidates = []
    for poly, text, conf in lines:
        m = RE_INVOICE_NO.search(text)
        if m:
            invoice_no_candidates.append((m.group(1), conf, poly, text))
    if invoice_no_candidates:
        # 优先选 confidence 最高的
        invoice_no_candidates.sort(key=lambda x: x[1], reverse=True)
        no, conf, _, _ = invoice_no_candidates[0]
        fields["invoiceNo"] = {"value": no, "confidence": _pct(conf)}

    # ===== 发票代码（10-12 位数字，且与发票号不同时）=====
    for poly, text, conf in lines:
        m = RE_INVOICE_CODE.search(text)
        if m:
            code = m.group(1)
            # 排除和发票号相同的
            if fields.get("invoiceNo", {}).get("value") != code:
                # 排除金额（金额一般不是纯数字长度 10-12）
                # 这里靠启发：发票代码一般前后无 ¥ 符号
                if "¥" not in text and "￥" not in text and len(code) >= 10:
                    fields["invoiceCode"] = {"value": code, "confidence": _pct(conf)}
                    break

    # ===== 开票日期 =====
    for poly, text, conf in lines:
        m = RE_DATE_CN.search(text)
        if m:
            y, mo, d = m.groups()
            try:
                dt = date(int(y), int(mo), int(d))
                fields["issueDate"] = {"value": dt.isoformat(), "confidence": _pct(conf)}
                break
            except ValueError:
                pass
        m = RE_DATE_DASH.search(text)
        if m:
            y, mo, d = m.groups()
            try:
                dt = date(int(y), int(mo), int(d))
                fields["issueDate"] = {"value": dt.isoformat(), "confidence": _pct(conf)}
                break
            except ValueError:
                pass

    # ===== 购买方/销售方（靠"购买方""销售方""名称"标识）=====
    _extract_buyer_seller(lines, fields)
    _extract_tax_no(lines, fields)
    _extract_items(lines, fields)

    # ===== 金额：只认"¥/￥" 开头的金额（明细行数字不算）=====
    # 关键：明细行 OCR 经常把数量/单价/金额/税额挤成短行，但都不带 ¥ 符号
    # 真正的金额行带 ¥ 或 ￥
    amounts = []
    for poly, text, conf in lines:
        # 跳过日期、税率、税号
        if "年" in text or "%" in text or len(text) > 30:
            continue
        # 只在带 ¥/￥ 时才抽（避免明细行污染）
        if "¥" not in text and "￥" not in text:
            continue
        for m in RE_AMOUNT.finditer(text):
            raw = m.group(1).replace(",", "")
            try:
                v = float(raw)
                if v > 0:
                    amounts.append((v, conf, poly, text))
            except ValueError:
                pass
    if amounts:
        # 价税合计 = 最大金额（出现在票面"价税合计"行）
        # 不含税金额 = 金额栏
        # 税额 = 税额栏
        total, tax, excl = None, None, None
        total_conf, tax_conf, excl_conf = 0, 0, 0

        # 第一步：找"价税合计"行（含"价税"或"小写"）
        for v, conf, poly, text in amounts:
            if "价税" in text or "小写" in text:
                total = v
                total_conf = conf
                break
        # 第二步：找"税额"行（Y 通常和金额行相同，X 靠右）
        for v, conf, poly, text in amounts:
            if "税额" in text:
                tax = v
                tax_conf = conf
                break
        # 第三步：找"金额"行（不含税）
        for v, conf, poly, text in amounts:
            if "金额" in text and "税" not in text:
                excl = v
                excl_conf = conf
                break

        # 兜底：按 ¥ 行的 X 排序（左=金额，中=税额，右=价税）
        if total is None or tax is None or excl is None:
            # 用 X 排序：左=金额（不含税），中=税额，右=价税合计
            sorted_by_x = sorted(amounts, key=lambda x: sum(p[0] for p in x[2]) / 4)
            if len(sorted_by_x) >= 3 and total is not None:
                # total 已经从"价税合计"或最大 Y 找到
                # tax = 税额（一般 X 在中右）
                # excl = 不含税金额（一般 X 在中左）
                # 按 X 中心从大到小
                sorted_by_x_desc = sorted(amounts, key=lambda x: sum(p[0] for p in x[2]) / 4, reverse=True)
                if total is not None:
                    # 价税合计已知，找税额和不含税
                    candidates = [a for a in sorted_by_x_desc if a[0] != total]
                    if tax is None and candidates:
                        tax = candidates[0][0]
                        tax_conf = candidates[0][1]
                    if excl is None and len(candidates) > 1:
                        # 不含税应该 < 税额
                        excl_cands = [c for c in candidates[1:] if c[0] < (tax or float('inf'))]
                        if excl_cands:
                            excl = excl_cands[0][0]
                            excl_conf = excl_cands[0][1]

        if total is not None:
            fields["totalAmount"] = {"value": total, "confidence": _pct(total_conf)}
        if tax is not None:
            fields["taxAmount"] = {"value": tax, "confidence": _pct(tax_conf)}
        if excl is not None:
            fields["amount"] = {"value": excl, "confidence": _pct(excl_conf)}
        elif total is not None and tax is not None:
            fields["amount"] = {"value": round(total - tax, 2), "confidence": _pct((total_conf + tax_conf) / 2)}

    # ===== 税率 =====
    for poly, text, conf in lines:
        m = RE_TAX_RATE.search(text)
        if m:
            try:
                rate = float(m.group(1)) / 100
                # 合理税率范围
                if 0 < rate <= 0.2:
                    fields["taxRate"] = {"value": rate, "confidence": _pct(conf)}
                    break
            except ValueError:
                pass

    # ===== 兜底：缺字段用 overall_conf =====
    for required in ("invoiceNo", "issueDate", "totalAmount"):
        if required not in fields:
            fields[required] = {"value": None, "confidence": int(overall_conf * 100 * 0.6)}

    return fields


def _extract_buyer_seller(lines: List[Tuple], fields: Dict[str, dict]):
    """
    抽取购方/销方名称

    增值税电子发票（新版）实际结构（**左右分栏**）：

    ┌─────────────────┬─────────────────┐
    │ 购 买 方 信 息  │ 销 售 方 信 息  │  ← 标签（竖排）
    │ 名 称：xxx     │ 名 称：yyy     │  ← 名称行
    │ 统一社会...：   │ 统一社会...：   │  ← 税号行
    └─────────────────┴─────────────────┘

    关键启发：
    1. 找所有"名称：xxx"行（以"名称："开头）
    2. 按 X 排序：X 小的 = 购方，X 大的 = 销方
    3. 公司名部分在"名称："冒号之后
    4. 排除"统一社会信用代码/纳税人识别号"行
    """
    name_candidates = []  # [(x, y, company_name, conf, raw_text)]

    for poly, text, conf in lines:
        t = text.strip()
        if not t or "名称" not in t:
            continue
        cy = sum(p[1] for p in poly) / 4
        cx = sum(p[0] for p in poly) / 4

        # 情况 1："名称：xxx"（标准格式）
        if t.startswith("名称：") or t.startswith("名称:"):
            company = t.split("：", 1)[-1].split(":", 1)[-1].strip()
            if 4 <= len(company) <= 30:
                name_candidates.append((cx, cy, company, conf, t))
        # 情况 2：纯公司名（含"公司/集团/有限/厂/分店/部"等关键词）
        elif (
            4 <= len(t) <= 30
            and any(kw in t for kw in ["公司", "集团", "有限", "厂", "分店", "部", "商店", "商行"])
            and "纳税人识别号" not in t
            and "信用代码" not in t
            and "统一社会" not in t
        ):
            name_candidates.append((cx, cy, t, conf, t))

    if not name_candidates:
        print(f"[ocr] no name candidates found", flush=True)
        return

    # 按 X 排序（X 小 = 左侧 = 购方；X 大 = 右侧 = 销方）
    name_candidates.sort(key=lambda r: (r[0], r[1]))

    if "buyerName" not in fields and name_candidates:
        cx, cy, name, conf, _ = name_candidates[0]
        fields["buyerName"] = {"value": name, "confidence": _pct(conf)}

    if "sellerName" not in fields and len(name_candidates) > 1:
        # 找 X 大于购方最多的那个（Y 可以略有差异）
        buyer_cx = name_candidates[0][0]
        seller_candidates = [c for c in name_candidates if c[0] - buyer_cx > 200]
        if seller_candidates:
            cx, cy, name, conf, _ = seller_candidates[0]
            fields["sellerName"] = {"value": name, "confidence": _pct(conf)}
        else:
            # 兜底：取最后一个
            cx, cy, name, conf, _ = name_candidates[-1]
            fields["sellerName"] = {"value": name, "confidence": _pct(conf)}




def _extract_tax_no(lines: List[Tuple], fields: Dict[str, dict]):
    """
    抽取购方/销方纳税人识别号
    关键：识别 "统一社会信用代码/纳税人识别号：" 行，按 X 位置区分购方（X 小）和销方（X 大）
    """
    # 找所有以"统一社会"开头的行（一般形如"统一社会信用代码/纳税人识别号：XXXXXXXXX"）
    tax_rows = []  # [(x, y, tax_no, conf, text)]
    for poly, text, conf in lines:
        t = text.strip()
        if not t:
            continue
        # 跳过没冒号的（避免误匹配）
        if "：" not in t and ":" not in t:
            continue
        # 找税号：18 位 A-Z0-9
        m = RE_TAX_NO.search(t)
        if not m:
            continue
        tax_no = m.group(0)
        # 排除明显不是税号的：
        # 1) 长度 15-20 之间
        # 2) 纯数字 20 位 + 不带"信用"/"纳税人"等关键字 → 是发票号
        if len(tax_no) < 15 or len(tax_no) > 20:
            continue
        # 关键：纯数字 18-20 位通常是发票号（如 26112000001122592861 = 20 位发票号）
        # 税号要么含字母（如 MA0000），要么 9111 开头 18 位
        # 简单判断：行内必须出现"税"/"信用"/"代码"等关键字才视为税号行
        if "税" not in t and "信用" not in t and "代码" not in t and "识别号" not in t:
            continue  # 这行根本不是税号描述
        cy = sum(p[1] for p in poly) / 4
        cx = sum(p[0] for p in poly) / 4
        tax_rows.append((cx, cy, tax_no, conf, t))

    if not tax_rows:
        return

    # 按 X 排序：X 小 = 购方，X 大 = 销方
    tax_rows.sort(key=lambda r: (r[0], r[1]))

    # 税号可能在同一行或不同行。优先按名称行的位置来对应（购方 X 配购方税号 X）
    # 简化：取 X 最小的 2 个，按 X 顺序分配给 buyer / seller
    if len(tax_rows) >= 2:
        # X 最小 → 购方，X 最大 → 销方
        if "buyerTaxNo" not in fields:
            cx, cy, tn, conf, _ = tax_rows[0]
            fields["buyerTaxNo"] = {"value": tn, "confidence": _pct(conf)}
        if "sellerTaxNo" not in fields:
            cx, cy, tn, conf, _ = tax_rows[-1]
            fields["sellerTaxNo"] = {"value": tn, "confidence": _pct(conf)}
    elif len(tax_rows) == 1:
        # 只有一个：默认给购方
        cx, cy, tn, conf, _ = tax_rows[0]
        if "buyerTaxNo" not in fields:
            fields["buyerTaxNo"] = {"value": tn, "confidence": _pct(conf)}





def _extract_items(lines: List[Tuple], fields: Dict[str, dict]):
    """
    抽取发票明细行（项目名称/规格型号/单位/数量/单价/金额/税率/税额）
    关键：找到"项目名称"表头行（X≈100-200），其下方的明细行是项目数据
    排除：表头行（项目名称/规格型号/单位/数量/单价/金额/税率/税额）
    排除：合计行（含"合"/"计"）+ 价税合计 + 大写小写金额
    """
    # 1. 找"项目名称"表头行作为锚点
    header_y = None
    for poly, text, conf in lines:
        t = text.strip()
        if "项目名称" in t and "规格" not in t:
            cy = sum(p[1] for p in poly) / 4
            header_y = cy
            break

    if header_y is None:
        return  # 没有表头 = 不是明细行格式

    # 2. 收集表头下方的所有行（Y > header_y，差 20px 内算同一明细行）
    item_rows: list = []  # list of [(x, y, text, conf)]
    for poly, text, conf in lines:
        cy = sum(p[1] for p in poly) / 4
        if cy <= header_y + 15:
            continue  # 表头或以上
        # 排除价税合计行（大写/小写/价税合计）和备注行
        t = text.strip()
        if not t:
            continue
        if any(kw in t for kw in [
            "价税合计", "大写", "小写", "备注", "开票人", "收款人", "复核",
            "产品", "商品", "携程订单", "订单号", "PNR", "票号", "行程单",  # 干扰行
        ]):
            continue
        if t in ("合", "计") or t == "合计":
            continue
        # 排除表头行
        if t in ("项目名称", "规格型号", "单位", "数量", "单价", "金额", "税率/征收率", "税额", "产品", "商品"):
            continue
        # 排除纯冒号 + 数字（如"携程订单: 1128147398848591"）
        if ":" in t and any(ch.isdigit() for ch in t):
            continue
        # 排除合计/价税合计行：Y 大于 400（明细区下方）+ 带 ¥ 或 "合" 关键词
        if "￥" in t or "¥" in t:
            continue  # 不抽带 ¥ 的合计行（前面的金额抽取已处理）
        if "合" in t or "价税" in t or "大写" in t or "小写" in t:
            continue
        cx = sum(p[0] for p in poly) / 4
        item_rows.append((cx, cy, t, conf))

    if not item_rows:
        return

    # 3. 按 Y 分组（Y 差 < 15 算同一行）
    item_rows.sort(key=lambda r: (r[1], r[0]))
    grouped: list = []  # list of (y, [(x, text, conf)])
    current_y = None
    current_group: list = []
    for x, y, t, c in item_rows:
        if current_y is None or abs(y - current_y) < 15:
            current_group.append((x, t, c))
            current_y = y if current_y is None else current_y
        else:
            grouped.append((current_y, current_group))
            current_group = [(x, t, c)]
            current_y = y
    if current_group:
        grouped.append((current_y, current_group))

    # 4. 解析每组为一条明细（按 X 顺序分配列）
    items = []
    for gy, row in grouped:
        row.sort(key=lambda r: r[0])
        item = {
            "name": "",      # 项目名称
            "spec": "",      # 规格型号
            "unit": "",      # 单位
            "quantity": "",  # 数量
            "price": "",     # 单价
            "amount": "",    # 金额
            "taxRate": "",   # 税率
            "taxAmount": "", # 税额
        }
        # 按 X 范围分配字段（基于国标增值税发票列位置·1400px 视口）
        for x, t, c in row:
            if x < 280:        # 项目名称列
                if not item["name"]: item["name"] = t
                else: item["name"] += " " + t  # 跨行拼接
            elif x < 440:      # 规格型号列
                if not item["spec"]: item["spec"] = t
            elif x < 540:      # 单位列
                if not item["unit"]: item["unit"] = t
            elif x < 680:      # 数量列
                if not item["quantity"]: item["quantity"] = t
            elif x < 820:      # 单价列
                if not item["price"]: item["price"] = t
            elif x < 920:      # 金额列
                if not item["amount"]: item["amount"] = t
            elif x < 1060:     # 税率列
                if not item["taxRate"]: item["taxRate"] = t
            else:              # 税额列
                if not item["taxAmount"]: item["taxAmount"] = t
        # 数字去重：金额 = 单价时合并；税率/税额为空时回退
        # 只保留至少有项目名称 或 金额的明细
        if not (item["name"] or item["amount"]):
            continue
        # 丢弃：金额是单价的子串（如 1,672.64 出现 2 次，OCR 误识别成 672.64）
        if item["price"] and item["amount"] and item["price"] in item["amount"] and item["price"] != item["amount"]:
            # 金额里有单价的子串 + 数字更短 → 金额是误识别，保留单价
            item["amount"] = item["price"]
        # 丢弃：金额 = 0 或纯占位符
        if item["amount"] in ("-", "—", "", "0", "0.00", "0.0"):
            item["amount"] = ""
        items.append(item)

    if items:
        fields["items"] = {"value": items, "confidence": _pct(sum(c for _, _, _, c in item_rows) / max(1, len(item_rows)))}

def _pct(conf: float) -> int:
    """置信度转百分制整数"""
    return int(round(conf * 100))


def date(y, m, d):
    from datetime import date as _d
    return _d(y, m, d)


# ============================================================
# 火车票识别（铁路电子客票）
# ============================================================
# 火车票版式固定，特征明显：
# - 标题：电子发票（铁路电子客票）
# - 发票号码：20+ 位数字
# - 开票日期：YYYY年MM月DD日
# - 出发站 + 到达站 + 车次
# - 乘车日期 + 时间
# - 车厢号 + 座位号
# - 票价：¥XX.XX
# - 姓名 + 身份证号（18 位）
# - 电子客票号（30+ 位数字）
# - 购买方名称 + 税号

import re

RE_TRAIN_FROM = re.compile(r"^([\u4e00-\u9fa5]{2,4})站\s*$")  # 上海站、北京南站
RE_TRAIN_TRAIN_NO = re.compile(r"^([GDCZTKLPS]\d{1,4})次?$|^([GDCZTKLPS]\d{1,4})$")  # G4/D12/K1057
RE_TRAIN_DATE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
RE_TRAIN_TIME = re.compile(r"(\d{1,2}):(\d{1,2})开$|^(\d{1,2}):(\d{1,2})$")
RE_TRAIN_CAR = re.compile(r"(\d{1,2})车(\d{1,3}[A-Z]?号)")  # 12车02C号
RE_TRAIN_PRICE = re.compile(r"[¥￥]\s*([0-9]+(?:\.[0-9]{1,2})?)")  # 半角/全角 ¥ 都收
RE_TRAIN_ID = re.compile(r"(?<!\d)(\d{17}[\dXx])(?!\d)")  # 18 位身份证（避免误匹 20 位发票号）
RE_TRAIN_ID_MASKED = re.compile(r"(\d{6,10})\*+(\d{4})")  # 3715811989****1751
RE_TRAIN_E_TICKET = re.compile(r"电子客票号[:：]\s*(\d{18,})" )  # 电子客票号（18+ 位）
RE_TRAIN_BUYER = re.compile(r"购买方名称[:：]\s*([^\n]+)")  # 火车票购买方（不跨行）
RE_TRAIN_TAX = re.compile(r"统一社会信用代码[:：]\s*([0-9A-Z]{15,20})")
RE_TRAIN_INVOICE_NO = re.compile(r"发票号码[:：]\s*(\d{15,25})")  # 火车票发票号 20 位左右


def _extract_train_ticket_fields(items: List[Tuple]) -> Dict[str, dict]:
    """提取铁路电子客票字段"""
    if not items:
        return {}

    merged = _merge_lines(items, y_threshold=25)
    lines = [(it[0], it[1].strip(), it[2]) for it in merged if it[1].strip()]
    overall_conf = sum(c for _, _, c in items) / max(1, len(items))

    fields: Dict[str, dict] = {}
    full_text = "\n".join(t for _, t, _ in lines)

    # ===== 发票号（标题"发票号码："后）=====
    m = RE_TRAIN_INVOICE_NO.search(full_text)
    if m:
        fields["invoiceNo"] = {"value": m.group(1), "confidence": _pct(overall_conf)}

    # ===== 开票日期 =====
    m = RE_TRAIN_DATE.search(full_text)
    if m:
        y, mo, d = m.groups()
        try:
            fields["issueDate"] = {"value": date(int(y), int(mo), int(d)).isoformat(), "confidence": _pct(overall_conf)}
        except ValueError:
            pass

    # ===== 票价（"¥" 开头的金额） =====
    m = RE_TRAIN_PRICE.search(full_text)
    if m:
        fields["totalAmount"] = {"value": float(m.group(1)), "confidence": _pct(overall_conf)}
        fields["taxAmount"] = {"value": 0.0, "confidence": 100}  # 火车票免税
        fields["amount"] = {"value": float(m.group(1)), "confidence": _pct(overall_conf)}
        fields["taxRate"] = {"value": 0.0, "confidence": 100}
        # 大写
        fields["totalAmountCn"] = {"value": _cn_capital(Decimal(str(m.group(1)))), "confidence": _pct(overall_conf)}

    # ===== 乘车人身份证（18 位或掩码） =====
    m = RE_TRAIN_ID.search(full_text)
    if m:
        fields["buyerIdNumber"] = {"value": m.group(1), "confidence": _pct(overall_conf)}
    m = RE_TRAIN_ID_MASKED.search(full_text)
    if m:
        fields["buyerIdMasked"] = {"value": f"{m.group(1)}****{m.group(2)}", "confidence": _pct(overall_conf)}

    # ===== 购买方（抬头） =====
    m = RE_TRAIN_BUYER.search(full_text)
    if m:
        fields["buyerName"] = {"value": m.group(1).strip(), "confidence": _pct(overall_conf)}

    m = RE_TRAIN_TAX.search(full_text)
    if m:
        fields["buyerTaxNo"] = {"value": m.group(1), "confidence": _pct(overall_conf)}

    # ===== 电子客票号 =====
    m = RE_TRAIN_E_TICKET.search(full_text)
    if m:
        fields["eTicketNo"] = {"value": m.group(1), "confidence": _pct(overall_conf)}

    # ===== 车次 / 出发 / 到达 / 乘车日期 / 车厢座位 =====
    # 提取所有 station 标记（"X站"格式）
    stations = []
    for _, t, c in lines:
        m = re.match(r"^([\u4e00-\u9fa5]{2,4})站$", t)
        if m:
            stations.append(m.group(1))
    if len(stations) >= 2:
        fields["fromStation"] = {"value": stations[0], "confidence": _pct(overall_conf)}
        fields["toStation"] = {"value": stations[1], "confidence": _pct(overall_conf)}

    # 车次
    for _, t, c in lines:
        m = re.match(r"^([GDCZTKLY]\d{1,4})$", t)
        if m:
            fields["trainNo"] = {"value": m.group(1), "confidence": _pct(c)}
            break

    # 乘车日期时间（"2026年04月10日" + "07:00开" 配对）
    ride_date = None
    ride_time = None
    for _, t, c in lines:
        m = RE_TRAIN_DATE.match(t)
        if m and not fields.get("issueDate", {}).get("value", "").endswith(f"-{int(m.group(2)):02d}-{int(m.group(3)):02d}"):
            # 可能是乘车日期（不是开票日期）
            try:
                ride_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
            except ValueError:
                pass
        m = re.match(r"^(\d{1,2}):(\d{1,2})开?$", t)
        if m:
            ride_time = f"{int(m.group(1)):02d}:{m.group(2)}"
    if ride_date:
        fields["rideDate"] = {"value": ride_date, "confidence": _pct(overall_conf)}
    if ride_time:
        fields["rideTime"] = {"value": ride_time, "confidence": _pct(overall_conf)}

    # 车厢 + 座位
    for _, t, c in lines:
        m = RE_TRAIN_CAR.match(t)
        if m:
            fields["carriageNo"] = {"value": f"{m.group(1)}车", "confidence": _pct(c)}
            fields["seatNo"] = {"value": m.group(2), "confidence": _pct(c)}
            break
    for _, t, c in lines:
        if t in ("二等座", "一等座", "商务座", "特等座", "硬座", "软座", "硬卧", "软卧", "动卧"):
            fields["seatClass"] = {"value": t, "confidence": _pct(c)}
            break

    # ===== 标识 =====
    fields["invoiceType"] = {"value": "铁路电子客票", "confidence": _pct(overall_conf)}
    fields["sellerName"] = {"value": "中国铁路", "confidence": _pct(overall_conf)}
    fields["sellerTaxNo"] = {"value": "", "confidence": 0}
    fields["invoiceCode"] = {"value": "", "confidence": 0}
    fields["remarks"] = {"value": "火车票（差旅）", "confidence": _pct(overall_conf)}

    print(f"[ocr] train ticket: fields={list(fields.keys())}", flush=True)
    return fields


def _cn_capital(amount):
    """数字转中文大写金额（复用主代码逻辑，避免重复 import）"""
    try:
        from postprocess_cn import cn_capital
        return cn_capital(amount)
    except ImportError:
        # 兜底：直接调用本地小函数
        return _cn_capital_local(amount)


def _cn_capital_local(amount):
    """简易中文大写转换（兜底）"""
    if amount is None:
        return ""
    try:
        amt = float(amount)
    except (TypeError, ValueError):
        return ""
    if amt == 0:
        return "零元整"
    # 简化版：数字 + "元"
    return f"{amt:.2f}元"



# ============================================================
# 航空电子客票行程单识别（R29 修复：之前没分支，被通用增值税发票逻辑误判为"中国铁路"）
# ============================================================
# 航空电子客票行程单版式（按国标 + 实际航司版式）：
# - 标题：电子发票（航空运输电子客票行程单）
# - 发票号码：通常 8-10 位
# - 开票日期：YYYY年MM月DD日
# - 票价 / 民航发展基金 / 燃油附加费（3 个子项）
# - 价税合计（大写）
# - 价税合计（小写）：¥XXX.XX ← totalAmount
# - 乘机人 + 有效身份证件号码
# - 购方名称 + 统一社会信用代码
# - 销方名称（航空公司）+ 销方纳税人识别号
# - 航班号（如 CA1234）
# - 出发机场 → 到达机场
# - 起飞时间 / 到达时间
# - 舱位

RE_FLIGHT_NO = re.compile(r"^([A-Z]{2,3}\d{2,4})$")  # CA1234 / MU5678
RE_FLIGHT_AIRPORT = re.compile(r"^([\u4e00-\u9fa5]{2,4})$")  # 北京首都、上海浦东
RE_FLIGHT_TIME = re.compile(r"^(\d{1,2}):(\d{1,2})$")
RE_FLIGHT_INVOICE_NO = re.compile(r"发票号码[::：]\s*(\d{8,25})")  # 8-25 位（航空电子客票行程单发票号 20 位）
RE_FLIGHT_DATE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
RE_FLIGHT_PRICE = re.compile(r"(?:[¥￥¥]|CNY)\s*([0-9]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)
RE_FLIGHT_BUYER = re.compile(r"(?:购买方名称|购方名称|名称)[::：][ \t]*([^\n]+)")
RE_FLIGHT_SELLER = re.compile(r"(?:销售方名称|销方名称|航空公司|承运人|填开单位)[::：]?[ \t]*([^\n]+)")
RE_FLIGHT_TAX = re.compile(r"统一社会信用代码[::\uff1a]\s*([0-9A-Z]{15,20})")
RE_FLIGHT_BUYER_TAX = re.compile(r"购买方(?:名称|公司)?(?:纳税人识别号|统一社会信用代码)?[::：]?\s*([0-9A-Z]{15,20})")
RE_FLIGHT_SELLER_TAX = re.compile(r"(?:销售方纳税人识别号|销方纳税人识别号|销方税号|统一社会信用代码[/／、]纳税人识别号)[::：]?\s*([0-9A-Z]{15,20})")
RE_FLIGHT_ID = re.compile(r"(?<!\d)(\d{17}[\dXx])(?!\d)")
RE_FLIGHT_ID_MASKED = re.compile(r"(\d{6,10})\*+(\d{4})")
RE_FLIGHT_CABIN = re.compile(r"^舱位[::：]?\s*([\u4e00-\u9fa5A-Z0-9]{1,8})$|^(?:头等舱|公务舱|经济舱|超级经济舱|高端经济舱|明珠经济舱|[WFBYJCDFHKLSUTV])$")  # W=超级经济 F=头等 J=公务等
RE_FLIGHT_FROM = re.compile(r"^[自起][::：]?[ \t]*([^\n]+)$")  # \\s 不跨行：避免吞掉下一行
RE_FLIGHT_TO = re.compile(r"^[至][::：]?[ \t]*([^\n]+)$")
RE_FLIGHT_E_TICKET = re.compile(r"\u7535\u5b50\u5ba2\u7968\u53f7\u7801[::：]?\s*(\d{10,30})")  # "电子客票号码：0182353153523"
RE_FLIGHT_DEPART_DATE = re.compile(r"^[\u65e5\u671f][::：]?\s*(\d{4})\s*\u5e74\s*(\d{1,2})\s*\u6708\s*(\d{1,2})\s*\u65e5$")  # "日期：2026年04月24日" → 出发日期
RE_FLIGHT_FILL_DATE = re.compile(r"\u586b\u5f00\u65e5\u671f[::：]?\s*(\d{4})\s*\u5e74\s*(\d{1,2})\s*\u6708\s*(\d{1,2})\s*\u65e5")  # "填开日期：2026年05月18日" → 开票日期



def _extract_flight_ticket_fields(items) -> dict:
    """
    提取航空电子客票行程单字段
    注意：PaddleOCR 经常把"航空"识别成"铁路"或"航室"等，所以这里走多策略匹配
    """
    if not items:
        return {}

    merged = _merge_lines(items, y_threshold=25)
    lines = [(it[0], it[1].strip(), it[2]) for it in merged if it[1].strip()]
    overall_conf = sum(c for _, _, c in items) / max(1, len(items))
    full_text = "\n".join(t for _, t, _ in lines)
    fields: Dict[str, dict] = {}

    # ===== 发票号码 =====
    m = RE_FLIGHT_INVOICE_NO.search(full_text)
    if m:
        fields["invoiceNo"] = {"value": m.group(1), "confidence": _pct(overall_conf)}
    # 兜底：找一行纯 8-12 位数字
    if "invoiceNo" not in fields:
        cands = []
        for _, t, c in lines:
            s = t.strip()
            if 8 <= len(s) <= 12 and s.isdigit():
                cands.append((s, c))
        if cands:
            # 取 confidence 最高的
            cands.sort(key=lambda x: x[1], reverse=True)
            fields["invoiceNo"] = {"value": cands[0][0], "confidence": _pct(cands[0][1])}

    # ===== 开票日期 =====
    # 优先级：填开日期（航空票明确"填开日期"）> 其他日期
    m = RE_FLIGHT_FILL_DATE.search(full_text)
    if m:
        y, mo, d = m.groups()
        try:
            fields["issueDate"] = {"value": date(int(y), int(mo), int(d)).isoformat(), "confidence": _pct(overall_conf)}
        except ValueError:
            pass
    if "issueDate" not in fields:
        m = RE_FLIGHT_DATE.search(full_text)
        if m:
            y, mo, d = m.groups()
            try:
                fields["issueDate"] = {"value": date(int(y), int(mo), int(d)).isoformat(), "confidence": _pct(overall_conf)}
            except ValueError:
                pass

    # ===== 出发日期（"日期：2026年04月24日"）=====
    # OCR 后"日期"和"2026年04月24日"可能没合并（y 差 ~55 像素），需要分两步：
    #  1. 找"日期"行 y
    #  2. 在 y 附近 ±60 像素找纯日期行
    date_y = None
    for poly, t, c in lines:
        if t.strip() == "日期" or "日期：" in t or t.strip().startswith("日期"):
            y = sum(p[1] for p in poly) / 4
            date_y = y
            break
    if date_y is not None:
        for poly, t, c in lines:
            # 匹配纯日期行（"YYYY年MM月DD日" 格式）
            m = re.match(r"^(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*$", t)
            if m:
                yy = sum(p[1] for p in poly) / 4
                if abs(yy - date_y) < 100:  # y 接近
                    try:
                        fields["rideDate"] = {"value": date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat(), "confidence": _pct(c)}
                        break
                    except ValueError:
                        pass

    # ===== 电子客票号 =====
    m = RE_FLIGHT_E_TICKET.search(full_text)
    if m:
        fields["eTicketNo"] = {"value": m.group(1), "confidence": _pct(overall_conf)}

    # ===== 价税合计（totalAmount） =====
    # 优先级：找"价税合计（小写）"附近的金额；兜底：找最大的人民币金额
    amounts = []
    for _, t, c in lines:
        m = RE_FLIGHT_PRICE.search(t)
        if m:
            try:
                amounts.append((float(m.group(1)), c, t))
            except ValueError:
                pass
    if amounts:
        # 找"价税合计"附近
        total_idx = None
        for i, (_, t, _) in enumerate(lines):
            if "价税合计" in t or "合计" in t:
                total_idx = i
                break
        if total_idx is not None:
            # 智能定位"合计"对应的金额
            # 关键观察：
            #  - 增值税发票："合计"与金额在同一 y 行（合并后同行）
            #  - 航空电子客票行程单："合计"在 y=484.5，金额在 y=506-508（差 ~22 像素），合并阈值 25 没合上
            #  - 航空票"保险费：0.00" x 接近"合计"x（都会在最右列），不能误选
            #  - 航空票"合计"是子项之和（票价+民航基金+燃油+其他），是子项里最大的
            # 策略：
            #  1. 排除"保险费"行
            #  2. 按"金额大小"选最大（避免选到 0 噪声）
            candidates = []
            for poly, t, c in lines:
                if "保险费" in t:
                    continue
                m = RE_FLIGHT_PRICE.search(t)
                if m:
                    try:
                        amt = float(m.group(1))
                        if amt > 0:  # 排除 0
                            candidates.append(amt)
                    except ValueError:
                        pass
            if candidates:
                best = max(candidates)
            else:
                best = 0.0
                fields["totalAmount"] = {"value": best, "confidence": _pct(overall_conf)}
                fields["taxAmount"] = {"value": 0.0, "confidence": 100}  # 航空票一般含税无单独税额
                fields["amount"] = {"value": best, "confidence": _pct(overall_conf)}
                fields["taxRate"] = {"value": 0.0, "confidence": 100}
                fields["totalAmountCn"] = {"value": _cn_capital(Decimal(str(best))), "confidence": _pct(overall_conf)}
        # 兜底：取最大金额
        if "totalAmount" not in fields:
            best = max(amounts, key=lambda x: x[0])[0]
            fields["totalAmount"] = {"value": best, "confidence": _pct(overall_conf)}
            fields["taxAmount"] = {"value": 0.0, "confidence": 100}
            fields["amount"] = {"value": best, "confidence": _pct(overall_conf)}
            fields["taxRate"] = {"value": 0.0, "confidence": 100}
            fields["totalAmountCn"] = {"value": _cn_capital(Decimal(str(best))), "confidence": _pct(overall_conf)}

    # ===== 乘机人身份证 =====
    m = RE_FLIGHT_ID.search(full_text)
    if m:
        fields["buyerIdNumber"] = {"value": m.group(1), "confidence": _pct(overall_conf)}
    m = RE_FLIGHT_ID_MASKED.search(full_text)
    if m:
        fields["buyerIdMasked"] = {"value": f"{m.group(1)}****{m.group(2)}", "confidence": _pct(overall_conf)}

    # ===== 购买方（抬头） =====
    m = RE_FLIGHT_BUYER.search(full_text)
    if m:
        # 去掉行尾的"统一社会信用代码"等附加内容
        name = m.group(1).strip()
        for noise in ("统一社会信用代码", "纳税人识别号", "纳税人", "识别号"):
            if noise in name:
                name = name.split(noise)[0].strip()
        if name:
            fields["buyerName"] = {"value": name, "confidence": _pct(overall_conf)}

    m = RE_FLIGHT_BUYER_TAX.search(full_text)
    if m:
        fields["buyerTaxNo"] = {"value": m.group(1), "confidence": _pct(overall_conf)}

    # ===== 销售方 =====
    m = RE_FLIGHT_SELLER.search(full_text)
    if m:
        name = m.group(1).strip()
        for noise in ("纳税人识别号", "统一社会信用代码", "纳税人", "识别号"):
            if noise in name:
                name = name.split(noise)[0].strip()
        # 排除明显是购方错位 / 中国铁路这种
        if name and name not in ("中国铁路", "中国国家铁路集团", "12306"):
            fields["sellerName"] = {"value": name, "confidence": _pct(overall_conf)}

    m = RE_FLIGHT_SELLER_TAX.search(full_text)
    if m:
        fields["sellerTaxNo"] = {"value": m.group(1), "confidence": _pct(overall_conf)}

    # ===== 航班号 =====
    for _, t, c in lines:
        m = RE_FLIGHT_NO.match(t)
        if m:
            fields["flightNo"] = {"value": m.group(1), "confidence": _pct(c)}
            break

    # ===== 出发机场 / 到达机场 =====
    # 优先级 1：找 "自：上海浦东" / "至：北京大兴" 这种带前导词的行
    from_city = None
    to_city = None
    for _, t, c in lines:
        m = RE_FLIGHT_FROM.match(t)
        if m and not from_city:
            v = m.group(1).strip()
            # 去掉后缀"机场"
            for suf in ("机场",):
                if v.endswith(suf):
                    v = v[:-len(suf)]
            if v:
                from_city = (v, c)
        m = RE_FLIGHT_TO.match(t)
        if m and not to_city:
            v = m.group(1).strip()
            for suf in ("机场",):
                if v.endswith(suf):
                    v = v[:-len(suf)]
            if v:
                to_city = (v, c)
    if from_city:
        fields["fromCity"] = {"value": from_city[0], "confidence": _pct(from_city[1])}
    if to_city:
        fields["toCity"] = {"value": to_city[0], "confidence": _pct(to_city[1])}

    # ===== 起飞时间 / 到达时间 =====
    times = []
    for _, t, c in lines:
        m = RE_FLIGHT_TIME.match(t)
        if m:
            times.append((f"{int(m.group(1)):02d}:{m.group(2)}", c))
    if len(times) >= 2:
        fields["departTime"] = {"value": times[0][0], "confidence": _pct(times[0][1])}
        fields["arriveTime"] = {"value": times[1][0], "confidence": _pct(times[1][1])}
    elif len(times) == 1:
        fields["departTime"] = {"value": times[0][0], "confidence": _pct(times[0][1])}

    # ===== 舱位 =====
    for _, t, c in lines:
        m = RE_FLIGHT_CABIN.match(t)
        if m:
            fields["cabin"] = {"value": m.group(1) if m.group(1) else t, "confidence": _pct(c)}
            break

    # ===== 标识（兜底） =====
    fields["invoiceType"] = {"value": "\u822a\u7a7a\u8fd0\u8f93\u7535\u5b50\u5ba2\u7968\u884c\u7a0b\u5355", "confidence": _pct(overall_conf)}
    if "invoiceCode" not in fields:
        fields["invoiceCode"] = {"value": "", "confidence": 0}
    if "remarks" not in fields:
        fields["remarks"] = {"value": "\u673a\u7968\uff08\u5dee\u65c5\uff09", "confidence": _pct(overall_conf)}

    print(f"[ocr] flight ticket: fields={list(fields.keys())}", flush=True)
    return fields
