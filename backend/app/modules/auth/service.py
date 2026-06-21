"""
认证服务层
R6.4 新增：
- check_sso_qrcode_status：从 Redis 查扫码状态
- handle_wechat_work_callback：企业微信 OAuth 回调
"""
import base64
import io
import json
import secrets
import time
import uuid
from datetime import datetime

import qrcode
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token, create_refresh_token,
    hash_password, verify_password
)
from app.core.exceptions import (
    UnauthorizedException, ParamErrorException
)
from app.core.cache import get_redis
from app.modules.auth.models import User, Role
from app.modules.auth.schemas import LoginResponse, UserInfo


# ===== 账号密码登录 =====

async def login_with_password(
    db: AsyncSession,
    account: str,
    password: str,
    remember_me: bool = False,
) -> LoginResponse:
    """
    账号密码登录
    account: 手机号/邮箱/工号（任一）
    """
    # 查询用户（预加载 roles / department，避免响应阶段触发 lazy IO）
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(User)
        .where(
            or_(User.username == account, User.email == account, User.phone == account),
            User.is_active == True
        )
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.department),
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        # R7.2: 登录失败埋点
        from app.core.metrics import business_login_total
        business_login_total.labels(method="password", result="failed").inc()
        raise UnauthorizedException("账号或密码错误")

    # 更新登录信息
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # R7.2: 登录成功埋点
    from app.core.metrics import business_login_total
    business_login_total.labels(method="password", result="success").inc()

    return _build_login_response(db, user, remember_me)


def _build_login_response(db: AsyncSession, user, remember_me: bool = False) -> LoginResponse:
    """R6.4: 抽出 token 签发 + UserInfo 构造，SSO 复用"""
    # 重新预加载（避免懒加载报错）
    from sqlalchemy.orm import selectinload
    # 注：传入的 user 应该是预加载过的
    expires_in = 60 * 24 * 7 if remember_me else 60 * 2 * 60
    token_data = {"sub": str(user.id), "username": user.username}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    roles = [r.name for r in user.roles]
    perm_codes: list[str] = []
    seen: set[str] = set()
    for r in user.roles:
        for p in (r.permissions or []):
            if p.code and p.code not in seen:
                seen.add(p.code)
                perm_codes.append(p.code)
    user_info = UserInfo(
        userId=user.id,
        name=user.name,
        avatar=user.avatar,
        role=" / ".join(roles) if roles else "用户",
        department=user.department.name if user.department else None,
        isAdmin=user.is_admin,
        permissions=perm_codes,
    )

    return LoginResponse(
        token=access_token,
        refreshToken=refresh_token,
        expiresIn=expires_in,
        userInfo=user_info,
    )


# ===== SSO 二维码 =====

async def generate_sso_qrcode(provider: str) -> dict:
    """生成 SSO 登录二维码
    R6.4: 存 state 到 Redis + provider-specific URL
    """
    qr_token = f"qr_{uuid.uuid4().hex[:16]}"

    # 1. 存到 Redis（key=sso:qr:{qr_token}，TTL 120s）
    try:
        r = await get_redis()
        state_data = {
            "qrToken": qr_token,
            "provider": provider,
            "status": "waiting",
            "createdAt": time.time(),
        }
        await r.set(f"sso:qr:{qr_token}", json.dumps(state_data), ex=120)
    except Exception as e:
        # Redis 不可用，mock 模式继续
        import logging
        logging.warning(f"[sso] 存 qr 状态到 redis 失败: {e}")

    # 2. provider-specific URL
    if provider == "wechat-work":
        # 真模式：用企业微信 OAuth URL；mock：shuzhi:// deeplink
        from app.integrations import wechat_work
        sso_url = wechat_work.generate_qrcode_url(state=qr_token) or f"shuzhi://sso?token={qr_token}&provider={provider}"
    else:
        sso_url = f"shuzhi://sso?token={qr_token}&provider={provider}"

    # 3. 生成二维码图片（base64）
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(sso_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_base64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "qrToken": qr_token,
        "qrImageUrl": f"data:image/png;base64,{img_base64}",
        "expiresIn": 120,
        "pollUrl": f"/api/v1/auth/sso/qrcode/check?token={qr_token}",
        "scanUrl": sso_url,  # 调试用
    }


async def check_sso_qrcode_status(qr_token: str) -> dict:
    """
    轮询扫码状态
    R6.4: 真查 Redis
    - waiting: 用户未扫
    - scanned: 用户已扫，未确认
    - confirmed: 用户已确认，附带 user info + token
    - expired: 二维码过期
    """
    try:
        r = await get_redis()
        raw = await r.get(f"sso:qr:{qr_token}")
        if not raw:
            return {"status": "expired"}
        data = json.loads(raw)
        # 兜底：mock 模式永远 waiting
        if data.get("provider") == "wechat-work" and not _is_wechat_real_mode():
            return {"status": "waiting"}
        return {
            "status": data.get("status", "waiting"),
            "token": data.get("token"),
            "userInfo": data.get("userInfo"),
        }
    except Exception as e:
        import logging
        logging.warning(f"[sso] check status 异常: {e}")
        return {"status": "waiting"}


def _is_wechat_real_mode() -> bool:
    """检查企业微信 SSO 是否真模式"""
    from app.config import settings
    return bool(settings.WECHAT_WORK_CORP_ID and settings.WECHAT_WORK_CORP_SECRET)


async def handle_wechat_work_callback(db: AsyncSession, code: str, state: str) -> dict:
    """
    企业微信 OAuth 回调
    R6.4: 真模式 + mock 双模式
    """
    from app.integrations import wechat_work

    # 1. 拿用户信息
    if _is_wechat_real_mode():
        # 真模式：调企业微信 API
        user_info = await wechat_work.exchange_code_for_user(code)
        if not user_info:
            raise UnauthorizedException("企业微信登录失败：code 无效或 access_token 过期")
    else:
        # mock 模式：用 state 模拟
        user_info = await wechat_work.mock_get_user_by_state(state)

    # 2. 在本系统找用户（按 userid 匹配）—— 必须预加载 roles
    from sqlalchemy.orm import selectinload
    wechat_userid = user_info.get("userid")
    if not wechat_userid:
        raise UnauthorizedException("企业微信未返回 userid")

    # 尝试用 userid 当 username 查
    db_user = (await db.execute(
        select(User)
        .where(User.username == wechat_userid)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.department),
        )
    )).scalar_one_or_none()

    # 兜底：admin
    if not db_user:
        db_user = (await db.execute(
            select(User)
            .where(User.username == "admin")
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.department),
            )
        )).scalar_one_or_none()

    if not db_user:
        raise UnauthorizedException(f"本系统未配置企业微信用户: {wechat_userid}")

    # 3. 签发 token（复用 login 流程）
    return _build_login_response(db, db_user, remember_me=False)


# ===== 登出 =====

async def logout(db: AsyncSession, user_id: int):
    """
    登出：清除 token（生产中应加入 token 黑名单到 Redis）
    """
    # TODO: 实现 token 黑名单
    pass
