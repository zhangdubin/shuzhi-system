"""
认证模块路由
对应 API.md §认证模块 6 个接口
"""
import qrcode
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, CurrentUser
from app.core.exceptions import UnauthorizedException
from app.modules.auth.schemas import (
    LoginRequest, LoginResponse,
    SSOQRCodeRequest, SSOQRCodeResponse,
    SSOCheckRequest, SSOCheckResponse,
    PasswordResetRequest, PasswordResetConfirm,
    UserInfo,
)
from app.modules.auth import service

router = APIRouter()


@router.post("/login", response_model=LoginResponse, summary="账号密码登录")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await service.login_with_password(
        db, req.account, req.password, req.rememberMe
    )


@router.post("/logout", summary="登出")
async def logout(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await service.logout(db, current_user.id)
    return {"code": 0, "message": "success"}


@router.post("/sso/qrcode/generate", response_model=SSOQRCodeResponse, summary="生成 SSO 扫码二维码")
async def sso_qrcode_generate(req: SSOQRCodeRequest):
    return await service.generate_sso_qrcode(req.provider)


@router.post("/sso/qrcode/check", response_model=SSOCheckResponse, summary="轮询扫码状态")
async def sso_qrcode_check(req: SSOCheckRequest):
    """
    R6.4: 真查 Redis 中 qr_token 对应的扫码状态
    waiting = 用户未扫/已扫未确认
    scanned = 用户已扫，等待确认
    confirmed = 用户已确认，附带 user info
    expired = 二维码过期
    """
    return await service.check_sso_qrcode_status(req.qrToken)


@router.post("/sso/wechat-work/callback", summary="企业微信 OAuth 回调")
async def sso_wechat_work_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """
    R6.4 架构预留：企业微信扫码后回调
    - 真模式：code → userid → 查本系统 user → 签发 token
    - mock 模式：state → mock user → 签发 token
    """
    return await service.handle_wechat_work_callback(db, code, state)


@router.get("/sso/wechat-work/health", summary="企业微信 SSO 健康检查")
async def sso_wechat_work_health():
    """探测企业微信 SSO 服务状态（mock / real / down）"""
    from app.integrations import wechat_work
    return {"code": 0, "data": await wechat_work.health_check()}


@router.post("/password/reset/request", summary="发送重置密码验证码")
async def password_reset_request(req: PasswordResetRequest):
    # TODO: 调用邮件/短信服务发送验证码
    return {"code": 0, "message": "验证码已发送"}


@router.post("/password/reset/confirm", summary="确认重置密码")
async def password_reset_confirm(req: PasswordResetConfirm):
    # TODO: 验证验证码 + 更新密码
    return {"code": 0, "message": "密码已重置"}


@router.get("/me", summary="获取当前登录用户信息")
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """R12 修复：补充 role / department / departmentId 字段，header 头像旁的角色 tag 才有值"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.modules.auth.models import User

    # 重新查 user 以拿到 role name 和 department name
    result = await db.execute(
        select(User)
        .where(User.id == current_user.id)
        .options(selectinload(User.roles), selectinload(User.department))
    )
    user = result.scalar_one_or_none()
    role_name = (user.roles[0].name if user and user.roles else None) or ("超级管理员" if current_user.is_admin else "用户")
    dept_name = (user.department.name if user and user.department else None) or ""
    return {
        "code": 0,
        "data": {
            "userId": current_user.id,
            "name": current_user.name,
            "username": current_user.username,
            "role": role_name,
            "department": dept_name,
            "departmentId": current_user.department_id,
            "isAdmin": current_user.is_admin,
            "permissions": current_user.permissions,
            "dataScope": current_user.data_scope,
        }
    }
