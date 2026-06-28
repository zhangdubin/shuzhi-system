"""UDPE 自定义异常。

设计文档：plans/udpe-design/design.md §六 6.2
"""
from app.core.exceptions import AppException


class PrintTemplateNotFoundError(AppException):
    """模板未找到"""
    code = 3101
    message = "打印模板不存在"
    status_code = 404


class PrintTemplateInactiveError(AppException):
    """模板未发布/已归档"""
    code = 3102
    message = "打印模板未处于可用状态"
    status_code = 409


class PrintRenderError(AppException):
    """渲染失败"""
    code = 3103
    message = "打印渲染失败"
    status_code = 500


class PrintDataResolveError(AppException):
    """数据解析失败"""
    code = 3104
    message = "打印数据解析失败"
    status_code = 422


class PrintPermissionDeniedError(AppException):
    """打印权限不足"""
    code = 3105
    message = "打印权限不足"
    status_code = 403


class RendererNotFoundError(AppException):
    """Renderer 未注册"""
    code = 3106
    message = "Renderer 未注册"
    status_code = 500


class ResolverNotFoundError(AppException):
    """Resolver 未注册"""
    code = 3107
    message = "Resolver 未注册"
    status_code = 500
