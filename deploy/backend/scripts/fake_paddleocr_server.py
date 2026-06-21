"""
本地测试用 PaddleOCR mock 服务（端口 8001）
按 BACKEND.md §7.2 协议：
  POST /recognize  → {file_url, fields}  →  {fields: {...}, confidence: 0-1, ...}
  GET  /health     → {status: ok}
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
import string
import hashlib
import uvicorn
from datetime import date, timedelta

app = FastAPI(title="PaddleOCR Mock Service", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class RecognizeReq(BaseModel):
    file_url: str = ""
    file_id: str = ""
    fields: list[str] = []
    language: str = "zh-CN"
    options: dict = {}


def _seed(s: str) -> int:
    return int(hashlib.md5((s or "x").encode()).hexdigest(), 16)


_CN_DIGITS = "零壹贰叁肆伍陆柒捌玖"
_CN_UNITS = ["", "拾", "佰", "仟"]
_CN_BIG_UNITS = ["", "万", "亿", "万亿"]


def _cn_capital(amount) -> str:
    """数字金额转中文大写（支持小数：角分）"""
    try:
        amt = round(float(amount), 2)
    except Exception:
        return ""
    if amt == 0:
        return "零元整"
    yuan = int(amt)
    jiao = int(round((amt - yuan) * 10))
    fen = int(round((amt - yuan) * 100 - jiao * 10))
    if yuan == 0 and (jiao or fen):
        s = "零"
    else:
        s = ""
        y = str(yuan)
        n = len(y)
        for i, ch in enumerate(y):
            d = int(ch)
            if d == 0:
                if s and not s.endswith("零") and (n - i - 1) % 4 != 0:
                    s += "零"
            else:
                s += _CN_DIGITS[d] + _CN_UNITS[n - i - 1]
            if (n - i - 1) % 4 == 0 and (n - i - 1) > 0:
                s += _CN_BIG_UNITS[(n - i - 1) // 4]
        s = s.rstrip("零").rstrip("万").rstrip("亿")
        s += "元"
    if jiao == 0 and fen == 0:
        s += "整"
    else:
        if jiao == 0:
            s += "零"
        else:
            s += _CN_DIGITS[jiao] + "角"
        if fen:
            s += _CN_DIGITS[fen] + "分"
    return s


SAMPLE_BUYERS = [
    "万象科技有限公司", "北辰实业集团", "朗驰智能设备有限公司",
    "用友网络科技股份有限公司", "京东企业购",
]
SAMPLE_SELLERS = [
    "上海数智信息技术有限公司", "用友网络科技股份有限公司",
    "阿里云计算有限公司", "携程计算机技术（上海）有限公司",
    "滴滴出行科技有限公司",
]


@app.get("/health")
async def health():
    return {"status": "ok", "service": "paddleocr-mock", "version": "v3"}


@app.post("/recognize")
async def recognize(req: RecognizeReq):
    """按 BACKEND.md §7.2 协议返字段抽取结果（**真**协议，对接业务侧）"""
    seed = _seed(req.file_id or req.file_url)
    rng = random.Random(seed)
    # 70% 高置信 / 25% 中等 / 5% 失败
    fail = rng.randint(0, 19) == 0
    if fail:
        return {
            "code": 5001, "message": "票面识别失败（mock）",
            "fileId": req.file_id, "fileUrl": req.file_url,
        }
    overall_conf = round(rng.uniform(0.78, 0.99), 3)
    if overall_conf < 0.85:
        overall_conf = round(rng.uniform(0.78, 0.88), 3)

    fields = {
        "invoiceNo": {"value": "".join(random.choices(string.digits, k=18)),
                      "confidence": rng.randint(92, 99)},
        "invoiceCode": {"value": "".join(random.choices(string.digits, k=12)),
                        "confidence": rng.randint(92, 99)},
        "issueDate": {"value": (date.today() - timedelta(days=rng.randint(0, 30))).isoformat(),
                      "confidence": rng.randint(95, 99)},
        "buyerName": {"value": SAMPLE_BUYERS[seed % len(SAMPLE_BUYERS)],
                      "confidence": rng.randint(85, 99)},
        "buyerTaxNo": {"value": "91310000MA1FL01X9G", "confidence": rng.randint(85, 99)},
        "sellerName": {"value": SAMPLE_SELLERS[seed % len(SAMPLE_SELLERS)],
                       "confidence": rng.randint(90, 99)},
        "totalAmount": {"value": round(rng.uniform(500, 50000), 2),
                        "confidence": rng.randint(94, 99)},
        "taxAmount": {"value": round(rng.uniform(30, 3000), 2),
                       "confidence": rng.randint(90, 99)},
        "amount": {"value": round(rng.uniform(500, 50000), 2),
                   "confidence": rng.randint(92, 99)},
        "taxRate": {"value": rng.choice([0.06, 0.13, 0.03, 0.09]),
                    "confidence": rng.randint(60, 99)},
        "verifyCode": {"value": "".join(random.choices(string.digits, k=20)),
                       "confidence": rng.randint(80, 99)},
        "remarks": {"value": "", "confidence": 0},
    }
    total_yuan = fields["totalAmount"]["value"]
    cn_capital = _cn_capital(total_yuan)
    fields["totalAmountCn"] = {"value": cn_capital, "confidence": 99}
    return {
        "code": 0,
        "message": "success",
        "fileId": req.file_id,
        "fileUrl": req.file_url,
        "fields": fields,
        "items": [
            {
                "name": "*信息技术服务*系统集成服务费",
                "quantity": 1, "unitPrice": round(rng.uniform(500, 20000), 2),
                "amount": round(rng.uniform(500, 20000), 2),
                "taxRate": 0.06,
                "taxAmount": round(rng.uniform(30, 1200), 2),
                "confidence": rng.randint(80, 95),
            }
        ],
        "confidence": overall_conf,
        "model": "paddleocr-v3",
        "version": "1.2.0",
        "elapsedMs": rng.randint(800, 2400),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")
