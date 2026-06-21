"""
登录请求/响应 Pydantic schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ===== 登录 =====

class LoginRequest(BaseModel):
    account: str = Field(..., min_length=1, max_length=128, description="手机号/邮箱/工号")
    password: str = Field(..., min_length=6, max_length=128)
    rememberMe: bool = False


class UserInfo(BaseModel):
    userId: int
    name: str
    avatar: Optional[str] = None
    role: str
    department: Optional[str] = None
    isAdmin: bool = False
    permissions: list[str] = []


class LoginResponse(BaseModel):
    token: str
    refreshToken: str
    expiresIn: int
    userInfo: UserInfo


# ===== SSO =====

class SSOQRCodeRequest(BaseModel):
    provider: str = Field(..., pattern="^(wechat|wechat-work|dingtalk|feishu)$")


class SSOQRCodeResponse(BaseModel):
    qrToken: str
    qrImageUrl: str  # 实际是 base64 data URL
    expiresIn: int
    pollUrl: str


class SSOCheckRequest(BaseModel):
    qrToken: str


class SSOCheckResponse(BaseModel):
    status: str  # waiting | confirmed | expired
    token: Optional[str] = None
    userInfo: Optional[UserInfo] = None


# ===== 密码重置 =====

class PasswordResetRequest(BaseModel):
    account: str
    verifyType: str = Field(..., pattern="^(email|sms)$")


class PasswordResetConfirm(BaseModel):
    account: str
    verifyCode: str = Field(..., min_length=4, max_length=8)
    newPassword: str = Field(..., min_length=8, max_length=128)
