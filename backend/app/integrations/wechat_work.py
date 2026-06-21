"""
企业微信 SSO 客户端（架构预留：mock 模式 + 真接入协议）
- 真实部署：调企业微信开放平台 https://login.work.weixin.qq.com
  鉴权：corpid + corpsecret + access_token（缓存 7200s）
  OAuth 流程：
    1. 生成 state + redirect_uri → https://open.work.weixin.qq.com/wwopen/sso/qrConnect
       ?appid=corp_id&agentid=agent_id&redirect_uri=...&state=...
    2. 用户扫码 → 跳 redirect_uri?code=...&state=...
    3. 后端用 code 换 userid（/cgi-bin/auth/getuserinfo?access_token=...&code=...）
    4. 用 userid 查 user detail（/cgi-bin/user/getuserdetail?access_token=...&user_ticket=...）
       注：仅企业自建应用可获取详情

- mock：deterministic 假用户（按 state 后 4 位生成）
- 自动回退：WECHAT_WORK_MODE=mock 或 corp_id 没配时用 mock

R6.4 架构预留：
- 完整真实客户端代码已就位
- 等企业资质申请下来后，配置 4 个环境变量即可切真模式：
    WECHAT_WORK_CORP_ID=ww0123456789abcdef
    WECHAT_WORK_CORP_SECRET=xxxxxxxx
    WECHAT_WORK_AGENT_ID=1000002
    WECHAT_WORK_REDIRECT_URI=https://yourdomain.com/api/v1/auth/sso/wechat-work/callback
"""
import asyncio
import json
import logging
import secrets
import time
from typing import Optional
from urllib.parse import urlencode, quote

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# Access Token 缓存（避免每次 OAuth 都重新获取）
# ============================================================

_token_cache: dict = {
    "token": None,
    "expires_at": 0,  # epoch 秒
}
_token_lock = asyncio.Lock()


async def _get_access_token() -> Optional[str]:
    """
    获取企业微信 access_token（缓存 7200s，提前 5 分钟续期）
    返回 None = 未配置 corp_id，走 mock
    """
    if not settings.WECHAT_WORK_CORP_ID or not settings.WECHAT_WORK_CORP_SECRET:
        return None

    # 缓存命中
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 300:
        return _token_cache["token"]

    # 抢锁（避免并发获取）
    async with _token_lock:
        # double-check
        if _token_cache["token"] and _token_cache["expires_at"] > now + 300:
            return _token_cache["token"]

        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            "corpid": settings.WECHAT_WORK_CORP_ID,
            "corpsecret": settings.WECHAT_WORK_CORP_SECRET,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url, params=params)
                data = r.json()
            if data.get("errcode") != 0:
                logger.error(f"[wechat-work] get token 失败: {data}")
                return None
            _token_cache["token"] = data["access_token"]
            _token_cache["expires_at"] = now + data.get("expires_in", 7200)
            logger.info(f"[wechat-work] access_token 已缓存，过期 {data.get('expires_in')}s")
            return _token_cache["token"]
        except Exception as e:
            logger.error(f"[wechat-work] get token 异常: {e}")
            return None


# ============================================================
# 扫码登录 URL 生成
# ============================================================

def generate_qrcode_url(state: str) -> str:
    """
    生成企业微信扫码登录 URL
    用户用企业微信 App 扫描后会跳转到 redirect_uri 并带 code 参数
    """
    if not settings.WECHAT_WORK_CORP_ID or not settings.WECHAT_WORK_AGENT_ID:
        return ""  # 走 mock

    params = {
        "appid": settings.WECHAT_WORK_CORP_ID,
        "agentid": settings.WECHAT_WORK_AGENT_ID,
        "redirect_uri": settings.WECHAT_WORK_REDIRECT_URI or "",
        "state": state,
    }
    return "https://open.work.weixin.qq.com/wwopen/sso/qrConnect?" + urlencode(params)


# ============================================================
# 用 code 换取 userid + user detail
# ============================================================

async def exchange_code_for_user(code: str) -> Optional[dict]:
    """
    用 OAuth code 换取用户信息
    返回 {userid, name, avatar, mobile, email, ...} 或 None
    """
    access_token = await _get_access_token()
    if not access_token:
        return None

    # 1. code → userid
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo",
                params={"access_token": access_token, "code": code},
            )
            data = r.json()
        if data.get("errcode") != 0:
            logger.warning(f"[wechat-work] getuserinfo 失败: {data}")
            return None
        userid = data.get("userid")
        user_ticket = data.get("user_ticket")
        if not userid:
            logger.warning(f"[wechat-work] 未拿到 userid: {data}")
            return None

        result = {"userid": userid, "raw": data}

        # 2. 拿详情（如果有 user_ticket）
        if user_ticket:
            async with httpx.AsyncClient(timeout=10) as client:
                r2 = await client.post(
                    "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserdetail",
                    params={"access_token": access_token},
                    json={"user_ticket": user_ticket},
                )
                detail = r2.json()
            if detail.get("errcode") == 0:
                user = detail.get("user", {})
                result.update({
                    "name": user.get("name"),
                    "avatar": user.get("avatar"),
                    "mobile": user.get("mobile"),
                    "email": user.get("email"),
                })
        return result
    except Exception as e:
        logger.error(f"[wechat-work] exchange code 异常: {e}")
        return None


# ============================================================
# Mock 模式（用于本地开发 + 等企业资质）
# ============================================================

async def mock_get_user_by_state(state: str) -> dict:
    """
    Mock：根据 state 生成假用户（让前端扫码能跑通流程）
    state 后 4 位 mod 5 决定用户角色
    """
    await asyncio.sleep(0.5)  # 模拟网络延迟
    try:
        bucket = int(state[-4:], 16) % 5
    except (ValueError, IndexError):
        bucket = 0

    mock_users = [
        {"userid": "mock_admin",    "name": "管理员（mock）",  "mobile": "13800000001", "email": "admin@mock.local",    "role": "admin"},
        {"userid": "mock_finance",  "name": "财务总监（mock）", "mobile": "13800000002", "email": "finance@mock.local",  "role": "finance"},
        {"userid": "mock_sales",    "name": "销售（mock）",     "mobile": "13800000003", "email": "sales@mock.local",    "role": "sales"},
        {"userid": "mock_pm",       "name": "项目经理（mock）", "mobile": "13800000004", "email": "pm@mock.local",       "role": "pm"},
        {"userid": "mock_viewer",   "name": "只读用户（mock）", "mobile": "13800000005", "email": "viewer@mock.local",   "role": "viewer"},
    ]

    user = mock_users[bucket]
    return {
        "userid": user["userid"],
        "name": user["name"],
        "mobile": user["mobile"],
        "email": user["email"],
        "avatar": "",  # mock 无头像
        "raw": {"mock": True, "bucket": bucket, "role": user["role"]},
    }


# ============================================================
# 健康检查
# ============================================================

async def health_check() -> dict:
    """探测企业微信服务状态"""
    if not settings.WECHAT_WORK_CORP_ID or not settings.WECHAT_WORK_CORP_SECRET:
        return {"status": "mock", "mode": "mock", "reason": "未配置 corp_id/secret"}

    token = await _get_access_token()
    if not token:
        return {"status": "down", "mode": "real", "reason": "access_token 获取失败"}

    return {
        "status": "ready",
        "mode": "real",
        "corpId": settings.WECHAT_WORK_CORP_ID[:8] + "***",  # 部分脱敏
        "agentId": settings.WECHAT_WORK_AGENT_ID,
    }
