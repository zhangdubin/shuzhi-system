"""
统一异常类 + 异常处理器
所有业务异常都继承 AppException，配合 code 字段返回给前端
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger


class AppException(Exception):
    """业务异常基类"""
    code: int = 1000
    message: str = "系统异常"
    status_code: int = 400

    def __init__(self, message: str = None, code: int = None, status_code: int = None):
        if message:
            self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


# ===== 通用异常 =====

class UnauthorizedException(AppException):
    code = 1001
    message = "未登录或登录已过期"
    status_code = 401


class ForbiddenException(AppException):
    code = 1003
    message = "无权限访问"
    status_code = 403


class NotFoundException(AppException):
    code = 2004
    message = "资源不存在"
    status_code = 404


class ParamErrorException(AppException):
    code = 2001
    message = "参数错误"
    status_code = 422


class ConflictException(AppException):
    code = 2009
    message = "数据冲突"
    status_code = 409


class ServerErrorException(AppException):
    code = 5000
    message = "服务器内部错误"
    status_code = 500


# ===== 业务异常 =====

class OCRFailedException(AppException):
    code = 5001
    message = "OCR 识别失败"
    status_code = 502


class VerifyFailedException(AppException):
    code = 5002
    message = "国税查验服务异常"
    status_code = 502


# ===== AI 平台错误码（AI-API.md §2） =====

class AIQuotaExceededException(AppException):
    """3001 AI 余额不足"""
    code = 3001
    message = "AI 余额不足，请充值或申请额度"
    status_code = 402


class AIRateLimitedException(AppException):
    """3002 AI 配额超限（限流）"""
    code = 3002
    message = "AI 配额超限，请稍后重试"
    status_code = 429


class AIInputTooLargeException(AppException):
    """3003 AI 输入超限（图太大/文档太长）"""
    code = 3003
    message = "AI 输入超限，请压缩后再试"
    status_code = 413


class AIModelUnavailableException(AppException):
    """5101 AI 模型不可用"""
    code = 5101
    message = "AI 模型暂不可用，已切换到普通模式"
    status_code = 503


class AITimeoutException(AppException):
    """5102 AI 超时"""
    code = 5102
    message = "AI 服务超时"
    status_code = 504


class AIRejectedException(AppException):
    """5103 AI 内容安全审核拒绝"""
    code = 5103
    message = "内容安全审核未通过"
    status_code = 451


class AIFormatException(AppException):
    """5104 AI 返回格式异常"""
    code = 5104
    message = "AI 返回格式异常"
    status_code = 502


# ===== 异常处理器 =====

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """统一异常响应"""
    logger.warning(f"业务异常：{exc.code} - {exc.message} (path={request.url.path})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "path": str(request.url.path),
        },
    )
