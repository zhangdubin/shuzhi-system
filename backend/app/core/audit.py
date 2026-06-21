"""
审计日志中间件：自动记录所有写接口
"""
import json
import logging
import re
import time
import uuid

logger = logging.getLogger(__name__)
from typing import Callable, Optional

from fastapi import Request, Response
from loguru import logger
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_token
from app.core.database import AsyncSessionLocal
from app.modules.auth.models import AuditLog, User

# 敏感字段（写入日志前脱敏）
_SENSITIVE_KEYS = {
    "password", "oldPassword", "newPassword", "old_password", "new_password",
    "token", "refreshToken", "refresh_token", "accessToken", "access_token",
    "secret", "apiKey", "api_key", "privateKey", "private_key",
}


def _redact_body(body_str: str) -> str:
    """过滤敏感字段：尝试解析 JSON 替换敏感值"""
    if not body_str:
        return body_str
    try:
        data = json.loads(body_str)
        if isinstance(data, dict):
            for k in list(data.keys()):
                if k in _SENSITIVE_KEYS or any(s in k.lower() for s in ("password", "secret", "token", "key")):
                    data[k] = "***REDACTED***"
            return json.dumps(data, ensure_ascii=False)
        return body_str
    except (ValueError, TypeError):
        # 非 JSON 格式：正则粗暴替换
        for k in _SENSITIVE_KEYS:
            body_str = re.sub(
                rf'"{k}"\s*:\s*"[^"]*"',
                f'"{k}": "***REDACTED***"',
                body_str,
                flags=re.IGNORECASE,
            )
        return body_str


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    自动审计写接口（POST/PUT/DELETE/PATCH）
    简化版：只记录关键信息，详细 before/after diff 由业务代码显式调用
    """

    # 不需要审计的路径
    SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}

    # 业务对象编码字段（按 resource_type → body 字段名）
    # 用于从 body 里抽 resourceCode（合同 → contractId/code；发票 → invoiceId/code）
    RESOURCE_CODE_FIELD = {
        "projects": "code",
        "contracts": "code",
        "expenses": "code",
        "receivables": "code",
        "invoices": "code",
        "templates": "code",
        "users": "username",
        "depts": "code",
        "roles": "code",
        "dicts": "value",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 只审计写操作 + 非白名单
        if request.method in ("POST", "PUT", "DELETE", "PATCH") and \
           not any(request.url.path.startswith(p) for p in self.SKIP_PATHS):

            # 读 body（用于记录）
            body = await request.body()
            body_str = body.decode("utf-8", errors="ignore") if body else ""
            # 过滤敏感字段（密码、token、secret 等）—— 防止明文存 DB
            body_str = _redact_body(body_str)
            # 截断过大的 body
            if len(body_str) > 2000:
                body_str = body_str[:2000] + "..."

            # 提取用户 + 查 name
            operator_id: Optional[int] = None
            operator_name: Optional[str] = None
            try:
                auth = request.headers.get("authorization", "")
                if auth.startswith("Bearer "):
                    payload = decode_token(auth[7:])
                    operator_id = int(payload.get("sub", 0))
            except Exception:
                pass

            # 解析 resource_code（从 body 找 code 字段）
            resource_code = self._extract_resource_code(body_str)

            # 执行请求
            start = time.time()
            response = await call_next(request)
            elapsed = (time.time() - start) * 1000

            # 慢请求日志（> 500ms 警告）
            if elapsed > 500:
                logger.warning(
                    f"[SLOW] {request.method} {request.url.path} "
                    f"status={response.status_code} elapsed={elapsed:.0f}ms"
                )

            # 异步写日志（不阻塞响应）
            if response.status_code < 500:
                try:
                    async with AsyncSessionLocal() as session:
                        # 拿用户名（一次性查）
                        if operator_id and not operator_name:
                            ur = await session.execute(
                                select(User.name).where(User.id == operator_id)
                            )
                            operator_name = ur.scalar_one_or_none()

                        log = AuditLog(
                            operator_id=operator_id,
                            operator_name=operator_name,
                            action=request.method,
                            resource_type=self._extract_resource(request.url.path),
                            resource_id=None,  # 详细 diff 由业务代码补
                            resource_code=resource_code,
                            path=request.url.path,
                            method=request.method,
                            status_code=response.status_code,
                            body=body_str,
                            ip=request.client.host if request.client else None,
                            user_agent=request.headers.get("user-agent", "")[:256],
                            elapsed_ms=int(elapsed),
                        )
                        session.add(log)
                        await session.commit()
                except Exception as e:
                    logger.error(f"审计日志写入失败：{e}")

            return response

        return await call_next(request)

    @staticmethod
    def _extract_resource(path: str) -> str:
        """从路径提取资源类型 /api/v1/projects/123 → projects"""
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 3 and parts[0] == "api":
            return parts[2]
        return "unknown"

    def _extract_resource_code(self, body_str: str) -> Optional[str]:
        """从 body JSON 抽 business code（合同号/用户名/编号）"""
        if not body_str or not body_str.strip().startswith("{"):
            return None
        try:
            data = json.loads(body_str)
        except Exception:
            return None
        # 优先从 path 拿 resource_type
        # （dispatch 内 path 可通过 request.url.path 拿，但这里不在 request 上下文）
        # 简化：扫所有可能的 code 字段
        for key in ("code", "username", "value"):
            if key in data and isinstance(data[key], str):
                return data[key]
        # 数字 ID 也可作为 resourceCode
        for key in ("contractId", "projectId", "expenseId", "receivableId",
                    "invoiceId", "templateId", "userId", "roleId", "deptId", "dictId"):
            if key in data and data[key] is not None:
                return f"#{data[key]}"
        return None
