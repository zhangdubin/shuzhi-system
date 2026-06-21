"""
认证模块测试

测试矩阵：
- 登录成功 / 失败
- 登录响应字段完整性
- me 端点需要 token
- SSO 二维码生成
- 密码重置（占位）
"""
import pytest
from datetime import datetime


# ============== 登录 ==============

@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    """管理员登录成功"""
    resp = await client.post("/api/v1/auth/login", json={
        "account": "admin",
        "password": "admin123",
        "rememberMe": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    # LoginResponse 直接序列化（无外层 code 包装）
    assert "token" in data
    assert "refreshToken" in data
    assert "expiresIn" in data
    assert "userInfo" in data

    # userInfo 字段
    ui = data["userInfo"]
    assert ui["name"] == "管理员"
    assert ui["userId"] > 0
    assert "role" in ui


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin_user):
    """密码错误 → 401"""
    resp = await client.post("/api/v1/auth/login", json={
        "account": "admin",
        "password": "wrong-password",
    })
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == 1001
    assert "data" in body
    assert body["data"] is None


@pytest.mark.asyncio
async def test_login_user_not_found(client):
    """用户不存在 → 401（不区分用户名/密码错误，防枚举）"""
    resp = await client.post("/api/v1/auth/login", json={
        "account": "nonexistent",
        "password": "whatever",
    })
    assert resp.status_code == 401
    assert resp.json()["code"] == 1001


@pytest.mark.asyncio
async def test_login_via_email(client, admin_user):
    """支持邮箱登录"""
    resp = await client.post("/api/v1/auth/login", json={
        "account": "admin@example.com",
        "password": "admin123",
    })
    assert resp.status_code == 200
    assert "token" in resp.json()


@pytest.mark.asyncio
async def test_login_via_phone(client, admin_user):
    """支持手机号登录"""
    resp = await client.post("/api/v1/auth/login", json={
        "account": "13800000001",
        "password": "admin123",
    })
    assert resp.status_code == 200
    assert "token" in resp.json()


@pytest.mark.asyncio
async def test_login_remember_me_extends_expiry(client, admin_user):
    """记住我延长 token 有效期"""
    resp_short = await client.post("/api/v1/auth/login", json={
        "account": "admin", "password": "admin123", "rememberMe": False,
    })
    resp_long = await client.post("/api/v1/auth/login", json={
        "account": "admin", "password": "admin123", "rememberMe": True,
    })
    assert resp_long.json()["expiresIn"] > resp_short.json()["expiresIn"]


@pytest.mark.asyncio
async def test_login_param_too_short(client):
    """密码不足 6 位 → 422"""
    resp = await client.post("/api/v1/auth/login", json={
        "account": "admin",
        "password": "123",  # 不足 6 位
    })
    assert resp.status_code == 422


# ============== 登出 ==============

@pytest.mark.asyncio
async def test_logout_success(client, auth_headers):
    """登出"""
    resp = await client.post("/api/v1/auth/logout", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


@pytest.mark.asyncio
async def test_logout_unauthorized(client):
    """未登录登出 → 401"""
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 401


# ============== 当前用户信息 ==============

@pytest.mark.asyncio
async def test_me_unauthorized(client):
    """未登录访问 /me → 401"""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_success(client, auth_headers, admin_user):
    """已登录访问 /me"""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["userId"] == admin_user.id
    assert data["data"]["name"] == "管理员"
    assert data["data"]["isAdmin"] is True
    assert "permissions" in data["data"]
    assert "dataScope" in data["data"]


# ============== SSO ==============

@pytest.mark.asyncio
async def test_sso_qrcode_generate_wechat(client):
    """生成企业微信二维码"""
    resp = await client.post(
        "/api/v1/auth/sso/qrcode/generate",
        json={"provider": "wechat"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "qrToken" in data
    assert "qrImageUrl" in data
    assert data["qrImageUrl"].startswith("data:image/png;base64,")
    assert "pollUrl" in data
    assert "expiresIn" in data


@pytest.mark.asyncio
async def test_sso_qrcode_generate_dingtalk(client):
    """生成钉钉二维码"""
    resp = await client.post(
        "/api/v1/auth/sso/qrcode/generate",
        json={"provider": "dingtalk"},
    )
    assert resp.status_code == 200
    assert "qrToken" in resp.json()


@pytest.mark.asyncio
async def test_sso_qrcode_invalid_provider(client):
    """无效的 provider → 422"""
    resp = await client.post(
        "/api/v1/auth/sso/qrcode/generate",
        json={"provider": "invalid"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sso_qrcode_check(client):
    """轮询扫码状态（演示版返回 waiting）"""
    resp = await client.post(
        "/api/v1/auth/sso/qrcode/check",
        json={"qrToken": "qr_test_token_123"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "waiting"


# ============== 密码重置 ==============

@pytest.mark.asyncio
async def test_password_reset_request(client):
    """发送重置密码验证码（占位实现）"""
    resp = await client.post(
        "/api/v1/auth/password/reset/request",
        json={"account": "admin@example.com", "verifyType": "email"},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


@pytest.mark.asyncio
async def test_password_reset_confirm(client):
    """确认重置密码（占位实现）"""
    resp = await client.post(
        "/api/v1/auth/password/reset/confirm",
        json={
            "account": "admin@example.com",
            "verifyCode": "123456",
            "newPassword": "newpassword123",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
